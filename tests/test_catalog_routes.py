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
