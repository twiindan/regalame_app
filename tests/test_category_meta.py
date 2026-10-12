"""Query-driven SEO titles and metas on ``/ideas/{slug}`` landings.

Covers:
- categories with a ``meta`` entry emit a title/description pair that is
  distinct from the generic pattern shared by all landings;
- categories without ``meta`` (no entry, or entry without the field) keep
  the exact current generic fallback;
- no title exceeds 70 chars and no description exceeds 160 chars;
- the 12 titles are unique among themselves.
"""

import re
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

import seo_content
from seo_content import CATEGORY_CONTENT, category_meta

_FALLBACK_NAME = "CD y vinilos"
_FALLBACK_SLUG = "cd-y-vinilos"

_META_SLUGS = sorted(
    slug for slug, entry in CATEGORY_CONTENT.items() if entry.get("meta")
)


def _generic_title(name):
    return f"Las Mejores Ideas de Regalo para {name} (2026) | Regálame"


def _generic_description(name):
    return (
        f"Encuentra el regalo perfecto en nuestra selección de {name}. "
        "Comparativa de precios y tendencias para el Amigo Invisible y cumpleaños."
    )


def test_meta_present_for_the_twelve_content_categories():
    assert len(_META_SLUGS) == 12
    assert set(_META_SLUGS) == set(CATEGORY_CONTENT)


@pytest.mark.parametrize("slug", _META_SLUGS)
def test_category_meta_lookup_returns_title_and_description(slug):
    entry = CATEGORY_CONTENT[slug]
    meta = category_meta(entry["name"])
    assert meta == {
        "title": entry["meta"]["title"],
        "description": entry["meta"]["description"],
    }
    # Slug form resolves to the same entry (same lookup as guide/FAQ).
    assert category_meta(slug) == meta


@pytest.mark.parametrize("slug", _META_SLUGS)
def test_meta_titles_differ_from_the_generic_pattern(slug):
    entry = CATEGORY_CONTENT[slug]
    title = entry["meta"]["title"]
    assert title != _generic_title(entry["name"])
    assert "Las Mejores Ideas de Regalo para" not in title


def test_meta_titles_are_unique():
    titles = [CATEGORY_CONTENT[slug]["meta"]["title"] for slug in _META_SLUGS]
    assert len(titles) == len(set(titles))


@pytest.mark.parametrize("slug", _META_SLUGS)
def test_meta_title_length_is_bounded(slug):
    assert len(CATEGORY_CONTENT[slug]["meta"]["title"]) <= 70


@pytest.mark.parametrize("slug", _META_SLUGS)
def test_meta_description_length_is_bounded(slug):
    description = CATEGORY_CONTENT[slug]["meta"]["description"]
    assert len(description) <= 160


def test_fallback_without_entry_returns_none():
    assert category_meta(_FALLBACK_NAME) is None
    assert category_meta(_FALLBACK_SLUG) is None
    assert category_meta("") is None
    assert category_meta(None) is None


def test_fallback_without_meta_field_returns_none(monkeypatch):
    stripped = {
        slug: {k: v for k, v in entry.items() if k != "meta"}
        for slug, entry in CATEGORY_CONTENT.items()
    }
    monkeypatch.setattr(seo_content, "CATEGORY_CONTENT", stripped)
    assert category_meta("Electrónica") is None


def _seed_vinilos(session):
    from models import Product, ProductList

    product = Product(
        asin="C1", title="Vinilo de colección",
        title_normalized="vinilo de coleccion",
        image_url="img-c1.jpg", url="https://www.amazon.es/dp/C1",
        category=_FALLBACK_NAME, category_slug=_FALLBACK_SLUG,
        price_numeric=None, price_raw="N/A",
        scraped_at=datetime(2026, 2, 1), updated_at=datetime(2026, 2, 1),
    )
    session.add(product)
    session.commit()
    session.add(ProductList(product_id=product.id, list_key="trends", rank=9))
    session.commit()


def test_rendered_landing_uses_meta_title_and_description(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    meta = category_meta("Alimentación y bebidas")
    assert soup.title.string == meta["title"]
    assert soup.find("meta", attrs={"name": "description"})["content"] == (
        meta["description"]
    )
    assert soup.find("meta", attrs={"name": "description"})["content"] != (
        _generic_description("Alimentación y bebidas")
    )


def test_rendered_landing_keeps_generic_fallback(client, session, catalog_seed):
    _seed_vinilos(session)
    response = client.get(f"/ideas/{_FALLBACK_SLUG}")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.title.string == _generic_title(_FALLBACK_NAME)
    assert soup.find("meta", attrs={"name": "description"})["content"] == (
        _generic_description(_FALLBACK_NAME)
    )
