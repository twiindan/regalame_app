"""HEAD support on GET routes (work unit 7, SEO).

Crawler validators and uptime monitors issue HEAD requests before crawling.
FastAPI (unlike Starlette core) does not add HEAD to GET routes, so every
HTML route answered 405 to HEAD. These tests pin the contract:

- GET routes answer HEAD with 200, no body, and the same Content-Length the
  GET response reports (RFC 9110 semantics).
- POST-only routes keep rejecting HEAD with 405 and an `Allow: POST` header.
- The OpenAPI schema is unchanged: HEAD never appears as an operation.
"""

from fastapi.testclient import TestClient

# A slug that exists in services.BLOG_POSTS without any fixture setup.
REAL_BLOG_SLUG = "regalos-amigo-invisible-10-euros"


def test_head_home_returns_200_with_empty_body(client: TestClient):
    response = client.head("/")
    assert response.status_code == 200
    assert response.content == b""


def test_head_home_content_length_matches_get(client: TestClient):
    head = client.head("/")
    get = client.get("/")
    assert head.headers["content-length"] == get.headers["content-length"]
    assert int(head.headers["content-length"]) > 0


def test_head_sitemap_returns_200(client: TestClient):
    response = client.head("/sitemap.xml")
    assert response.status_code == 200
    assert response.content == b""


def test_head_blog_post_returns_200(client: TestClient):
    response = client.head(f"/blog/{REAL_BLOG_SLUG}")
    assert response.status_code == 200
    assert response.content == b""


def test_head_post_only_route_still_rejected(client: TestClient):
    response = client.head("/register")
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"


def test_openapi_schema_has_no_head_operations(client: TestClient):
    schema = client.get("/openapi.json").json()
    for path, operations in schema["paths"].items():
        assert "head" not in operations, f"HEAD leaked into schema for {path}"
