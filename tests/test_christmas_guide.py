"""Focused tests for the Christmas most-wanted guide (roadmap item 5).

Covers the optional `criteria["limit"]` cap on curated lists and the new
`regalos-navidad-mas-deseados` blog entry that uses it.
"""

import pytest


# --------------------------------------------------------------------------- #
# WU-1 — optional criteria["limit"] cap on curated lists
# --------------------------------------------------------------------------- #

def _probe(monkeypatch, slug, criteria):
    """Point services at a single synthetic post and return it."""
    import services

    monkeypatch.setattr(services, "BLOG_POSTS", [{
        "slug": slug,
        "title": "Probe",
        "description": "Probe",
        "criteria": criteria,
        "hero_image": None,
    }])


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
