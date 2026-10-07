import pytest
from bs4 import BeautifulSoup


def _is_noindex(html):
    soup = BeautifulSoup(html, "html.parser")
    robots = soup.find("meta", attrs={"name": "robots"})
    return bool(robots and "noindex" in robots["content"])


def test_join_page_is_noindexed(client):
    response = client.get("/join/ABC123")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    robots = soup.find("meta", attrs={"name": "robots"})
    assert robots is not None
    assert robots["content"] == "noindex, follow"


def test_robots_txt_disallows_join(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert "Disallow: /join/" in response.text


LEGACY_ROUTES = ["/bestsellers", "/trends", "/most-desired"]


@pytest.mark.parametrize("path", LEGACY_ROUTES)
def test_legacy_catalog_clean_url_is_indexable(client, catalog_seed, path):
    response = client.get(path)
    assert response.status_code == 200
    assert not _is_noindex(response.text)


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
    assert _is_noindex(response.text)


def test_legacy_catalog_form_submit_shape_is_noindexed(client):
    response = client.get("/bestsellers?q=&sort=relevance&source=bestsellers")
    assert response.status_code == 200
    assert _is_noindex(response.text)


def test_catalog_stays_noindexed_with_source(client):
    response = client.get("/catalog?source=trends")
    assert response.status_code == 200
    assert _is_noindex(response.text)


def test_idea_landing_page_one_stays_indexable(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas")
    assert response.status_code == 200
    assert not _is_noindex(response.text)

