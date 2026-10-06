"""Phase 1 schema foundation: editorial decision/gate models and additive migration.

These tests pin the model semantics from the design's "Interfaces / Contracts"
and the strictly-additive migration chain (down_revision ``9f1c7b2a4d3e``).
"""
import ast
import importlib.util
import inspect
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import curation
from catalog import import_from_json, normalize_text
from models import EditorialDecision, EditorialGateState, Product

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"
MIGRATION_GLOB = "*_add_editorial_decision.py"
VERIFIED_HEAD = "9f1c7b2a4d3e"


def _load_migration_module():
    """Import the editorial migration module by revision file (never executes it)."""
    matches = sorted(MIGRATIONS_DIR.glob(MIGRATION_GLOB))
    assert len(matches) == 1, f"expected exactly one editorial migration, found {matches}"
    path = matches[0]
    spec = importlib.util.spec_from_file_location("editorial_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def _op_calls(source: str, func_name: str):
    """Return the alembic ``op.<attr>`` method names called inside ``func_name``."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return [
                sub.func.attr
                for sub in ast.walk(node)
                if isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id == "op"
            ]
    raise AssertionError(f"{func_name} not found in migration source")


def _create_table_names(source: str):
    """Return the first string argument of every ``op.create_table`` call."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
            and node.func.attr == "create_table"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            names.append(node.args[0].value)
    return names


def _drop_table_names(source: str):
    """Return the first string argument of every ``op.drop_table`` call."""
    names = []
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
            and node.func.attr == "drop_table"
            and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            names.append(node.args[0].value)
    return names


# --------------------------------------------------------------------------- #
# Model semantics
# --------------------------------------------------------------------------- #


def test_editorial_decision_model_tablename_is_singular():
    assert EditorialDecision.__tablename__ == "editorial_decision"


def test_editorial_gate_state_model_tablename_is_singular():
    assert EditorialGateState.__tablename__ == "editorial_gate_state"


def test_editorial_decision_model_product_id_is_unique_indexed_fk():
    table = EditorialDecision.__table__
    column = table.columns["product_id"]

    assert {fk.target_fullname for fk in column.foreign_keys} == {"product.id"}
    assert column.nullable is False

    unique_indexes = [
        index
        for index in table.indexes
        if [col.name for col in index.columns] == ["product_id"] and index.unique
    ]
    assert len(unique_indexes) == 1


def test_editorial_decision_model_ai_columns_are_nullable():
    table = EditorialDecision.__table__
    for name in (
        "state",
        "context",
        "reason",
        "model_id",
        "policy_version",
        "input_fingerprint",
        "classified_at",
    ):
        assert table.columns[name].nullable is True, name


def test_editorial_decision_model_manual_columns_are_nullable():
    table = EditorialDecision.__table__
    for name in ("manual_state", "manual_context", "manual_reason", "manual_updated_at"):
        assert table.columns[name].nullable is True, name


def test_editorial_gate_state_model_exposes_expected_columns():
    table = EditorialGateState.__table__
    expected = {
        "gate_passed",
        "coverage_ratio",
        "unknown_ratio",
        "overall_agreement",
        "excluded_leak_ratio",
        "policy_version",
        "model_id",
        "evaluated_at",
        "updated_at",
    }
    assert expected.issubset(set(table.columns.keys()))
    assert table.columns["overall_agreement"].nullable is True
    assert table.columns["excluded_leak_ratio"].nullable is True
    assert table.columns["gate_passed"].nullable is False


def test_editorial_models_timestamps_default_to_naive_utc():
    decision = EditorialDecision(product_id=1)
    assert isinstance(decision.classified_at, datetime)
    assert decision.classified_at.tzinfo is None
    # The manual side is only ever written by an explicit override.
    assert decision.manual_updated_at is None

    gate = EditorialGateState(
        gate_passed=True,
        coverage_ratio=1.0,
        unknown_ratio=0.0,
        policy_version="1",
        model_id="test-model",
    )
    assert isinstance(gate.evaluated_at, datetime)
    assert gate.evaluated_at.tzinfo is None
    assert isinstance(gate.updated_at, datetime)
    assert gate.updated_at.tzinfo is None


def test_editorial_decision_model_duplicate_product_id_raises_integrity_error(session: Session):
    product = Product(
        asin="T1",
        title="Regalo de prueba",
        title_normalized="regalo de prueba",
        url="https://www.amazon.es/dp/T1",
        category="Juguetes",
        category_slug="juguetes",
        scraped_at=datetime(2026, 1, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    session.add(EditorialDecision(product_id=product.id, state="eligible"))
    session.commit()

    session.add(EditorialDecision(product_id=product.id, state="excluded"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# --------------------------------------------------------------------------- #
# Migration chain (strictly additive)
# --------------------------------------------------------------------------- #


def test_migration_is_chained_to_the_verified_head():
    module, _ = _load_migration_module()
    assert module.down_revision == VERIFIED_HEAD
    assert module.revision and module.revision != VERIFIED_HEAD


def test_migration_upgrade_is_strictly_additive():
    _, path = _load_migration_module()
    calls = _op_calls(path.read_text(), "upgrade")

    forbidden = {
        "alter_table",
        "drop_table",
        "drop_index",
        "drop_column",
        "drop_constraint",
        "add_column",
        "execute",
    }
    assert forbidden.isdisjoint(calls), f"non-additive op in upgrade(): {calls}"
    assert calls, "upgrade() performs no operations"
    assert set(calls) == {"create_table", "create_index"}


def test_migration_creates_only_the_editorial_tables():
    _, path = _load_migration_module()
    created = _create_table_names(path.read_text())
    assert sorted(created) == ["editorial_decision", "editorial_gate_state"]


def test_migration_downgrade_drops_the_editorial_tables():
    _, path = _load_migration_module()
    dropped = _drop_table_names(path.read_text())
    assert sorted(dropped) == ["editorial_decision", "editorial_gate_state"]


# --------------------------------------------------------------------------- #
# Phase 2 — curation.py domain service
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class _Result:
    """Structural stand-in for ``curation_provider.ClassificationResult``."""

    state: str
    context: str | None
    reason: str


def _make_product(session, asin, title, *, category="Hogar y cocina", slug="hogar-y-cocina",
                  active=True):
    from models import Product

    product = Product(
        asin=asin,
        title=title,
        title_normalized=normalize_text(title),
        url=f"https://www.amazon.es/dp/{asin}",
        category=category,
        category_slug=slug,
        scraped_at=datetime(2026, 1, 1),
        is_active=active,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def _seed_gate(session, *, gate_passed, coverage_ratio, policy_version, model_id="m",
               unknown_ratio=0.0):
    gate = EditorialGateState(
        gate_passed=gate_passed,
        coverage_ratio=coverage_ratio,
        unknown_ratio=unknown_ratio,
        policy_version=policy_version,
        model_id=model_id,
    )
    session.add(gate)
    session.commit()
    session.refresh(gate)
    return gate


def _asins(session, predicate):
    rows = session.exec(
        select(Product).where(Product.is_active == True, predicate)  # noqa: E712
    ).all()
    return {product.asin for product in rows}


# --------------------------------------------------------------------------- #
# 2.1–2.2 Fingerprint rules
# --------------------------------------------------------------------------- #


def test_fingerprint_is_deterministic():
    args = ("cafetera", "Hogar y cocina", "1", "qwen3.6")
    assert curation.compute_fingerprint(*args) == curation.compute_fingerprint(*args)


def test_fingerprint_matches_the_json_canonical_sha256_formula():
    # Locks the exact serialization: json.dumps(list, ensure_ascii=False) + sha256.
    assert curation.compute_fingerprint("cafetera", "Hogar y cocina", "1", "qwen3.6") == (
        "7f184ce78dadc997558485edd36dea8eddfe4485603eae1268404819433856c0"
    )


def test_fingerprint_is_json_canonical_not_delimiter_joined():
    # A naive ",".join would alias these two inputs; canonical JSON cannot.
    assert curation.compute_fingerprint("a,b", "c", "1", "m") != (
        curation.compute_fingerprint("a", "b,c", "1", "m")
    )


def test_fingerprint_has_exactly_the_documented_inputs():
    # Price/rank/scraped_at/updated_at/is_active are not inputs: assert by construction.
    params = list(inspect.signature(curation.compute_fingerprint).parameters)
    assert params == ["title_normalized", "category", "policy_version", "model_id"]


@pytest.mark.parametrize("index", range(4))
def test_fingerprint_is_sensitive_to_each_single_input(index):
    base = ["cafetera", "Hogar y cocina", "1", "qwen3.6"]
    changed = list(base)
    changed[index] = changed[index] + "-x"
    assert curation.compute_fingerprint(*base) != curation.compute_fingerprint(*changed)


def test_editorial_states_and_policy_constants():
    assert curation.EDITORIAL_STATES == ("eligible", "contextual", "excluded", "unknown")
    assert curation.EDITORIAL_POLICY_VERSION == "2"
    assert isinstance(curation.EDITORIAL_CONTEXTS, frozenset)


# --------------------------------------------------------------------------- #
# 2.3–2.4 Pending selection, apply/upsert, manual wins, unknown semantics
# --------------------------------------------------------------------------- #


def test_pending_products_returns_only_active_products_without_a_decision(session):
    pending = _make_product(session, "P1", "Cafetera")
    _make_product(session, "P2", "Taza", active=False)

    result = curation.pending_products(session, policy_version="1", model_id="m")

    assert [product.asin for product in result] == ["P1"]
    assert result[0].id == pending.id


def test_pending_products_skips_current_fingerprint(session):
    product = _make_product(session, "P1", "Cafetera")
    curation.apply_decision(
        session, product, _Result("eligible", None, "ok"), model_id="m", policy_version="1"
    )
    session.commit()

    assert curation.pending_products(session, policy_version="1", model_id="m") == []


def test_pending_products_flags_fingerprint_mismatch(session):
    product = _make_product(session, "P1", "Cafetera")
    curation.apply_decision(
        session, product, _Result("eligible", None, "ok"), model_id="m", policy_version="1"
    )
    session.commit()

    product.title_normalized = normalize_text("Cafetera nueva")
    session.add(product)
    session.commit()

    result = curation.pending_products(session, policy_version="1", model_id="m")
    assert [p.asin for p in result] == ["P1"]


def test_pending_products_never_returns_a_manual_override(session):
    product = _make_product(session, "P1", "Cafetera")
    session.add(EditorialDecision(product_id=product.id, manual_state="eligible",
                                  manual_updated_at=datetime(2026, 1, 1)))
    session.commit()

    assert curation.pending_products(session, policy_version="1", model_id="m") == []


def test_pending_products_respects_limit(session):
    _make_product(session, "P1", "Uno")
    _make_product(session, "P2", "Dos")
    _make_product(session, "P3", "Tres")

    result = curation.pending_products(session, policy_version="1", model_id="m", limit=2)

    assert len(result) == 2


def test_apply_decision_upserts_by_product_id_and_writes_the_ai_columns(session):
    product = _make_product(session, "P1", "Cafetera")

    decision = curation.apply_decision(
        session, product, _Result("eligible", None, "good gift"),
        model_id="m", policy_version="1",
    )
    session.commit()

    assert decision.product_id == product.id
    assert decision.state == "eligible"
    assert decision.context is None
    assert decision.reason == "good gift"
    assert decision.model_id == "m"
    assert decision.policy_version == "1"
    assert decision.input_fingerprint == curation.compute_fingerprint(
        product.title_normalized, product.category, "1", "m"
    )
    assert decision.classified_at is not None

    # Re-applying updates the same row instead of creating a duplicate.
    curation.apply_decision(
        session, product, _Result("excluded", None, "nope"),
        model_id="m", policy_version="1",
    )
    session.commit()
    rows = session.exec(
        select(EditorialDecision).where(EditorialDecision.product_id == product.id)
    ).all()
    assert len(rows) == 1
    assert rows[0].state == "excluded"


def test_apply_decision_normalizes_context_for_non_contextual(session):
    product = _make_product(session, "P1", "Cafetera")

    decision = curation.apply_decision(
        session, product, _Result("eligible", "hogar-y-cocina", "ok"),
        model_id="m", policy_version="1",
    )

    assert decision.context is None


def test_apply_decision_preserves_context_for_contextual(session):
    product = _make_product(session, "P1", "Cafetera")

    decision = curation.apply_decision(
        session, product, _Result("contextual", "hogar-y-cocina", "ok"),
        model_id="m", policy_version="1",
    )

    assert decision.context == "hogar-y-cocina"


def test_apply_decision_never_writes_manual_columns(session):
    product = _make_product(session, "P1", "Cafetera")
    decision = EditorialDecision(
        product_id=product.id,
        manual_state="eligible",
        manual_context="hogar-y-cocina",
        manual_reason="operator",
        manual_updated_at=datetime(2026, 1, 1),
    )
    session.add(decision)
    session.commit()

    curation.apply_decision(
        session, product, _Result("excluded", None, "ai"), model_id="m", policy_version="1"
    )
    session.commit()
    session.refresh(decision)

    assert decision.manual_state == "eligible"
    assert decision.manual_context == "hogar-y-cocina"
    assert decision.manual_reason == "operator"
    assert decision.state == "excluded"
    assert curation.effective_state(decision) == "eligible"


def test_effective_state_resolves_unknown_and_applies_manual_wins():
    assert curation.effective_state(None) == "unknown"
    assert curation.effective_state(EditorialDecision(product_id=1)) == "unknown"
    assert curation.effective_state(
        EditorialDecision(product_id=1, state="excluded")
    ) == "excluded"
    assert curation.effective_state(
        EditorialDecision(product_id=1, state="excluded", manual_state="contextual")
    ) == "contextual"


def test_import_from_json_leaves_editorial_decision_untouched(session, tmp_path):
    product = _make_product(session, "B0CURATION", "Cafetera")
    session.add(EditorialDecision(product_id=product.id, state="eligible",
                                  input_fingerprint="fp"))
    session.commit()

    data_file = tmp_path / "bestsellers.json"
    data_file.write_text(
        '[{"url": "https://www.amazon.es/dp/B0CURATION", "title": "Cafetera nueva",'
        ' "category": "Hogar", "price": "10,00 €", "image": "x.jpg"}]'
    )
    import_from_json(session, data_files={"bestsellers": str(data_file)})
    session.expire_all()

    refreshed = session.exec(select(Product).where(Product.asin == "B0CURATION")).one()
    assert refreshed.title == "Cafetera nueva"  # the import did run

    rows = session.exec(select(EditorialDecision)).all()
    assert len(rows) == 1
    assert rows[0].state == "eligible"
    assert rows[0].input_fingerprint == "fp"


def test_manual_override_survives_import_and_re_runs(session, tmp_path):
    product = _make_product(session, "B0OVERRIDE", "Cafetera")
    # The operator overrode the AI result to eligible.
    session.add(
        EditorialDecision(
            product_id=product.id,
            state="excluded",
            manual_state="eligible",
            manual_context="hogar-y-cocina",
            manual_reason="operator",
            manual_updated_at=datetime(2026, 1, 1),
        )
    )
    session.commit()

    # A catalog import re-runs and mutates the product, but must not touch the row.
    data_file = tmp_path / "bestsellers.json"
    data_file.write_text(
        '[{"url": "https://www.amazon.es/dp/B0OVERRIDE", "title": "Cafetera nueva",'
        ' "category": "Hogar", "price": "10,00 €", "image": "x.jpg"}]'
    )
    import_from_json(session, data_files={"bestsellers": str(data_file)})
    session.expire_all()

    refreshed = session.exec(select(Product).where(Product.asin == "B0OVERRIDE")).one()
    assert refreshed.title == "Cafetera nueva"  # the import did run

    # Re-running the classifier must not spend a provider call on the override.
    assert curation.pending_products(session, policy_version="1", model_id="m") == []

    decision = session.exec(
        select(EditorialDecision).where(EditorialDecision.product_id == refreshed.id)
    ).one()
    assert decision.manual_state == "eligible"
    assert decision.manual_context == "hogar-y-cocina"
    assert decision.manual_reason == "operator"
    assert decision.manual_updated_at == datetime(2026, 1, 1)
    assert curation.effective_state(decision) == "eligible"


# --------------------------------------------------------------------------- #
# 2.5–2.6 Effective mode + enforce preconditions
# --------------------------------------------------------------------------- #


class _NoReadSession:
    """Session stand-in that fails any DB access."""

    def exec(self, *args, **kwargs):
        raise AssertionError("the off path must perform zero DB reads")


def test_effective_filter_mode_off_makes_no_db_read(monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    assert curation.effective_filter_mode(_NoReadSession()) == "off"


def test_effective_filter_mode_defaults_to_off(monkeypatch):
    # The module reads os.getenv("EDITORIAL_FILTER_MODE", "off") at import.
    assert curation.EDITORIAL_FILTER_MODE == os.getenv("EDITORIAL_FILTER_MODE", "off")


def test_effective_filter_mode_enforce_without_a_gate_row_is_off(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    assert curation.effective_filter_mode(session) == "off"


@pytest.mark.parametrize(
    "gate_kwargs",
    [
        {"gate_passed": False, "coverage_ratio": 1.0, "policy_version": "1"},
        {"gate_passed": True, "coverage_ratio": 0.97, "policy_version": "1"},
        {"gate_passed": True, "coverage_ratio": 1.0, "policy_version": "0"},
    ],
    ids=["gate-failed", "incomplete-backfill", "stale-policy"],
)
def test_effective_filter_mode_preconditions_unmet_is_off(session, monkeypatch, gate_kwargs):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, **gate_kwargs)
    assert curation.effective_filter_mode(session) == "off"


def test_effective_filter_mode_enforce_when_all_preconditions_hold(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, gate_passed=True, coverage_ratio=1.0,
               policy_version=curation.EDITORIAL_POLICY_VERSION)
    assert curation.effective_filter_mode(session) == "enforce"


# --------------------------------------------------------------------------- #
# 2.7–2.8 Visibility predicates
# --------------------------------------------------------------------------- #


def _seed_decision(session, product, state, context=None, *, manual=False):
    decision = (
        EditorialDecision(
            product_id=product.id, manual_state=state, manual_context=context,
            manual_updated_at=datetime(2026, 1, 1),
        )
        if manual
        else EditorialDecision(product_id=product.id, state=state, context=context)
    )
    session.add(decision)
    session.commit()
    return decision


def _seed_visibility_fixtures(session):
    hogar = {"category": "Hogar y cocina", "slug": "hogar-y-cocina"}
    electronica = {"category": "Electrónica", "slug": "electronica"}
    fixtures = {}
    fixtures["ELIG_H"] = _make_product(session, "ELIG_H", "Cafetera", **hogar)
    fixtures["CTX_H"] = _make_product(session, "CTX_H", "Fundas de taza", **hogar)
    fixtures["CTX_E_ON_H"] = _make_product(session, "CTX_E_ON_H", "Altavoz", **hogar)
    fixtures["ELIG_E"] = _make_product(session, "ELIG_E", "Auriculares", **electronica)
    fixtures["EXCL_H"] = _make_product(session, "EXCL_H", "Bebida alcoholica", **hogar)
    fixtures["UNK_H"] = _make_product(session, "UNK_H", "Objeto raro", **hogar)
    fixtures["NONE_H"] = _make_product(session, "NONE_H", "Sin clasificar", **hogar)

    _seed_decision(session, fixtures["ELIG_H"], "eligible")
    _seed_decision(session, fixtures["CTX_H"], "contextual", "hogar-y-cocina")
    _seed_decision(session, fixtures["CTX_E_ON_H"], "contextual", "electronica")
    _seed_decision(session, fixtures["ELIG_E"], "eligible")
    _seed_decision(session, fixtures["EXCL_H"], "excluded")
    _seed_decision(session, fixtures["UNK_H"], "unknown")
    return fixtures


def test_editorial_visibility_is_none_when_off(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    _seed_visibility_fixtures(session)
    assert curation.editorial_visibility(session) is None


def test_editorial_visibility_is_none_when_enforce_without_passing_gate(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_visibility_fixtures(session)
    assert curation.editorial_visibility(session) is None


def test_general_predicate_shows_only_eligible(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, gate_passed=True, coverage_ratio=1.0,
               policy_version=curation.EDITORIAL_POLICY_VERSION)
    _seed_visibility_fixtures(session)

    visibility = curation.editorial_visibility(session)
    assert visibility is not None
    assert _asins(session, visibility.general()) == {"ELIG_H", "ELIG_E"}


def test_context_predicate_merges_eligible_category_and_contextual_match(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, gate_passed=True, coverage_ratio=1.0,
               policy_version=curation.EDITORIAL_POLICY_VERSION)
    _seed_visibility_fixtures(session)

    visibility = curation.editorial_visibility(session)
    assert _asins(session, visibility.context_category("hogar-y-cocina")) == {"ELIG_H", "CTX_H"}
    # A contextual product whose context differs from its own category is still
    # found under its effective context (electronica), not its own slug.
    assert _asins(session, visibility.context_category("electronica")) == {
        "ELIG_E", "CTX_E_ON_H",
    }


def test_excluded_unknown_and_no_row_are_hidden_from_both_branches(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, gate_passed=True, coverage_ratio=1.0,
               policy_version=curation.EDITORIAL_POLICY_VERSION)
    _seed_visibility_fixtures(session)

    visibility = curation.editorial_visibility(session)
    hidden = {"EXCL_H", "UNK_H", "NONE_H"}
    assert _asins(session, visibility.general()).isdisjoint(hidden)
    assert _asins(session, visibility.context_category("hogar-y-cocina")).isdisjoint(hidden)


# --------------------------------------------------------------------------- #
# 2.9 visible_category_slugs
# --------------------------------------------------------------------------- #


def test_general_predicate_honours_a_manual_override(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, gate_passed=True, coverage_ratio=1.0,
               policy_version=curation.EDITORIAL_POLICY_VERSION)

    promoted = _make_product(session, "P1", "Bebida", category="Hogar", slug="hogar")
    manual_only = _make_product(session, "P2", "Adorno", category="Adornos", slug="adornos")
    # AI said excluded, the operator overrode it to eligible.
    _seed_decision(session, promoted, "excluded")
    promoted_decision = session.exec(
        select(EditorialDecision).where(EditorialDecision.product_id == promoted.id)
    ).one()
    promoted_decision.manual_state = "eligible"
    promoted_decision.manual_updated_at = datetime(2026, 1, 1)
    session.add(promoted_decision)
    # A manual-only row (no AI state) is contextual under "bebe".
    _seed_decision(session, manual_only, "contextual", "bebe", manual=True)
    session.commit()

    visibility = curation.editorial_visibility(session)
    assert _asins(session, visibility.general()) == {"P1"}
    assert _asins(session, visibility.context_category("bebe")) == {"P2"}


def test_visible_category_slugs_is_none_when_off(session, monkeypatch):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "off")
    _make_product(session, "P1", "Cafetera", category="Hogar", slug="hogar")
    assert curation.visible_category_slugs(session) is None


def test_visible_category_slugs_unions_eligible_categories_and_effective_contexts(
    session, monkeypatch
):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, gate_passed=True, coverage_ratio=1.0,
               policy_version=curation.EDITORIAL_POLICY_VERSION)

    eligible_hogar = _make_product(session, "P1", "Cafetera", category="Hogar",
                                   slug="hogar-y-cocina")
    eligible_electronica = _make_product(session, "P2", "Auriculares",
                                         category="Electrónica", slug="electronica")
    contextual_libros = _make_product(session, "P3", "Novela", category="Libros",
                                      slug="libros")
    contextual_off_category = _make_product(session, "P4", "Moldes", category="Hogar",
                                            slug="hogar-y-cocina")
    excluded_juguetes = _make_product(session, "P5", "Pistola", category="Juguetes",
                                      slug="juguetes")
    inactive_eligible = _make_product(session, "P6", "Vinilo", category="Música",
                                      slug="musica", active=False)

    _seed_decision(session, eligible_hogar, "eligible")
    _seed_decision(session, eligible_electronica, "eligible")
    _seed_decision(session, contextual_libros, "contextual", "libros")
    # Context differs from its own category: the UNION must keep the context slug.
    _seed_decision(session, contextual_off_category, "contextual", "cocina-tematica")
    _seed_decision(session, excluded_juguetes, "excluded")
    _seed_decision(session, inactive_eligible, "eligible")

    assert curation.visible_category_slugs(session) == {
        "hogar-y-cocina", "electronica", "libros", "cocina-tematica",
    }


def test_visible_category_slugs_suppresses_a_category_with_no_visible_products(
    session, monkeypatch
):
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    _seed_gate(session, gate_passed=True, coverage_ratio=1.0,
               policy_version=curation.EDITORIAL_POLICY_VERSION)

    visible = _make_product(session, "P1", "Cafetera", category="Hogar", slug="hogar")
    hidden = _make_product(session, "P2", "Pistola", category="Juguetes", slug="juguetes")
    _seed_decision(session, visible, "eligible")
    _seed_decision(session, hidden, "excluded")

    assert curation.visible_category_slugs(session) == {"hogar"}
