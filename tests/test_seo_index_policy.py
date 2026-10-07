from bs4 import BeautifulSoup


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
