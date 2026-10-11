"""Structure and schema tests for blog post pages (/blog/{slug}).

Covers the thematic <h2> grouping of the product grid and the per-post
JSON-LD blocks: BlogPosting completeness and the conditional FAQPage hook.
"""

import json

import pytest
from bs4 import BeautifulSoup

from catalog import normalize_text
from models import Product


def _product(asin, title, category, slug, price):
    from datetime import datetime

    return Product(
        asin=asin,
        title=title,
        title_normalized=normalize_text(title),
        image_url=f"img-{asin}.jpg",
        url=f"https://www.amazon.es/dp/{asin}",
        category=category,
        category_slug=slug,
        price_numeric=price,
        price_raw=f"{price} €" if price is not None else "N/A",
        scraped_at=datetime(2026, 1, 1),
    )


def _titles(section):
    return [item.title for item in section["items"]]


# --------------------------------------------------------------------------- #
# group_blog_products — unit tests
# --------------------------------------------------------------------------- #

def test_group_by_category_when_multiple_categories_present():
    from services import group_blog_products

    products = [
        _product("A1", "Café", "Alimentación", "alimentacion", 12.0),
        _product("B1", "Auriculares", "Electrónica", "electronica", 30.0),
        _product("A2", "Té", "Alimentación", "alimentacion", 5.0),
    ]

    groups = group_blog_products(products)

    assert [g["title"] for g in groups] == ["Alimentación", "Electrónica"]
    assert _titles(groups[0]) == ["Café", "Té"]
    assert _titles(groups[1]) == ["Auriculares"]


def test_group_by_price_tiers_for_single_category():
    from services import group_blog_products

    products = [
        _product("A1", "Barato", "Electrónica", "electronica", 5.0),
        _product("A2", "Medio", "Electrónica", "electronica", 15.0),
        _product("A3", "Caro", "Electrónica", "electronica", 60.0),
        _product("A4", "Rango alto", "Electrónica", "electronica", 25.0),
    ]

    groups = group_blog_products(products)

    assert [g["title"] for g in groups] == [
        "Menos de 10 €",
        "Entre 10 y 20 €",
        "Entre 20 y 50 €",
        "Más de 50 €",
    ]
    assert _titles(groups[0]) == ["Barato"]
    assert _titles(groups[1]) == ["Medio"]
    assert _titles(groups[2]) == ["Rango alto"]
    assert _titles(groups[3]) == ["Caro"]


def test_group_price_tiers_boundary_values_are_inclusive():
    from services import group_blog_products

    products = [
        _product("A1", "Justo 10", "Electrónica", "electronica", 10.0),
        _product("A2", "Justo 20", "Electrónica", "electronica", 20.0),
        _product("A3", "Justo 50", "Electrónica", "electronica", 50.0),
    ]

    groups = group_blog_products(products)

    assert [g["title"] for g in groups] == [
        "Entre 10 y 20 €",
        "Entre 20 y 50 €",
        "Más de 50 €",
    ]
    assert _titles(groups[0]) == ["Justo 10"]
    assert _titles(groups[1]) == ["Justo 20"]
    assert _titles(groups[2]) == ["Justo 50"]


def test_group_price_tiers_trailing_section_for_missing_price():
    from services import group_blog_products

    products = [
        _product("A1", "Con precio", "Electrónica", "electronica", 8.0),
        _product("A2", "Sin precio", "Electrónica", "electronica", None),
    ]

    groups = group_blog_products(products)

    assert [g["title"] for g in groups] == ["Menos de 10 €", "Precio variable"]
    assert _titles(groups[1]) == ["Sin precio"]


def test_group_empty_products_returns_no_sections():
    from services import group_blog_products

    assert group_blog_products([]) == []


def test_group_returns_product_objects_not_copies():
    from services import group_blog_products

    products = [_product("A1", "Café", "Alimentación", "alimentacion", 12.0)]
    groups = group_blog_products(products)

    assert groups[0]["items"][0] is products[0]


# --------------------------------------------------------------------------- #
# Page-level structure and schema
# --------------------------------------------------------------------------- #

