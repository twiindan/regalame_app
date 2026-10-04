"""Phase 5 evaluation gate: stratified sampling, metric math, single-row upsert.

The gate is offline by contract: it reads persisted ``editorial_decision`` rows
plus a human-labels JSON file and makes **zero** provider calls. Strict TDD:
every behavior here was a RED test before ``jobs/evaluate_curation.py`` existed.
"""

import json
from datetime import datetime

import pytest
from sqlmodel import select

import curation
import curation_provider
import jobs.evaluate_curation as gate
from curation_provider import ClassificationResult
from models import EditorialGateState, Product

POLICY = curation.EDITORIAL_POLICY_VERSION
MODEL = curation_provider.EDITORIAL_PROVIDER_MODEL


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


def _silent(*args, **kwargs):
    pass


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


# --------------------------------------------------------------------------- #
# 5.2 — the single-row gate upsert, template output, and CLI
# --------------------------------------------------------------------------- #


def test_a_successful_run_upserts_exactly_one_gate_row(session, tmp_path):
    labels, _ = _seed(
        session, [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(10)]
    )

    code = gate.run(session, labels_path=_write_labels(tmp_path, labels), log=_silent)

    assert code == 0
    rows = session.exec(select(EditorialGateState)).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.gate_passed is True
    assert row.coverage_ratio == 1.0
    assert row.unknown_ratio == 0.0
    assert row.overall_agreement == 1.0
    assert row.excluded_leak_ratio == 0.0
    assert row.policy_version == POLICY
    assert row.model_id == MODEL
    assert row.evaluated_at.tzinfo is None


def test_a_re_run_updates_the_same_single_row(session, tmp_path):
    labels, _ = _seed(
        session, [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(10)]
    )
    gate.run(session, labels_path=_write_labels(tmp_path, labels), log=_silent)

    disagreeing = [{"asin": "EL0", "expected_state": "excluded"}]
    code = gate.run(
        session,
        labels_path=_write_labels(tmp_path, disagreeing, name="second.json"),
        log=_silent,
    )

    assert code == 0
    rows = session.exec(select(EditorialGateState)).all()
    assert len(rows) == 1
    assert rows[0].gate_passed is False


def test_a_malformed_labels_file_exits_1_without_writing(session, tmp_path):
    _product(session, asin="EL0")
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")

    code = gate.run(session, labels_path=str(path), log=_silent)

    assert code == 1
    assert session.exec(select(EditorialGateState)).all() == []


def test_a_partially_filled_labels_file_exits_1_without_writing(session, tmp_path):
    _product(session, asin="EL0")
    path = tmp_path / "partial.json"
    path.write_text(
        json.dumps({"labels": [{"asin": "EL0", "expected_state": ""}]}), encoding="utf-8"
    )

    code = gate.run(session, labels_path=str(path), log=_silent)

    assert code == 1
    assert session.exec(select(EditorialGateState)).all() == []


def test_run_without_labels_writes_the_label_template(session, tmp_path):
    for index in range(3):
        _product(session, asin=f"P{index}", slug="cat", category="Cat")
    out = tmp_path / "sample.json"

    code = gate.run(session, sample_out=str(out), log=_silent)

    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["policy_version"] == POLICY
    assert [entry["expected_state"] for entry in payload["labels"]] == ["", "", ""]
    assert {entry["asin"] for entry in payload["labels"]} == {"P0", "P1", "P2"}
    assert session.exec(select(EditorialGateState)).all() == []


def test_a_run_makes_no_provider_calls(session, tmp_path, monkeypatch):
    def explode(*args, **kwargs):
        raise AssertionError("the evaluation gate must never call the provider")

    monkeypatch.setattr(curation_provider, "classify_product", explode)
    labels, _ = _seed(session, [{"asin": "EL0", "ai": "eligible", "expected": "eligible"}])

    code = gate.run(session, labels_path=_write_labels(tmp_path, labels), log=_silent)

    assert code == 0


# --------------------------------------------------------------------------- #
# 5.3 — the gate feeds the enforce preconditions (join with task 2.6)
# --------------------------------------------------------------------------- #


def test_a_passing_gate_makes_enforce_effective(session, tmp_path, monkeypatch):
    labels, _ = _seed(
        session, [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(20)]
    )
    assert gate.run(session, labels_path=_write_labels(tmp_path, labels), log=_silent) == 0

    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")

    assert curation.effective_filter_mode(session) == "enforce"


def test_an_incomplete_backfill_keeps_enforce_off(session, tmp_path, monkeypatch):
    rows = [{"asin": f"EL{i}", "ai": "eligible", "expected": "eligible"} for i in range(19)]
    rows += [{"asin": "MISS", "ai": None, "expected": "unknown"}]
    labels, _ = _seed(session, rows)
    assert gate.run(session, labels_path=_write_labels(tmp_path, labels), log=_silent) == 0

    row = session.exec(select(EditorialGateState)).first()
    assert row.coverage_ratio < 1.0
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")

    assert curation.effective_filter_mode(session) == "off"


# --------------------------------------------------------------------------- #
# 5.2 — CLI shape
# --------------------------------------------------------------------------- #


def test_parse_args_supports_labels_and_sample_out():
    args = gate._parse_args(["--labels", "l.json", "--sample-out", "s.json"])

    assert args.labels == "l.json"
    assert args.sample_out == "s.json"


def test_main_uses_the_injected_session(session, tmp_path):
    labels, _ = _seed(session, [{"asin": "EL0", "ai": "eligible", "expected": "eligible"}])
    path = _write_labels(tmp_path, labels)

    code = gate.main(["--labels", path], session=session)

    assert code == 0
    assert len(session.exec(select(EditorialGateState)).all()) == 1
