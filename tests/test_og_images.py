"""Work unit 10: per-page OG images for category landings and listings.

The first product of a listing whose ``image_url`` is an absolute http(s) URL
becomes the page ``og:image``/``twitter:image``. Pages without any usable
product image keep the default social asset with its 1200x630 dimensions, and
the alt text becomes page-specific whenever a real product photo is used.
"""
import json
from datetime import datetime

from bs4 import BeautifulSoup

from catalog import normalize_text
from models import Product, ProductList

DEFAULT_SUFFIX = "/static/og-image-default.jpg"
GENERIC_ALT = "Regálame: listas de regalos y amigo invisible"

IMG_FIRST = "https://m.media-amazon.com/images/I/first-product.jpg"
IMG_SECOND = "https://m.media-amazon.com/images/I/second-product.jpg"


def _soup(client, path):
    response = client.get(path)
    assert response.status_code == 200
    return BeautifulSoup(response.text, "html.parser")


def _make_product(session, asin, slug, image, *, list_key=None, rank=1):
    title = f"Producto {asin}"
    product = Product(
        asin=asin,
        title=title,
        title_normalized=normalize_text(title),
        image_url=image,
        url=f"https://www.amazon.es/dp/{asin}",
        category="Electrónica",
        category_slug=slug,
        price_numeric=19.9,
        price_raw="19,9 €",
        scraped_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    if list_key:
        session.add(ProductList(product_id=product.id, list_key=list_key, rank=rank))
        session.commit()
    return product


def test_category_landing_uses_the_first_product_with_an_absolute_image(client, session):
    _make_product(session, "B00NOIMG1", "gadgets", None)
    _make_product(session, "B00NOIMG2", "gadgets", IMG_FIRST)
    _make_product(session, "B00NOIMG3", "gadgets", IMG_SECOND)

    soup = _soup(client, "/ideas/gadgets")
    assert soup.find("meta", property="og:image")["content"] == IMG_FIRST
    assert soup.find("meta", property="twitter:image")["content"] == IMG_FIRST


def test_category_landing_without_usable_images_keeps_the_default(client, catalog_seed):
    # catalog_seed only ships relative image paths, which must be ignored.
    soup = _soup(client, "/ideas/alimentacion-y-bebidas")
    assert soup.find("meta", property="og:image")["content"].endswith(DEFAULT_SUFFIX)
    assert soup.find("meta", property="og:image:width")["content"] == "1200"
    assert soup.find("meta", property="og:image:height")["content"] == "630"


def test_listing_without_usable_images_keeps_the_default_dimensions(client, catalog_seed):
    soup = _soup(client, "/bestsellers")
    assert soup.find("meta", property="og:image")["content"].endswith(DEFAULT_SUFFIX)
    assert soup.find("meta", property="og:image:width")["content"] == "1200"
    assert soup.find("meta", property="og:image:height")["content"] == "630"
    assert soup.find("meta", property="og:image:alt")["content"] == GENERIC_ALT


def test_specific_product_image_omits_width_and_height(client, session):
    _make_product(session, "B00NOIMG1", "gadgets", IMG_FIRST)

    soup = _soup(client, "/ideas/gadgets")
    assert soup.find("meta", property="og:image")["content"] == IMG_FIRST
    assert soup.find("meta", property="og:image:width") is None
    assert soup.find("meta", property="og:image:height") is None
    # The alt describes the page, not the generic site tagline.
    assert soup.find("meta", property="og:image:alt")["content"] == (
        "Ideas de regalo: Electrónica"
    )
    assert soup.find("meta", property="twitter:image:alt")["content"] == (
        "Ideas de regalo: Electrónica"
    )


def test_bestsellers_listing_uses_first_ranked_product_image(client, session):
    _make_product(session, "B00BEST2", "gadgets", IMG_SECOND, list_key="bestsellers", rank=2)
    _make_product(session, "B00BEST1", "gadgets", IMG_FIRST, list_key="bestsellers", rank=1)

    soup = _soup(client, "/bestsellers")
    assert soup.find("meta", property="og:image")["content"] == IMG_FIRST
    assert soup.find("meta", property="og:image:width") is None
    assert soup.find("meta", property="og:image:alt")["content"] == (
        "Ideas de regalo: Top Ventas & Ideas"
    )


def test_blog_posting_json_ld_stays_intact(client, catalog_seed):
    soup = _soup(client, "/blog/regalos-amigo-invisible-10-euros")
    schemas = [
        json.loads(script.string)
        for script in soup.find_all("script", attrs={"type": "application/ld+json"})
    ]
    posting = next(s for s in schemas if s["@type"] == "BlogPosting")
    assert posting["author"] == {"@type": "Organization", "name": "Regálame"}
    assert posting["url"].startswith("https://")
