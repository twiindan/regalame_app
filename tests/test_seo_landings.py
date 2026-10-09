import json
from pathlib import Path
from xml.etree import ElementTree

import pytest
from bs4 import BeautifulSoup

from blog_config import BLOG_POSTS

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


def page(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return BeautifulSoup(response.text, "html.parser")


def test_landings_have_distinct_wishlist_and_organizer_intent(client):
    home = page(client, "/")
    organizer = page(client, "/amigo-invisible")
    assert home.title.string == "Crea y comparte tu lista de regalos | Regálame"
    assert organizer.title.string == "Amigo invisible online: organiza tu sorteo | Regálame"
    for soup, heading in [(home, "Crea y comparte tu lista de regalos"),
                          (organizer, "Amigo invisible online: organiza tu sorteo")]:
        assert len(soup.find_all("h1")) == 1
        assert soup.h1.get_text(" ", strip=True) == heading
        assert soup.find("meta", attrs={"name": "description"})["content"]
        content = soup.main.get_text(" ", strip=True).lower()
        for claim in ["cualquier tienda", "privacidad garantizada", "gratis para siempre",
                      "inteligencia artificial", "con ia", "acertar siempre"]:
            assert claim not in content
    assert home.find("meta", attrs={"name": "description"})["content"] != (
        organizer.find("meta", attrs={"name": "description"})["content"]
    )
    assert home.main.find("a", href="/amigo-invisible")
    assert "Navidad" in home.main.get_text()
    assert organizer.main.find("a", href="/", string="Crear mi lista de regalos")
    assert organizer.main.find("a", href="/blog/regalos-amigo-invisible-10-euros")


def test_home_preserves_auth_forms(client):
    home = page(client, "/")
    for action, fields in [("/login", {"email", "password"}),
                           ("/register", {"name", "email", "password"})]:
        form = home.find("form", attrs={"hx-post": action})
        assert form is not None
        assert {item["name"] for item in form.find_all("input")} == fields
        assert all(item.has_attr("required") for item in form.find_all("input"))


def test_signed_in_home_redirect_and_public_organizer(auth_client):
    response = auth_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    organizer = page(auth_client, "/amigo-invisible")
    assert organizer.main.find("a", href="/dashboard")
    assert len(organizer.find_all("h1")) == 1


def test_organizer_explains_actual_workflow_and_limits(client):
    organizer = page(client, "/amigo-invisible")
    steps = organizer.main.find("ol").find_all("li", recursive=False)
    assert len(steps) == 4
    text = organizer.main.get_text(" ", strip=True)
    for phrase in ["Crea un grupo", "Invita", "cuenta", "iniciar sesión", "administrador",
                   "al menos dos participantes", "nadie se asigna a sí mismo",
                   "restricciones pueden impedir", "listas de deseos", "presupuesto es orientativo",
                   "WhatsApp comparte el enlace de invitación, no los resultados"]:
        assert phrase in text


@pytest.mark.parametrize("slug", [post["slug"] for post in BLOG_POSTS])
def test_only_relevant_blog_post_links_to_organizer(client, slug):
    soup = page(client, f"/blog/{slug}")
    links = soup.main.find_all("a", href="/amigo-invisible")
    assert len(links) == (1 if slug == "regalos-amigo-invisible-10-euros" else 0)


@pytest.mark.parametrize("domain", ["https://regalame.app", "https://landing.example/"])
@pytest.mark.parametrize("path", ["/", "/amigo-invisible"])
def test_landings_opt_in_to_clean_configured_identity(client, monkeypatch, domain, path):
    monkeypatch.setenv("DOMAIN_URL", domain)
    soup = page(client, f"{path}?q=regalos&page=2&session=ignored#fragment")
    expected = domain.rstrip("/") + path
    canonicals = soup.find_all("link", rel="canonical")
    assert [item["href"] for item in canonicals] == [expected]
    for prop in ["og:url", "twitter:url"]:
        assert [item["content"] for item in soup.find_all("meta", property=prop)] == [expected]
    assert not soup.find("meta", attrs={"name": "robots"})
    assert "noindex" not in str(soup.head)


@pytest.mark.parametrize("path", ["/", "/amigo-invisible", "/catalog", "/blog"])
def test_shared_metadata_is_valid_and_does_not_invent_claims(client, path):
    soup = page(client, path)
    schemas = [json.loads(script.string) for script in soup.find_all(
        "script", attrs={"type": "application/ld+json"}
    )]
    software = next(item for item in schemas if item["@type"] == "SoftwareApplication")
    assert software["name"] == "Regálame"
    assert software["operatingSystem"] == "Web"
    assert "aggregateRating" not in software
    assert all(item["@type"] != "FAQPage" for item in schemas)
    claims = " ".join([software["description"], soup.find(
        "meta", attrs={"name": "description"}
    )["content"], soup.find("meta", property="og:description")["content"],
        soup.find("meta", property="twitter:description")["content"]]).lower()
    for unsupported in ["con ia", "inteligencia artificial", "acertar siempre", "4.8"]:
        assert unsupported not in claims


@pytest.mark.parametrize("path,noindex", [("/catalog", True),
                                         ("/trends?q=regalo&page=2", True)])
def test_unrelated_pages_keep_canonical_and_noindex_policy(client, path, noindex):
    soup = page(client, path)
    assert not soup.find("link", rel="canonical")
    for prop in ["og:url", "twitter:url"]:
        assert [item["content"] for item in soup.find_all("meta", property=prop)] == [
            "https://regalame.app/"
        ]
    robots = soup.find("meta", attrs={"name": "robots"})
    assert bool(robots and "noindex" in robots["content"]) == noindex


def test_category_retains_its_existing_relative_canonical(client, catalog_seed):
    soup = page(client, "/ideas/alimentacion-y-bebidas")
    assert [item["href"] for item in soup.find_all("link", rel="canonical")] == [
        "/ideas/alimentacion-y-bebidas"
    ]
    assert "noindex" not in str(soup.head)


def test_default_social_image_is_a_real_asset_emitted_with_dimensions(client):
    assert (STATIC_DIR / "og-image-default.jpg").is_file()
    soup = page(client, "/")
    assert soup.find("meta", property="og:image")["content"].endswith(
        "/static/og-image-default.jpg"
    )
    assert soup.find("meta", property="og:image:width")["content"] == "1200"
    assert soup.find("meta", property="og:image:height")["content"] == "630"
    assert soup.find("meta", property="og:image:alt")["content"]
    assert soup.find("meta", property="twitter:image:alt")["content"]


def test_public_origin_helpers_use_the_configured_domain(monkeypatch):
    from main import public_origin, social_url

    monkeypatch.setenv("DOMAIN_URL", "https://landing.example/")
    assert public_origin() == "https://landing.example"
    assert social_url("/blog") == "https://landing.example/blog"
    assert social_url("https://other.example/post") == "https://other.example/post"
    assert social_url(None) == "https://landing.example/"


def test_default_social_image_uses_the_configured_origin(client, monkeypatch):
    monkeypatch.setenv("DOMAIN_URL", "https://landing.example/")
    soup = page(client, "/")
    assert soup.find("meta", property="og:image")["content"] == (
        "https://landing.example/static/og-image-default.jpg"
    )


def test_identity_tags_have_no_hardcoded_default_origin(client, monkeypatch):
    monkeypatch.setenv("DOMAIN_URL", "https://landing.example/")
    response = client.get("/")
    assert response.status_code == 200
    assert "regalame.app" not in response.text


@pytest.mark.parametrize("domain", ["https://regalame.app", "https://landing.example/"])
def test_organizer_sitemap_is_unique_and_robots_allow_public_landings(client, monkeypatch, domain):
    monkeypatch.setenv("DOMAIN_URL", domain)
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ElementTree.fromstring(response.text)
    urls = [item.text for item in root.findall("{*}url/{*}loc")]
    assert urls.count(domain.rstrip("/") + "/amigo-invisible") == 1
    assert urls.count(domain.rstrip("/") + "/") == 1
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Allow: /" in robots.text
    assert "Disallow: /amigo-invisible" not in robots.text
    assert f"Sitemap: {domain.rstrip('/')}/sitemap.xml" in robots.text
    assert client.get("/amigo-invisible/desconocido").status_code == 404


def _affiliate_anchors(soup):
    return [a for a in soup.find_all("a", href=True) if "amazon." in a["href"]]


def _assert_sponsored(anchor):
    rel = set(anchor.get("rel") or [])
    assert {"sponsored", "nofollow", "noopener"}.issubset(rel), anchor


def test_catalog_affiliate_links_are_sponsored(client, catalog_seed):
    anchors = _affiliate_anchors(page(client, "/bestsellers"))
    assert anchors
    for anchor in anchors:
        _assert_sponsored(anchor)


def test_blog_affiliate_links_are_sponsored(client, catalog_seed):
    anchors = _affiliate_anchors(page(client, "/blog/regalos-amigo-invisible-10-euros"))
    assert anchors
    for anchor in anchors:
        _assert_sponsored(anchor)


def test_dashboard_affiliate_links_are_sponsored(auth_client, catalog_seed):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    anchors = _affiliate_anchors(BeautifulSoup(response.text, "html.parser"))
    assert anchors
    for anchor in anchors:
        _assert_sponsored(anchor)


def test_wish_store_link_is_sponsored(auth_client, session, test_user):
    from models import Wish

    session.add(Wish(user_id=test_user.id, title="Regalo test",
                     url="https://www.amazon.es/dp/ZZTOP?tag=test-21"))
    session.commit()

    soup = BeautifulSoup(auth_client.get("/dashboard").text, "html.parser")
    anchor = soup.find("a", href=lambda href: href and "ZZTOP" in href)
    assert anchor is not None
    _assert_sponsored(anchor)


def test_blog_index_has_self_canonical_and_identity(client):
    from main import public_origin

    soup = page(client, "/blog")
    assert [item["href"] for item in soup.find_all("link", rel="canonical")] == ["/blog"]
    for prop in ["og:url", "twitter:url"]:
        assert [item["content"] for item in soup.find_all("meta", property=prop)] == [
            public_origin() + "/blog"
        ]


@pytest.mark.parametrize("slug", [post["slug"] for post in BLOG_POSTS])
def test_blog_post_has_self_canonical_and_identity(client, slug):
    from main import public_origin

    soup = page(client, f"/blog/{slug}")
    assert [item["href"] for item in soup.find_all("link", rel="canonical")] == [
        f"/blog/{slug}"
    ]
    for prop in ["og:url", "twitter:url"]:
        assert [item["content"] for item in soup.find_all("meta", property=prop)] == [
            public_origin() + f"/blog/{slug}"
        ]


def test_blog_post_falls_back_to_the_default_social_image_for_a_relative_hero(
        client, catalog_seed):
    from main import public_origin

    soup = page(client, "/blog/regalos-amigo-invisible-10-euros")
    default = public_origin() + "/static/og-image-default.jpg"
    assert soup.find("meta", property="og:image")["content"] == default
    assert soup.find("meta", property="twitter:image")["content"] == default
    assert soup.find("meta", property="og:image:width")["content"] == "1200"
    assert soup.find("meta", property="og:image:height")["content"] == "630"


def test_blog_post_lets_an_absolute_hero_override_og_image(client, monkeypatch):
    def fake_detail(session, slug):
        return ({
            "slug": slug,
            "title": "Regalo absoluto",
            "description": "Descripción de prueba",
            "hero_image": "https://cdn.example/hero.jpg",
        }, [])

    monkeypatch.setattr("main.get_blog_post_detail", fake_detail)
    soup = page(client, "/blog/regalos-amigo-invisible-10-euros")
    assert soup.find("meta", property="og:image")["content"] == "https://cdn.example/hero.jpg"
    assert soup.find("meta", property="twitter:image")["content"] == (
        "https://cdn.example/hero.jpg"
    )
    assert soup.find("meta", property="og:image:width") is None
    assert soup.find("meta", property="og:image:height") is None


@pytest.mark.parametrize("path", ["/bestsellers", "/trends", "/most-desired"])
def test_indexable_catalog_pages_have_self_canonical(client, catalog_seed, path):
    soup = page(client, path)
    assert [item["href"] for item in soup.find_all("link", rel="canonical")] == [path]
    assert not soup.find("meta", attrs={"name": "robots"})


# --- Per-page structured data (T3) ---

BLOG_GUIDE_SLUG = "regalos-amigo-invisible-10-euros"
BREADCRUMB_NAV_LABEL = "Migas de pan"


def _json_ld(soup):
    return [json.loads(script.string) for script in soup.find_all(
        "script", attrs={"type": "application/ld+json"}
    )]


def _schema_of_type(schemas, type_name):
    return next(item for item in schemas if item["@type"] == type_name)


def _breadcrumb_nav(soup):
    return soup.find("nav", attrs={"aria-label": BREADCRUMB_NAV_LABEL})


@pytest.mark.parametrize("path", ["/", "/amigo-invisible", "/catalog", "/blog",
                                   "/ideas/alimentacion-y-bebidas",
                                   f"/blog/{BLOG_GUIDE_SLUG}"])
def test_every_json_ld_block_is_valid_json(client, catalog_seed, path):
    soup = page(client, path)
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    assert scripts
    for script in scripts:
        assert isinstance(json.loads(script.string), dict)


def test_home_emits_website_and_organization_schema(client):
    from main import public_origin

    soup = page(client, "/")
    schemas = _json_ld(soup)
    website = _schema_of_type(schemas, "WebSite")
    organization = _schema_of_type(schemas, "Organization")
    assert website["name"] == "Regálame"
    action = website["potentialAction"]
    assert action["@type"] == "SearchAction"
    assert action["target"]["urlTemplate"] == (
        public_origin() + "/catalog?q={search_term_string}"
    )
    assert organization["name"] == "Regálame"
    assert organization["url"].startswith(public_origin())
    assert all(item["@type"] != "FAQPage" for item in schemas)


def test_blog_post_emits_blogposting_and_matching_breadcrumbs(client):
    from main import public_origin

    post = next(p for p in BLOG_POSTS if p["slug"] == BLOG_GUIDE_SLUG)
    soup = page(client, f"/blog/{BLOG_GUIDE_SLUG}")
    assert soup.find("meta", property="og:type")["content"] == "article"
    schemas = _json_ld(soup)
    blogposting = _schema_of_type(schemas, "BlogPosting")
    assert blogposting["headline"] == post["title"]
    assert blogposting["mainEntityOfPage"] == public_origin() + f"/blog/{BLOG_GUIDE_SLUG}"
    assert blogposting["author"]["@type"] == "Organization"
    assert blogposting["publisher"]["@type"] == "Organization"
    # No real publish date exists in the post data, so it must not be fabricated.
    assert "datePublished" not in blogposting
    assert "dateModified" not in blogposting

    breadcrumbs = _schema_of_type(schemas, "BreadcrumbList")
    assert [entry["name"] for entry in breadcrumbs["itemListElement"]] == [
        "Inicio", "Blog", post["title"]
    ]

    nav = _breadcrumb_nav(soup)
    assert nav is not None
    text = nav.get_text(" ", strip=True)
    assert "Inicio" in text and "Blog" in text and post["title"] in text


def test_category_emits_collectionpage_itemlist_and_breadcrumbs(client, catalog_seed):
    soup = page(client, "/ideas/alimentacion-y-bebidas")
    schemas = _json_ld(soup)
    collection = _schema_of_type(schemas, "CollectionPage")
    item_list = collection["mainEntity"]
    assert item_list["@type"] == "ItemList"
    entries = item_list["itemListElement"]
    assert entries
    assert [entry["position"] for entry in entries] == list(range(1, len(entries) + 1))
    assert "Café molido" in [entry["name"] for entry in entries]
    assert all(entry["url"] for entry in entries)

    breadcrumbs = _schema_of_type(schemas, "BreadcrumbList")
    assert [entry["name"] for entry in breadcrumbs["itemListElement"]] == [
        "Inicio", "Guía de regalos", "Alimentación y bebidas"
    ]

    nav = _breadcrumb_nav(soup)
    assert nav is not None
    text = nav.get_text(" ", strip=True)
    assert "Inicio" in text and "Guía de regalos" in text
    assert "Alimentación y bebidas" in text


@pytest.mark.parametrize("path", ["/blog", "/bestsellers", "/trends", "/most-desired"])
def test_indexable_pages_use_the_configured_origin(client, catalog_seed, monkeypatch, path):
    monkeypatch.setenv("DOMAIN_URL", "https://landing.example/")
    soup = page(client, path)
    for prop in ["og:url", "twitter:url"]:
        assert [item["content"] for item in soup.find_all("meta", property=prop)] == [
            "https://landing.example" + path
        ]
    assert [item["href"] for item in soup.find_all("link", rel="canonical")] == [path]


# --- Category landing content depth (T4) ---

CATEGORY_SLUG = "alimentacion-y-bebidas"
CATEGORY_NAME = "Alimentación y bebidas"
PRICE_GUIDE_SLUGS = {
    "regalos-amigo-invisible-10-euros",
    "regalos-baratos-menos-20-euros",
}
FORBIDDEN_COPY = ["con ia", "inteligencia artificial", "acertar siempre", "4.8"]


def test_category_page_renders_guide_faq_and_related_guides(client, catalog_seed):
    soup = page(client, f"/ideas/{CATEGORY_SLUG}")
    main_text = soup.main.get_text(" ", strip=True)

    assert f"Cómo elegir un regalo de {CATEGORY_NAME}" in main_text
    assert "Preguntas frecuentes" in main_text
    assert "Sigue con estas guías" in main_text

    guide_links = {
        anchor["href"]
        for anchor in soup.main.find_all("a", href=True)
        if anchor["href"].startswith("/blog/")
    }
    assert guide_links & {f"/blog/{slug}" for slug in PRICE_GUIDE_SLUGS}


def test_category_page_emits_faqpage_json_ld(client, catalog_seed):
    soup = page(client, f"/ideas/{CATEGORY_SLUG}")
    schemas = _json_ld(soup)
    assert any(item["@type"] == "CollectionPage" for item in schemas)

    faq = _schema_of_type(schemas, "FAQPage")
    assert faq["@context"] == "https://schema.org"
    entities = faq["mainEntity"]
    assert 2 <= len(entities) <= 3
    for entry in entities:
        assert entry["@type"] == "Question"
        assert entry["name"]
        answer = entry["acceptedAnswer"]
        assert answer["@type"] == "Answer"
        assert answer["text"]

    rendered = f"{soup.main.get_text(' ', strip=True)} {json.dumps(faq)}".lower()
    for phrase in FORBIDDEN_COPY:
        assert phrase not in rendered


def test_related_guides_prefer_a_matching_category():
    from seo_content import related_posts

    matching = related_posts("Electrónica")
    assert matching == [{
        "title": "Lo más viral en Electrónica y Gadgets",
        "slug": "top-tendencias-tecnologia-2025",
    }]
    fallback = related_posts(CATEGORY_NAME)
    assert {entry["slug"] for entry in fallback} <= PRICE_GUIDE_SLUGS
    assert fallback


def test_faqpage_is_confined_to_category_landings(client, catalog_seed):
    for path in ["/", "/amigo-invisible", "/catalog", "/blog",
                 "/blog/regalos-amigo-invisible-10-euros"]:
        soup = page(client, path)
        assert all(item["@type"] != "FAQPage" for item in _json_ld(soup)), path


def test_category_page_unknown_slug_keeps_existing_404_policy(client, catalog_seed):
    response = client.get("/ideas/categoria-inexistente")
    assert response.status_code == 404
    soup = BeautifulSoup(response.text, "html.parser")
    assert not soup.find("link", rel="canonical")
    robots = soup.find("meta", attrs={"name": "robots"})
    assert robots and "noindex" in robots["content"]
    assert all(item["@type"] != "FAQPage" for item in _json_ld(soup))
