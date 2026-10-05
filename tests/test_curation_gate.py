"""Phase 5 evaluation gate: stratified sampling, metric math, single-row upsert.

The gate is offline by contract: it reads persisted ``editorial_decision`` rows
plus a human-labels JSON file and makes **zero** provider calls. Strict TDD:
every behavior here was a RED test before ``jobs/evaluate_curation.py`` existed.
"""

import json
from datetime import datetime

import pytest

import curation
import curation_provider
import jobs.evaluate_curation as gate
from curation_provider import ClassificationResult
from models import Product

POLICY = curation.EDITORIAL_POLICY_VERSION
MODEL = curation_provider.EDITORIAL_PROVIDER_MODEL


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


def _decide(session, product, state, context=None):
    """Persist a *current* (matching-fingerprint) AI decision for ``product``."""
    result = ClassificationResult(state=state, context=context, reason="label")
    curation.apply_decision(session, product, result, model_id=MODEL, policy_version=POLICY)
    session.commit()


def _seed(session, rows):
    """Create products and their AI decisions.

    ``rows`` is a list of dicts ``{asin, ai, expected, context?}``. ``ai=None``
    leaves the product with no decision (an uncovered / unknown product). Returns
    ``(labels, products)`` where ``labels`` is the human-labels list payload.
    """
    products = [
        Product(
            asin=row["asin"],
            title=row["asin"],
            title_normalized=row["asin"].lower(),
            image_url=None,
            url=f"https://www.amazon.es/dp/{row['asin']}",
            category=row.get("category", "Hogar"),
            category_slug=row.get("slug", "hogar"),
            price_numeric=None,
            price_raw="N/A",
            scraped_at=datetime(2026, 1, 1),
        )
        for row in rows
    ]
    session.add_all(products)
    session.commit()
    for product in products:
        session.refresh(product)

    labels = []
    for row, product in zip(rows, products):
        if row.get("ai") is not None:
            _decide(session, product, row["ai"], row.get("context"))
        labels.append({"asin": row["asin"], "expected_state": row["expected"]})
    return labels, products


def _write_labels(tmp_path, labels, *, policy_version=POLICY, name="labels.json"):
    path = tmp_path / name
    path.write_text(
        json.dumps({"policy_version": policy_version, "labels": labels}), encoding="utf-8"
    )
    return str(path)


def _sample_rows():
    """92% agreement / ~3% excluded-leak / 8% unknown / 100% coverage."""
    rows = [{"asin": f"UNK{i}", "ai": "unknown", "expected": "unknown"} for i in range(8)]
    rows += [{"asin": f"EX{i}", "ai": "excluded", "expected": "excluded"} for i in range(32)]
    rows += [{"asin": "LEAK", "ai": "eligible", "expected": "excluded"}]
    rows += [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(52)]
    rows += [
        {"asin": f"CTX{i}", "ai": "contextual", "expected": "eligible", "context": "hogar"}
        for i in range(7)
    ]
    return rows


# --------------------------------------------------------------------------- #
# 5.1 — the exact adopted thresholds
# --------------------------------------------------------------------------- #


def test_gate_thresholds_match_the_specification():
    assert gate.GATE_MIN_OVERALL_AGREEMENT == 0.90
    assert gate.GATE_MAX_EXCLUDED_LEAK_RATIO == 0.05
    assert gate.GATE_MAX_UNKNOWN_RATIO == 0.10
    assert gate.GATE_REQUIRED_COVERAGE_RATIO == 1.0


# --------------------------------------------------------------------------- #
# 5.1 — metric math (the spec scenarios)
# --------------------------------------------------------------------------- #


def test_gate_passes_when_all_must_thresholds_hold(session, tmp_path):
    labels, _ = _seed(session, _sample_rows())

    report = gate.evaluate(session, _write_labels(tmp_path, labels))

    assert report.gate_passed is True
    assert report.overall_agreement == pytest.approx(0.92)
    assert report.excluded_leak_ratio == pytest.approx(1 / 33)
    assert report.unknown_ratio == pytest.approx(0.08)
    assert report.coverage_ratio == 1.0
    assert report.unknown_flagged is False
    assert report.model_id == MODEL
    assert report.policy_version == POLICY
    assert report.labeled_count == 100


def test_gate_fails_on_agreement(session, tmp_path):
    rows = [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(87)]
    rows += [
        {"asin": f"CTX{i}", "ai": "contextual", "expected": "eligible", "context": "hogar"}
        for i in range(13)
    ]
    labels, _ = _seed(session, rows)

    report = gate.evaluate(session, _write_labels(tmp_path, labels))

    assert report.overall_agreement == pytest.approx(0.87)
    assert report.excluded_leak_ratio == 0.0
    assert report.coverage_ratio == 1.0
    assert report.gate_passed is False


def test_gate_fails_on_excluded_leakage(session, tmp_path):
    rows = [{"asin": f"EX{i}", "ai": "excluded", "expected": "excluded"} for i in range(23)]
    rows += [{"asin": f"LK{i}", "ai": "eligible", "expected": "excluded"} for i in range(2)]
    rows += [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(70)]
    rows += [
        {"asin": f"CTX{i}", "ai": "contextual", "expected": "eligible", "context": "hogar"}
        for i in range(5)
    ]
    labels, _ = _seed(session, rows)

    report = gate.evaluate(session, _write_labels(tmp_path, labels))

    assert report.overall_agreement == pytest.approx(0.93)
    assert report.excluded_leak_ratio == pytest.approx(0.08)
    assert report.gate_passed is False


def test_gate_fails_on_incomplete_backfill(session, tmp_path):
    rows = [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(97)]
    rows += [{"asin": f"MISS{i}", "ai": None, "expected": "unknown"} for i in range(3)]
    labels, _ = _seed(session, rows)

    report = gate.evaluate(session, _write_labels(tmp_path, labels))

    assert report.coverage_ratio == pytest.approx(0.97)
    assert report.overall_agreement == pytest.approx(1.0)
    assert report.gate_passed is False


def test_gate_passes_but_flags_a_residual_unknown_share(session, tmp_path):
    rows = [{"asin": f"UNK{i}", "ai": "unknown", "expected": "unknown"} for i in range(14)]
    rows += [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(86)]
    labels, _ = _seed(session, rows)

    report = gate.evaluate(session, _write_labels(tmp_path, labels))

    assert report.unknown_ratio == pytest.approx(0.14)
    assert report.gate_passed is True
    assert report.unknown_flagged is True


# --------------------------------------------------------------------------- #
# 5.1 — evaluation is offline
# --------------------------------------------------------------------------- #


def test_the_gate_makes_no_provider_calls(session, tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("the evaluation gate must never call the provider")

    monkeypatch.setattr(curation_provider, "classify_product", explode)
    labels, _ = _seed(session, [{"asin": "EL0", "ai": "eligible", "expected": "eligible"}])

    report = gate.evaluate(session, _write_labels(tmp_path, labels))

    assert report.gate_passed is True
