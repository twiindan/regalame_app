"""Phase 5 evaluation gate: stratified sampling, metric math, single-row upsert.

The gate is offline by contract: it reads persisted ``editorial_decision`` rows
plus a human-labels JSON file and makes **zero** provider calls. Strict TDD:
every behavior here was a RED test before ``jobs/evaluate_curation.py`` existed.
"""

import json
from datetime import datetime

import pytest

import jobs.evaluate_curation as gate
from models import Product


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


def _product(session, *, asin, title=None, category="Hogar", slug="hogar", is_active=True):
    product = Product(
        asin=asin,
        title=title or asin,
        title_normalized=(title or asin).lower(),
        image_url=None,
        url=f"https://www.amazon.es/dp/{asin}",
        category=category,
        category_slug=slug,
        price_numeric=None,
        price_raw="N/A",
        scraped_at=datetime(2026, 1, 1),
        is_active=is_active,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


# --------------------------------------------------------------------------- #
# 5.1 — deterministic, category-stratified sampling
# --------------------------------------------------------------------------- #


def test_sample_products_stratifies_deterministically_across_categories(session):
    for index in range(10):
        _product(session, asin=f"A{index}", slug="cat-a", category="A")
    for index in range(6):
        _product(session, asin=f"B{index}", slug="cat-b", category="B")

    sample = gate.sample_products(session, total=4)

    slugs = [product.category_slug for product in sample]
    assert len(sample) == 4
    assert slugs.count("cat-a") == 2
    assert slugs.count("cat-b") == 2
    # Deterministic: the same session yields the identical sample.
    again = gate.sample_products(session, total=4)
    assert [product.asin for product in again] == [product.asin for product in sample]


def test_sample_products_caps_at_the_available_products(session):
    _product(session, asin="A0", slug="cat-a", category="A")
    _product(session, asin="B0", slug="cat-b", category="B")

    assert len(gate.sample_products(session, total=100)) == 2


def test_sample_products_excludes_deactivated_products(session):
    _product(session, asin="A0", slug="cat-a", category="A")
    _product(session, asin="OFF", slug="cat-a", category="A", is_active=False)

    assert [product.asin for product in gate.sample_products(session, total=100)] == ["A0"]


# --------------------------------------------------------------------------- #
# 5.1 — the human-labels contract (malformed / partially-filled rejected)
# --------------------------------------------------------------------------- #


def test_load_labels_parses_a_well_formed_file(tmp_path):
    path = tmp_path / "labels.json"
    path.write_text(
        json.dumps({"labels": [{"asin": "A1", "expected_state": "eligible"}]}),
        encoding="utf-8",
    )

    assert gate._load_labels(str(path)) == {"A1": "eligible"}


def test_load_labels_rejects_unparseable_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(gate.LabelsError):
        gate._load_labels(str(path))


def test_load_labels_rejects_an_object_without_entries(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"policy_version": "1", "labels": []}), encoding="utf-8")

    with pytest.raises(gate.LabelsError):
        gate._load_labels(str(path))


def test_load_labels_rejects_a_partially_filled_entry(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(
        json.dumps({"labels": [{"asin": "A1", "expected_state": ""}]}), encoding="utf-8"
    )

    with pytest.raises(gate.LabelsError):
        gate._load_labels(str(path))


def test_load_labels_rejects_an_out_of_enum_state(tmp_path):
    path = tmp_path / "bad-state.json"
    path.write_text(
        json.dumps({"labels": [{"asin": "A1", "expected_state": "promoted"}]}),
        encoding="utf-8",
    )

    with pytest.raises(gate.LabelsError):
        gate._load_labels(str(path))


def test_load_labels_rejects_an_entry_without_an_asin(tmp_path):
    path = tmp_path / "no-asin.json"
    path.write_text(
        json.dumps({"labels": [{"expected_state": "eligible"}]}), encoding="utf-8"
    )

    with pytest.raises(gate.LabelsError):
        gate._load_labels(str(path))
