"""Focused tests for the Christmas gift guide work (roadmap item 5).

Covers the optional `criteria["limit"]` cap and the `criteria["items"]`
hand-curated list, both used by the new Christmas guide entry.
"""

import pytest
from bs4 import BeautifulSoup


def _probe(monkeypatch, slug, criteria):
    """Point services at a single synthetic post."""
    import services

    monkeypatch.setattr(services, "BLOG_POSTS", [{
        "slug": slug,
        "title": "Probe",
        "description": "Probe",
        "criteria": criteria,
        "hero_image": None,
    }])


# --------------------------------------------------------------------------- #
# WU-1 — optional criteria["limit"] cap on curated lists
# --------------------------------------------------------------------------- #

def test_get_blog_post_detail_respects_limit(session, catalog_seed, monkeypatch):
    from services import get_blog_post_detail

    _probe(monkeypatch, "limit-probe", {"limit": 2})

    post, products = get_blog_post_detail(session, "limit-probe")

    assert post is not None
    assert len(products) == 2


def test_get_blog_post_detail_without_limit_returns_all(session, catalog_seed, monkeypatch):
    from services import get_blog_post_detail

    _probe(monkeypatch, "no-limit-probe", {})

    _, products = get_blog_post_detail(session, "no-limit-probe")

    assert len(products) == 3


@pytest.mark.parametrize("bad_limit", [0, -1, "2", None])
def test_get_blog_post_detail_ignores_non_positive_or_non_int_limit(
    session, catalog_seed, monkeypatch, bad_limit
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "bad-limit", {"limit": bad_limit})

    _, products = get_blog_post_detail(session, "bad-limit")

    assert len(products) == 3


# --------------------------------------------------------------------------- #
# WU-2 — hand-curated criteria["items"] (explicit ASIN list)
# --------------------------------------------------------------------------- #

def test_get_blog_post_detail_resolves_curated_items_in_order(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "curated", {"items": ["B1", "A1"]})

    _, products = get_blog_post_detail(session, "curated")

    assert [p.asin for p in products] == ["B1", "A1"]


def test_get_blog_post_detail_curated_skips_unknown_asins(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "curated-missing", {"items": ["A1", "ZZZZ", "B1"]})

    _, products = get_blog_post_detail(session, "curated-missing")

    assert [p.asin for p in products] == ["A1", "B1"]


def test_get_blog_post_detail_curated_skips_inactive_products(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _, _, b1 = catalog_seed
    b1.is_active = False
    session.add(b1)
    session.commit()

    _probe(monkeypatch, "curated-inactive", {"items": ["A1", "B1"]})

    _, products = get_blog_post_detail(session, "curated-inactive")

    assert [p.asin for p in products] == ["A1"]


def test_get_blog_post_detail_curated_items_respects_limit(
    session, catalog_seed, monkeypatch
):
    from services import get_blog_post_detail

    _probe(monkeypatch, "curated-limited", {"items": ["B1", "A1", "A2"], "limit": 2})

    _, products = get_blog_post_detail(session, "curated-limited")

    assert [p.asin for p in products] == ["B1", "A1"]