def _json_ld(soup):
    return [json.loads(script.string) for script in soup.find_all(
        "script", attrs={"type": "application/ld+json"}
    )]


def test_blog_post_renders_h2_sections_for_mixed_categories(client, monkeypatch):
    import main
    from datetime import datetime

    products = [
        Product(
            asin="A1", title="Café", title_normalized=normalize_text("Café"),
            image_url="img-a1.jpg", url="https://www.amazon.es/dp/A1",
            category="Alimentación", category_slug="alimentacion",
            price_numeric=12.0, price_raw="12 €", scraped_at=datetime(2026, 1, 1),
        ),
        Product(
            asin="B1", title="Auriculares", title_normalized=normalize_text("Auriculares"),
            image_url="img-b1.jpg", url="https://www.amazon.es/dp/B1",
            category="Electrónica", category_slug="electronica",
            price_numeric=30.0, price_raw="30 €", scraped_at=datetime(2026, 1, 1),
        ),
    ]

    def fake_detail(session, slug):
        return {
            "slug": slug, "title": "Probe", "description": "Probe",
            "criteria": {}, "hero_image": None,
        }, products

    monkeypatch.setattr(main, "get_blog_post_detail", fake_detail)
    response = client.get("/blog/mixed-probe")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    h2s = [h2.get_text(strip=True) for h2 in soup.find_all("h2")]
    assert h2s == ["Alimentación", "Electrónica"]
    h3_cards = [h3 for h3 in soup.find_all("h3") if h3.get("title")]
    assert len(h3_cards) == 2


def test_blog_post_without_products_renders_no_sections(client, catalog_seed,
                                                        monkeypatch):
    import services

    monkeypatch.setattr(services, "BLOG_POSTS", [{
        "slug": "empty-probe",
        "title": "Probe",
        "description": "Probe",
        "criteria": {"category": "Categoria Inexistente"},
        "hero_image": None,
    }])
    response = client.get("/blog/empty-probe")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    assert not soup.find_all("h2")


def test_blog_post_emits_blogposting_with_absolute_url(client, catalog_seed):
    response = client.get("/blog/regalos-amigo-invisible-10-euros")
    assert response.status_code == 200
    schemas = _json_ld(BeautifulSoup(response.text, "html.parser"))

    posting = next(s for s in schemas if s["@type"] == "BlogPosting")
    assert posting["headline"] == "Top 15 Regalos de Amigo Invisible por menos de 10€"
    assert posting["author"] == {"@type": "Organization", "name": "Regálame"}
    assert posting["url"].startswith("https://")
    assert posting["mainEntityOfPage"].startswith("https://")


def test_blog_post_faqpage_absent_without_faq_data(client, catalog_seed):
    response = client.get("/blog/regalos-amigo-invisible-10-euros")
    schemas = _json_ld(BeautifulSoup(response.text, "html.parser"))

    assert all(s["@type"] != "FAQPage" for s in schemas)


def test_blog_post_faqpage_rendered_when_post_defines_faq(client, catalog_seed,
                                                          monkeypatch):
    import services

    monkeypatch.setattr(services, "BLOG_POSTS", [{
        "slug": "faq-probe",
        "title": "Probe",
        "description": "Probe",
        "criteria": {"category": "Electrónica"},
        "hero_image": None,
        "faq": [
            {"q": "¿Cuánto cuesta el envío?", "a": "Depende del vendedor."},
            {"q": "¿Puedo devolver un regalo?", "a": "Sí, según el vendedor."},
        ],
    }])
    response = client.get("/blog/faq-probe")
    assert response.status_code == 200
    schemas = _json_ld(BeautifulSoup(response.text, "html.parser"))

    faq = next(s for s in schemas if s["@type"] == "FAQPage")
    questions = faq["mainEntity"]
    assert [q["name"] for q in questions] == [
        "¿Cuánto cuesta el envío?",
        "¿Puedo devolver un regalo?",
    ]
    assert all(q["acceptedAnswer"]["@type"] == "Answer" for q in questions)
