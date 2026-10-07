import sys

import pytest

from main import _parse_page_number


def test_catalog_page_returns_200(client, catalog_seed):
    response = client.get("/catalog")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_catalog_with_filters_returns_200(client, catalog_seed):
    response = client.get("/catalog?q=cafe&category=alimentacion-y-bebidas&min=1&max=50&sort=price_asc")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_catalog_is_always_noindex(client, catalog_seed):
    assert "noindex" in client.get("/catalog").text
    assert "noindex" in client.get("/catalog?q=cafe").text
    assert "noindex" in client.get("/catalog?sort=price_asc").text
    assert "noindex" in client.get("/catalog?page=2").text


def test_catalog_returns_real_products_without_javascript(client, catalog_seed):
    response = client.get("/catalog")
    assert "tag=" in response.text
    assert "img-a1.jpg" in response.text


def test_catalog_htmx_returns_partial_only(client, catalog_seed):
    response = client.get("/catalog", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "catalog-results" in response.text
    assert "<html" not in response.text


def test_catalog_empty_state_with_filters(client, catalog_seed):
    response = client.get("/catalog?q=zzzznotfound")
    assert response.status_code == 200
    assert "No hay resultados" in response.text


def test_catalog_preserves_filters_in_category_links(client, catalog_seed):
    response = client.get("/catalog?q=cafe&sort=price_asc")
    assert "/catalog?q=cafe&amp;sort=price_asc&amp;category=alimentacion-y-bebidas" in response.text


def test_legacy_catalog_routes_return_200(client, catalog_seed):
    assert client.get("/bestsellers").status_code == 200
    assert client.get("/trends").status_code == 200
    assert client.get("/most-desired").status_code == 200


def test_bestsellers_only_shows_its_source(client, catalog_seed):
    response = client.get("/bestsellers")
    assert "Café molido" in response.text
    assert "Auriculares bluetooth" not in response.text


def test_ideas_slug_returns_200_and_shows_products(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_ideas_slug_has_canonical(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=1")
    assert 'rel="canonical"' in response.text


def test_ideas_explicit_page_one_canonical_is_clean(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=1")
    assert response.status_code == 200
    assert '<link rel="canonical" href="/ideas/alimentacion-y-bebidas">' in response.text
    assert 'href="/ideas/alimentacion-y-bebidas?page=1"' not in response.text


def test_ideas_unknown_slug_returns_404(client, catalog_seed):
    response = client.get("/ideas/inexistente")
    assert response.status_code == 404


def test_ideas_unknown_slug_has_no_canonical(client, catalog_seed):
    response = client.get("/ideas/inexistente")
    assert response.status_code == 404
    assert 'rel="canonical"' not in response.text


def test_ideas_unknown_slug_404_is_noindex(client, catalog_seed):
    response = client.get("/ideas/inexistente")
    assert response.status_code == 404
    assert '<meta name="robots" content="noindex">' in response.text


def test_ideas_page_overflow_returns_404(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=99")
    assert response.status_code == 404


def test_ideas_page_zero_returns_404(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=0")
    assert response.status_code == 404


def test_ideas_page_non_integer_returns_404(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=abc")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "raw_value",
    [
        " 2 ",     # surrounding whitespace
        "+2",      # leading sign
        "1_0",     # PEP-515 underscore separator
        "\uff12",  # fullwidth digit 2 (non-ASCII)
        " 1 ",     # in-range whitespace representative
        "+1",      # in-range sign representative
        "0_1",     # in-range underscore representative
        "\uff11",  # in-range fullwidth digit 1 (non-ASCII)
        "",        # empty string
    ],
)
def test_parse_page_number_rejects_lenient_integer_forms(raw_value):
    assert _parse_page_number(raw_value) is None


def test_parse_page_number_rejects_over_long_digit_string():
    setter = getattr(sys, "set_int_max_str_digits", None)
    if setter is None:
        pytest.skip("interpreter has no int_max_str_digits cap")
    original = sys.get_int_max_str_digits()
    try:
        sys.set_int_max_str_digits(640)  # minimum allowed by CPython (>=640)
        payload = "1" * 5000
        assert len(payload) > sys.get_int_max_str_digits()
        assert _parse_page_number(payload) is None
    finally:
        sys.set_int_max_str_digits(original)


@pytest.mark.parametrize(
    "raw_page",
    [
        "%202%20",    # 2 (surrounding whitespace) — reported by review
        "%2B2",       # 2 (leading sign) — reported by review
        "1_0",        # 10 (PEP-515 underscore) — reported by review
        "%EF%BC%92",  # 2 (fullwidth digit, non-ASCII) — reported by review
        "%201%20",    # 1 (surrounding whitespace) — in range, isolates the parser
        "%2B1",       # 1 (leading sign) — in range, isolates the parser
        "0_1",        # 1 (underscore separator) — in range, isolates the parser
        "%EF%BC%91",  # 1 (fullwidth digit, non-ASCII) — in range, isolates the parser
    ],
)
def test_ideas_page_lenient_integer_forms_return_404(client, catalog_seed, raw_page):
    response = client.get(f"/ideas/alimentacion-y-bebidas?page={raw_page}")
    assert response.status_code == 404


def test_ideas_page_empty_returns_404(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=")
    assert response.status_code == 404


def test_ideas_page_over_long_digit_string_returns_404(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=" + "1" * 5000)
    assert response.status_code == 404


def test_sitemap_lists_categories(client, catalog_seed):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "/ideas/alimentacion-y-bebidas" in response.text
    assert "/catalog" not in response.text


def test_dashboard_returns_200(auth_client):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200


def test_legacy_routes_are_indexable_when_unfiltered(client, catalog_seed):
    assert "noindex" not in client.get("/bestsellers").text
    assert "noindex" not in client.get("/trends").text
    assert "noindex" not in client.get("/most-desired").text


def test_legacy_routes_become_noindex_when_filtered(client, catalog_seed):
    assert "noindex" in client.get("/bestsellers?q=cafe").text
    assert "noindex" in client.get("/bestsellers?sort=price_asc").text


def test_ideas_slug_canonical_and_pagination_links(client, session):
    from datetime import datetime

    from models import Product

    session.add_all([
        Product(asin=f"E{i:09d}", title=f"Gadget {i}", title_normalized=f"gadget {i}",
                url=f"https://www.amazon.es/dp/E{i:09d}", category="Electrónica", category_slug="electronica",
                price_numeric=float(i), price_raw=f"{i} €", scraped_at=datetime(2026, 1, 1))
        for i in range(1, 26)
    ])
    session.commit()

    page1 = client.get("/ideas/electronica")
    assert '<link rel="canonical" href="/ideas/electronica">' in page1.text
    assert 'rel="next"' in page1.text

    page2 = client.get("/ideas/electronica?page=2")
    assert '<link rel="canonical" href="/ideas/electronica?page=2">' in page2.text
    assert 'rel="prev"' in page2.text


def test_trends_htmx_returns_partial_only(client, catalog_seed):
    response = client.get("/trends", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "catalog-results" in response.text
    assert "<html" not in response.text


def test_dashboard_renders_catalog_products(auth_client, catalog_seed):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert "Café molido" in response.text
    assert "tag=" in response.text


def test_ideas_htmx_returns_partial_only(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas", headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "catalog-results" in response.text
    assert "<html" not in response.text


def test_ideas_htmx_unknown_slug_returns_404(client, catalog_seed):
    response = client.get("/ideas/inexistente", headers={"HX-Request": "true"})
    assert response.status_code == 404
    # htmx 1.9.10 has no 4xx swap configured, so an invalid HTMX request
    # intentionally receives the full-document 404 (htmx does not swap a 4xx
    # by default) rather than a fragment. Assert the full document is returned.
    assert "<html" in response.text
    assert "Página no encontrada" in response.text


def test_legacy_routes_noindex_with_price_filters(client, catalog_seed):
    assert "noindex" in client.get("/bestsellers?min=1").text
    assert "noindex" in client.get("/bestsellers?max=50").text


def test_catalog_rejects_random_sort_for_users(client, catalog_seed):
    response = client.get("/catalog?sort=random")
    assert response.status_code == 200
    assert '<option value="relevance" selected>' in response.text
