"""Phase 1 schema foundation: editorial decision/gate models and additive migration.

These tests pin the model semantics from the design's "Interfaces / Contracts"
and the strictly-additive migration chain (down_revision ``9f1c7b2a4d3e``).
"""
import ast
import importlib.util
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

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
