import pytest
from bs4 import BeautifulSoup
from xml.etree import ElementTree


def _robots_content(html):
    soup = BeautifulSoup(html, "html.parser")
    robots = soup.find("meta", attrs={"name": "robots"})
    return robots["content"] if robots else None


def test_join_page_is_noindexed(client):
    response = client.get("/join/ABC123")
    assert response.status_code == 200
    assert _robots_content(response.text) == "noindex, follow"


def test_robots_txt_disallows_join(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "Disallow: /join/" in response.text


LEGACY_ROUTES = ["/bestsellers", "/trends", "/most-desired"]


@pytest.mark.parametrize("path", LEGACY_ROUTES)
def test_legacy_catalog_clean_url_is_indexable(client, catalog_seed, path):
    response = client.get(path)
    assert response.status_code == 200
    assert _robots_content(response.text) is None


@pytest.mark.parametrize(
    "path",
    [
        "/bestsellers?source=trends",
        "/trends?source=bestsellers",
        "/most-desired?source=trends",
    ],
)
def test_legacy_catalog_source_param_is_noindexed(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert _robots_content(response.text) == "noindex, follow"


def test_legacy_catalog_form_submit_shape_is_noindexed(client):
    response = client.get("/bestsellers?q=&sort=relevance&source=bestsellers")
    assert response.status_code == 200
    assert _robots_content(response.text) == "noindex, follow"


def test_catalog_stays_noindexed_with_source(client):
    response = client.get("/catalog?source=trends")
    assert response.status_code == 200
    assert _robots_content(response.text) == "noindex, follow"


def test_idea_landing_page_one_stays_indexable(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas")
    assert response.status_code == 200
    assert _robots_content(response.text) is None


def test_public_profile_is_noindexed(client, test_user):
    response = client.get(f"/p/{test_user.id}")
    assert response.status_code == 200
    assert _robots_content(response.text) == "noindex, follow"


def test_sitemap_excludes_profiles_but_keeps_landings(
    client, monkeypatch, test_user, catalog_seed
):
    monkeypatch.delenv("DOMAIN_URL", raising=False)
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    text = response.text
    assert "/p/" not in text
    assert f"/p/{test_user.id}" not in text
    assert "<loc>https://regalame.app/</loc>" in text
    assert "/amigo-invisible" in text
    assert "/ideas/alimentacion-y-bebidas" in text
    assert "/blog/" in text


CATALOG_LANDINGS = ["/blog", "/bestsellers", "/trends", "/most-desired"]


@pytest.mark.parametrize("landing", CATALOG_LANDINGS)
def test_sitemap_lists_catalog_landings_exactly_once(client, monkeypatch, landing):
    monkeypatch.delenv("DOMAIN_URL", raising=False)
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ElementTree.fromstring(response.text)
    locs = [item.text for item in root.findall("{*}url/{*}loc")]
    assert locs.count(f"https://regalame.app{landing}") == 1


@pytest.mark.parametrize("landing", ["/", "/amigo-invisible", *CATALOG_LANDINGS])
def test_robots_allows_the_public_landings(client, landing):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    directives = [line.strip() for line in response.text.splitlines()]
    assert f"Disallow: {landing}" not in directives
    assert f"Disallow: {landing}/" not in directives
