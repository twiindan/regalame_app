"""Tests for the Amazon WebP URL rewrite helper and its Jinja filter wiring.

Strict TDD: these were written and observed failing (RED) before
``image_urls.py`` existed and before the ``amazon_webp`` filter was registered.
"""

from datetime import datetime

import pytest

from image_urls import amazon_webp_url

# A real Amazon product URL shape: the transform segment ends with ``_`` and the
# file ends with ``.jpg``, so the rewritten form carries a doubled ``__FMwebp_``.
AC_UL600 = "https://images-eu.ssl-images-amazon.com/images/I/718aQ--fGIL._AC_UL600_SR600,400_.jpg"
AC_UL300 = "https://images-eu.ssl-images-amazon.com/images/I/71ABCdef._AC_UL300_SR300,200_.jpg"
MEDIA_AC = "https://m.media-amazon.com/images/I/91xyz._AC_SL1500_.jpg"


def test_rewrites_ac_ul600_url():
    result = amazon_webp_url(AC_UL600)
    # The original already ended with ``_``, so the marker yields ``__FMwebp_``.
    assert result.endswith("__FMwebp_.jpg")
    assert result.count("_FMwebp_") == 1


def test_rewrites_ac_ul300_url():
    result = amazon_webp_url(AC_UL300)
    assert "_FMwebp_.jpg" in result
    assert result.count("_FMwebp_") == 1


def test_rewrites_media_amazon_host():
    result = amazon_webp_url(MEDIA_AC)
    assert result != MEDIA_AC
    assert "_FMwebp_.jpg" in result
    assert result.count("_FMwebp_") == 1


def test_rewrite_is_idempotent():
    once = amazon_webp_url(AC_UL600)
    assert amazon_webp_url(once) == once


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "img-a1.jpg",
        "https://img.example/1.jpg",
        "https://cdn.example/hero.jpg",
        "https://www.amazon.es/dp/ZZTOP",
        # Amazon image host but no ``._AC_`` transform segment.
        "https://images-eu.ssl-images-amazon.com/images/I/718aQ--fGIL._SL600_.jpg",
        # Amazon ``._AC_`` transform but not a ``.jpg`` file.
        "https://images-eu.ssl-images-amazon.com/images/I/718aQ--fGIL._AC_UL600_SR600,400_.png",
    ],
)
def test_passthrough_returns_original(value):
    result = amazon_webp_url(value)
    assert result == value
    if isinstance(value, str):
        assert result is value


def test_catalog_img_uses_webp_but_manual_image_keeps_original(auth_client, session):
    from catalog import normalize_text
    from models import Product

    session.add(
        Product(
            asin="AMZ1",
            title="Producto Amazon",
            title_normalized=normalize_text("Producto Amazon"),
            image_url=AC_UL600,
            url="https://www.amazon.es/dp/AMZ1",
            category="Varios",
            category_slug="varios",
            price_numeric=9.99,
            price_raw="9,99 €",
            scraped_at=datetime(2026, 1, 1),
        )
    )
    session.commit()

    response = auth_client.get("/catalog")
    assert response.status_code == 200
    body = response.text

    webp = amazon_webp_url(AC_UL600)
    assert webp != AC_UL600

    # The rendered <img src> is rewritten to the WebP variant ...
    assert f'src="{webp}"' in body
    # ... while the persisted-value hidden input keeps the ORIGINAL URL.
    assert f'name="manual_image" value="{AC_UL600}"' in body
    # And the plain original never leaks into an <img src>.
    assert f'src="{AC_UL600}"' not in body
