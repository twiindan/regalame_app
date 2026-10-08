"""Focused tests for the Christmas gift guide work (roadmap item 5).

Covers the optional `criteria["limit"]` cap and the `criteria["items"]`
hand-curated list, both used by the new Christmas guide entry.
"""

import pytest
from bs4 import BeautifulSoup


def _probe(monkeypatch, slug, criteria):
    """Point services at a single synthetic post."""
    import services

    monkeypatch.setattr(services, "BLOG_POSTS", [{
        "slug": slug,
        "title": "Probe",
        "description": "Probe",
        "criteria": criteria,
        "hero_image": None,
    }])


# --------------------------------------------------------------------------- #
# WU-1 — optional criteria["limit"] cap on curated lists
# --------------------------------------------------------------------------- #

def test_get_blog_post_detail_respects_limit(session, catalog_seed, monkeypatch):
    from services import get_blog_post_detail

    _probe(monkeypatch, "limit-probe", {"limit": 2})

    post, products = get_blog_post_detail(session, "limit-probe")

    assert post is not None
    assert len(products) == 2


def test_get_blog_post_detail_without_limit_returns_all(session, catalog_seed, monkeypatch):
    from services import get_blog_post_detail

    _probe(monkeypatch, "no-limit-probe", {})

    _, products = get_blog_post_detail(session, "no-limit-probe")

    assert len(products) == 3


@pytest.mark.parametrize("bad_limit", [0, -1, "2", None])
def test_get_blog_post_detail_ignores_non_positive_or_non_int_limit(
    session, catalog_seed, monkeypatch, bad_limit
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "bad-limit", {"limit": bad_limit})

    _, products = get_blog_post_detail(session, "bad-limit")

    assert len(products) == 3


# --------------------------------------------------------------------------- #
# WU-2 — hand-curated criteria["items"] (explicit ASIN list)
# --------------------------------------------------------------------------- #

def test_get_blog_post_detail_resolves_curated_items_in_order(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "curated", {"items": ["B1", "A1"]})

    _, products = get_blog_post_detail(session, "curated")

    assert [p.asin for p in products] == ["B1", "A1"]


def test_get_blog_post_detail_curated_skips_unknown_asins(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "curated-missing", {"items": ["A1", "ZZZZ", "B1"]})

    _, products = get_blog_post_detail(session, "curated-missing")

    assert [p.asin for p in products] == ["A1", "B1"]


def test_get_blog_post_detail_curated_skips_inactive_products(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _, _, b1 = catalog_seed
    b1.is_active = False
    session.add(b1)
    session.commit()

    _probe(monkeypatch, "curated-inactive", {"items": ["A1", "B1"]})

    _, products = get_blog_post_detail(session, "curated-inactive")

    assert [p.asin for p in products] == ["A1"]


def test_get_blog_post_detail_curated_items_respects_limit(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "curated-limited", {"items": ["B1", "A1", "A2"], "limit": 2})

    _, products = get_blog_post_detail(session, "curated-limited")

    assert [p.asin for p in products] == ["B1", "A1"]


# --------------------------------------------------------------------------- #
# WU-3 — the Christmas guide entry (hand-curated ASIN list)
# --------------------------------------------------------------------------- #

NEW_SLUG = "regalos-navidad-mas-deseados"

CURATED_ITEMS = [
    "B0B77CMJXZ", "B0FLQG3BL5", "B0DHSDHHPG", "B0CN41GMDK", "B0DRCZ7YL2",
    "B0D9LNMRB6", "B0FXB1RNCM", "B0FQNWG1YX", "B07Q7463M7", "B0CHFHK76L",
    "B08CGQZ7ND", "B09FK88YSH", "B09XHTR4RP", "B0CJVTDTB1", "B0B8ZMMV2H",
    "B09C1ZT1TQ", "B0FPQRM6MS", "B0D2D4M1VG", "B0FZB7CGCK", "B07MCD3WVG",
    "B07BB2MBNC", "B0DT4RPCK9", "B08L9HVWT3", "B0DHNYMK86", "8434439689",
    "B0F5HPS9HW", "B0CB4JY5DV",
]


def test_christmas_guide_is_configured():
    from blog_config import BLOG_POSTS

    post = next((p for p in BLOG_POSTS if p["slug"] == NEW_SLUG), None)

    assert post is not None
    assert post["criteria"] == {"items": CURATED_ITEMS}
    assert post["hero_image"] is None
    assert post["title"]
    assert post["description"]


def test_christmas_guide_renders_a_curated_product(client, session):
    from datetime import datetime

    from catalog import normalize_text
    from models import Product

    asin = "B0FQNWG1YX"
    session.add(Product(
        asin=asin,
        title="Proyector de estrellas",
        title_normalized=normalize_text("Proyector de estrellas"),
        image_url="https://cdn.example/estrellas.jpg",
        url=f"https://www.amazon.es/dp/{asin}",
        category="Iluminación",
        category_slug="iluminacion",
        price_numeric=10.44,
        price_raw="10,44 €",
        scraped_at=datetime(2026, 1, 1),
    ))
    session.commit()

    response = client.get(f"/blog/{NEW_SLUG}")

    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert len(soup.find_all("h1")) == 1
    assert soup.h1.get_text(" ", strip=True) == "Los regalos más deseados para Navidad"
    assert [item["href"] for item in soup.find_all("link", rel="canonical")] == [
        f"/blog/{NEW_SLUG}"
    ]
    assert asin in response.text


def test_christmas_guide_is_in_the_sitemap(client):
    response = client.get("/sitemap.xml")

    assert response.status_code == 200
    assert f"/blog/{NEW_SLUG}" in response.text


def test_christmas_guide_does_not_show_the_organizer_aside(client):
    soup = BeautifulSoup(client.get(f"/blog/{NEW_SLUG}").text, "html.parser")

    assert soup.main.find("a", href="/amigo-invisible") is None

