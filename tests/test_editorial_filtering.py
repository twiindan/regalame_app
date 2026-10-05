"""Centralized editorial filtering: modes, visibility, suppression, blog, T1/T2.

Strict TDD: each behavior below was written RED before the wiring it exercises.
The shadow guarantee has two halves — T1 (structural: no editorial read under
``off`` and responses independent of decision rows) and T2 (golden baselines).
"""

from datetime import datetime
from pathlib import Path

import pytest
from sqlmodel import select

import curation
from catalog import CatalogQuery, list_categories, normalize_text, search_products
from models import EditorialDecision, EditorialGateState, Product, ProductList, Wish
from services import get_blog_post_detail

BASELINES_DIR = Path(__file__).parent / "baselines"
POLICY = curation.EDITORIAL_POLICY_VERSION
MODEL = "qwen3.6"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_product(session, asin, title, *, category="Hogar y cocina",
                  slug="hogar-y-cocina", price=None, image=None, active=True):
    product = Product(
        asin=asin,
        title=title,
        title_normalized=normalize_text(title),
        image_url=image or f"img-{asin.lower()}.jpg",
        url=f"https://www.amazon.es/dp/{asin}",
        category=category,
        category_slug=slug,
        price_numeric=price,
        price_raw=f"{price} €" if price is not None else "N/A",
        scraped_at=datetime(2026, 1, 1),
        is_active=active,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def _seed_gate(session, *, gate_passed=True, coverage_ratio=1.0, policy_version=POLICY):
    gate = EditorialGateState(
        gate_passed=gate_passed,
        coverage_ratio=coverage_ratio,
        unknown_ratio=0.0,
        policy_version=policy_version,
        model_id=MODEL,
    )
    session.add(gate)
    session.commit()
    session.refresh(gate)
    return gate


def _asins(result):
    return {product.asin for product in result.items}


@pytest.fixture(name="enforce")
def enforce_fixture(session, monkeypatch):
    """Configure ``enforce`` with a passing gate (all preconditions met)."""
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session)
    return session


# --------------------------------------------------------------------------- #
# 6.1 Default off + T1 shadow structural proof
# --------------------------------------------------------------------------- #


