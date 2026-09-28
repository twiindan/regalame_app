def test_catalog_page_returns_200(client, catalog_seed):
    response = client.get("/catalog")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_catalog_with_filters_returns_200(client, catalog_seed):
    response = client.get("/catalog?q=cafe&category=alimentacion-y-bebidas&min=1&max=50&sort=price_asc")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_catalog_is_indexable_without_filters(client, catalog_seed):
    response = client.get("/catalog")
    assert "noindex" not in response.text


def test_catalog_is_noindex_with_query(client, catalog_seed):
    response = client.get("/catalog?q=cafe")
    assert "noindex" in response.text


def test_catalog_is_noindex_with_sort_or_page(client, catalog_seed):
    assert "noindex" in client.get("/catalog?sort=price_asc").text
    assert "noindex" in client.get("/catalog?page=2").text


def test_catalog_returns_real_products_without_javascript(client, catalog_seed):
    response = client.get("/catalog")
    assert "tag=" in response.text
    assert "img-a1.jpg" in response.text
