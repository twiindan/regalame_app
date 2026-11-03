"""Christmas SEO refresh work unit.

Covers: dynamic footer copyright year (T1), home CTA to the Christmas gift
guide (T2), /amigo-invisible links to both guides (T3), and the evergreen
technology post slug with a 301 from the legacy yearly slug (T4).
"""

from datetime import datetime

CHRISTMAS_GUIDE_HREF = "/blog/regalos-navidad-mas-deseados"
LEGACY_TECH_SLUG = "top-tendencias-tecnologia-2025"
EVERGREEN_TECH_SLUG = "mejores-gadgets-tecnologia"


def test_home_footer_renders_current_year(client):
    response = client.get("/")
    assert response.status_code == 200
    assert f"&copy; {datetime.now().year} Regálame." in response.text
    assert "&copy; 2025 Regálame." not in response.text


def test_home_links_to_christmas_guide(client):
    response = client.get("/")
    assert response.status_code == 200
    assert f'href="{CHRISTMAS_GUIDE_HREF}"' in response.text


def test_amigo_invisible_links_to_both_guides(client):
    response = client.get("/amigo-invisible")
    assert response.status_code == 200
    assert 'href="/blog/regalos-amigo-invisible-10-euros"' in response.text
    assert f'href="{CHRISTMAS_GUIDE_HREF}"' in response.text


def test_evergreen_tech_slug_serves_post(client, catalog_seed):
    response = client.get(f"/blog/{EVERGREEN_TECH_SLUG}")
    assert response.status_code == 200
    assert "Lo más viral en Electrónica y Gadgets" in response.text


def test_legacy_tech_slug_redirects_permanently(client):
    response = client.get(f"/blog/{LEGACY_TECH_SLUG}", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == f"/blog/{EVERGREEN_TECH_SLUG}"