def test_default_filter_mode_is_off(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    assert curation.effective_filter_mode(session) == "off"


def test_off_mode_issues_no_editorial_sql(client, catalog_seed, seed_editorial, monkeypatch,
                                          sql_statements):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    for product in catalog_seed:
        seed_editorial(product, "excluded")

    sql_statements.clear()
    for path in ("/catalog", "/bestsellers", "/ideas/alimentacion-y-bebidas",
                 "/sitemap.xml", "/blog/regalos-amigo-invisible-10-euros"):
        assert client.get(path).status_code == 200

    offenders = [s for s in sql_statements
                 if "editorial_decision" in s or "editorial_gate_state" in s]
    assert offenders == []


def test_off_mode_responses_are_independent_of_editorial_rows(client, catalog_seed,
                                                              seed_editorial, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    surfaces = [
        "/",
        "/catalog",
        "/catalog?category=alimentacion-y-bebidas",
        "/trends",
        "/most-desired",
        "/bestsellers",
        "/ideas/alimentacion-y-bebidas",
        "/blog/regalos-amigo-invisible-10-euros",
        "/sitemap.xml",
    ]

    without_rows = {path: client.get(path).text for path in surfaces}

    for product in catalog_seed:
        seed_editorial(product, "excluded")

    with_rows = {path: client.get(path).text for path in surfaces}
    assert with_rows == without_rows


# --------------------------------------------------------------------------- #
# 6.3 Enforce: visibility, totals, pagination (catalog path)
# --------------------------------------------------------------------------- #


def test_general_surface_shows_only_eligible(session, catalog_seed, enforce, seed_editorial):
    a1, a2, b1 = catalog_seed
    seed_editorial(a1, "eligible")
    seed_editorial(a2, "excluded")
    # b1 has no decision row -> unknown -> hidden.

    result = search_products(session, CatalogQuery())
    assert _asins(result) == {"A1"}
    assert result.total == 1


def test_contextual_only_under_a_matching_context(session, catalog_seed, enforce,
                                                  seed_editorial):
    a1, a2, b1 = catalog_seed
    seed_editorial(a2, "contextual", "alimentacion-y-bebidas")
    seed_editorial(b1, "eligible")

    general = search_products(session, CatalogQuery())
    assert _asins(general) == {"B1"}

    # The /ideas/{slug} context surface merges eligible-of-category with the
    # contextual products whose context matches the slug.
    context = search_products(session, CatalogQuery(
        category_slug="alimentacion-y-bebidas",
        editorial_context="alimentacion-y-bebidas",
    ))
    assert _asins(context) == {"A2"}

    # A plain category filter (e.g. /catalog?category=...) stays a general surface.
    catalog_category = search_products(session, CatalogQuery(
        category_slug="alimentacion-y-bebidas"))
    assert _asins(catalog_category) == set()


def test_excluded_and_unknown_are_hidden_everywhere(session, catalog_seed, enforce,
                                                    seed_editorial):
    a1, a2, b1 = catalog_seed
    seed_editorial(a1, "excluded")
    seed_editorial(a2, "unknown")
    # b1 has no row.

    assert search_products(session, CatalogQuery()).items == []
    assert search_products(session, CatalogQuery(
        category_slug="alimentacion-y-bebidas",
        editorial_context="alimentacion-y-bebidas",
    )).items == []


def test_totals_and_pagination_reflect_the_filtered_set(session, enforce, seed_editorial):
    products = [_make_product(session, f"P{i:02d}", f"Regalo {i}") for i in range(15)]
    for product in products[:12]:
        seed_editorial(product, "eligible")
    for product in products[12:]:
        seed_editorial(product, "excluded")

    page1 = search_products(session, CatalogQuery(per_page=10, page=1))
    assert page1.total == 12
    assert page1.total_pages == 2
    assert len(page1.items) == 10

    page2 = search_products(session, CatalogQuery(per_page=10, page=2))
    assert len(page2.items) == 2
    assert _asins(page2).isdisjoint({f"P{i:02d}" for i in range(12, 15)})


# --------------------------------------------------------------------------- #
# 6.5 Category suppression (navigation + sitemap)
# --------------------------------------------------------------------------- #


def test_list_categories_suppresses_zero_visible_category(session, enforce, seed_editorial):
    visible = _make_product(session, "P1", "Cafetera", category="Hogar", slug="hogar")
    hidden = _make_product(session, "P2", "Pistola", category="Juguetes", slug="juguetes")
    seed_editorial(visible, "eligible")
    seed_editorial(hidden, "excluded")

    assert [slug for _, slug in list_categories(session)] == ["hogar"]


def test_list_categories_unchanged_when_off(session, monkeypatch, seed_editorial):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    visible = _make_product(session, "P1", "Cafetera", category="Hogar", slug="hogar")
    hidden = _make_product(session, "P2", "Pistola", category="Juguetes", slug="juguetes")
    seed_editorial(visible, "eligible")
    seed_editorial(hidden, "excluded")

    assert {slug for _, slug in list_categories(session)} == {"hogar", "juguetes"}


def test_sitemap_suppresses_zero_visible_category(client, session, enforce, seed_editorial):
    visible = _make_product(session, "P1", "Cafetera", category="Hogar", slug="hogar")
    hidden = _make_product(session, "P2", "Pistola", category="Juguetes", slug="juguetes")
    seed_editorial(visible, "eligible")
    seed_editorial(hidden, "excluded")

    body = client.get("/sitemap.xml").text
    assert "/ideas/hogar" in body
    assert "/ideas/juguetes" not in body


def test_sitemap_unchanged_when_off(client, session, monkeypatch, seed_editorial):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    visible = _make_product(session, "P1", "Cafetera", category="Hogar", slug="hogar")
    hidden = _make_product(session, "P2", "Pistola", category="Juguetes", slug="juguetes")
    seed_editorial(visible, "eligible")
    seed_editorial(hidden, "excluded")

    body = client.get("/sitemap.xml").text
    assert "/ideas/hogar" in body
    assert "/ideas/juguetes" in body


# --------------------------------------------------------------------------- #
# 6.3/6.4 Route surfaces + /ideas context wiring
# --------------------------------------------------------------------------- #


def test_all_shared_surfaces_hide_excluded(client, session, catalog_seed, enforce,
                                           seed_editorial):
    a1, a2, b1 = catalog_seed
    session.add_all([
        ProductList(product_id=a1.id, list_key="trends", rank=9),
        ProductList(product_id=a1.id, list_key="desired", rank=9),
    ])
    session.commit()
    seed_editorial(a1, "excluded")
    seed_editorial(a2, "eligible")
    seed_editorial(b1, "eligible")

    for path in ("/catalog", "/trends", "/most-desired", "/bestsellers",
                 "/ideas/alimentacion-y-bebidas"):
        assert "Café molido" not in client.get(path).text, path


def test_dashboard_samples_hide_excluded(auth_client, session, catalog_seed, enforce,
                                         seed_editorial):
    a1, a2, b1 = catalog_seed
    seed_editorial(a1, "excluded")
    seed_editorial(a2, "eligible")
    seed_editorial(b1, "eligible")

    body = auth_client.get("/dashboard").text
    assert "Café molido" not in body
    assert "Cafetera express" in body


def test_ideas_route_merges_context_visibility(client, session, enforce, seed_editorial):
    contextual = _make_product(session, "C1", "Cuna portátil", category="Hogar", slug="hogar")
    eligible = _make_product(session, "E1", "Cafetera", category="Hogar", slug="hogar")
    other = _make_product(session, "C2", "Altavoz", category="Electrónica", slug="electronica")
    seed_editorial(contextual, "contextual", "hogar")
    seed_editorial(eligible, "eligible")
    seed_editorial(other, "contextual", "electronica")

    ideas_hogar = client.get("/ideas/hogar").text
    assert "Cuna portátil" in ideas_hogar       # contextual matching the slug
    assert "Cafetera" in ideas_hogar            # eligible of the category
    assert "Altavoz" not in ideas_hogar         # contextual for another context

    ideas_electronica = client.get("/ideas/electronica").text
    assert "Altavoz" in ideas_electronica       # contextual matching its own context
    assert "Cuna portátil" not in ideas_electronica

    general = client.get("/catalog").text
    assert "Cuna portátil" not in general       # contextual hidden on a general surface
    assert "Cafetera" in general


# --------------------------------------------------------------------------- #
# 6.4/6.5 Blog empty state + hero fallback
# --------------------------------------------------------------------------- #


def test_blog_list_filters_and_renders_empty_state(client, session, enforce, seed_editorial):
    product = _make_product(session, "BLOG1", "Café barato", category="Hogar", slug="hogar",
                            price=5.0)
    seed_editorial(product, "excluded")

    post, products = get_blog_post_detail(session, "regalos-amigo-invisible-10-euros")
    assert products == []
    # The hero fallback must never be derived from an empty visible list.
    assert post.get("hero_image") is None

    body = client.get("/blog/regalos-amigo-invisible-10-euros").text
    assert "No encontramos productos" in body
    assert "Café barato" not in body


def test_blog_hero_uses_the_first_visible_product(client, session, enforce, seed_editorial):
    product = _make_product(session, "BLOG2", "Café bueno", category="Hogar", slug="hogar",
                            price=5.0, image="img-blog2.jpg")
    seed_editorial(product, "eligible")

    post, products = get_blog_post_detail(session, "regalos-amigo-invisible-10-euros")
    assert [p.asin for p in products] == ["BLOG2"]
    assert post["hero_image"] == "img-blog2.jpg"


# --------------------------------------------------------------------------- #
# 6.5 Safety rails: wishes + import health
# --------------------------------------------------------------------------- #


def test_wish_can_add_an_excluded_product_under_enforce(auth_client, session, enforce,
                                                        seed_editorial):
    product = _make_product(session, "W1", "Pistola de agua", category="Juguetes",
                            slug="juguetes")
    seed_editorial(product, "excluded")

    response = auth_client.post("/wishes", data={
        "content": product.url,
        "manual_title": product.title,
        "manual_image": product.image_url,
    })
    assert response.status_code == 200

    wishes = session.exec(select(Wish)).all()
    assert [wish.title for wish in wishes] == ["Pistola de agua"]


def test_existing_wishes_survive_classification(auth_client, session, test_user, enforce,
                                                seed_editorial):
    session.add(Wish(user_id=test_user.id, title="Regalo antiguo",
                     url="https://www.amazon.es/dp/OLD", image_url="img-old.jpg"))
    session.commit()
    product = _make_product(session, "OLD", "Regalo antiguo", category="Juguetes",
                            slug="juguetes")
    seed_editorial(product, "excluded")

    # The wish route does not go through search_products, so it stays visible.
    wishes = session.exec(select(Wish)).all()
    assert [wish.title for wish in wishes] == ["Regalo antiguo"]


def test_curation_never_mutates_productlist(session, catalog_seed, enforce, seed_editorial):
    import jobs.refresh_catalog as refresh_catalog

    a1, a2, b1 = catalog_seed

    def snapshot():
        return sorted(
            tuple(row) for row in session.exec(
                select(ProductList.product_id, ProductList.list_key, ProductList.rank)
            ).all()
        )

    before = snapshot()
    seed_editorial(a1, "eligible")
    seed_editorial(a2, "excluded")

    search_products(session, CatalogQuery())
    search_products(session, CatalogQuery(category_slug="alimentacion-y-bebidas",
                                          editorial_context="alimentacion-y-bebidas"))
    list_categories(session)

    # Import-health metrics keep counting the unfiltered ProductList rows.
    assert refresh_catalog.baseline_counts(session) == {"bestsellers": 2, "trends": 2}
    assert snapshot() == before


# --------------------------------------------------------------------------- #
# 6.6 T2 golden baselines
# --------------------------------------------------------------------------- #

OFF_SURFACES = [
    ("/", "home"),
    ("/catalog", "catalog"),
    ("/catalog?category=alimentacion-y-bebidas", "catalog_category"),
    ("/trends", "trends"),
    ("/most-desired", "most_desired"),
    ("/bestsellers", "bestsellers"),
    ("/ideas/alimentacion-y-bebidas", "ideas"),
    ("/blog/regalos-amigo-invisible-10-euros", "blog"),
    ("/sitemap.xml", "sitemap"),
]


@pytest.mark.parametrize("path,name", OFF_SURFACES, ids=[name for _, name in OFF_SURFACES])
def test_off_mode_matches_golden_baseline(client, catalog_seed, seed_editorial, monkeypatch,
                                          editorial_update_baselines, path, name):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    # The baselines must prove that decision rows change nothing under off.
    for product in catalog_seed:
        seed_editorial(product, "excluded")

    body = client.get(path).text
    target = BASELINES_DIR / f"editorial_off_{name}.html"

    if editorial_update_baselines:
        BASELINES_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    assert target.exists(), (
        f"missing golden baseline {target}; regenerate with --editorial-update-baselines"
    )
    assert body == target.read_text(encoding="utf-8"), f"off-mode drift on {path}"
