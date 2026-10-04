"""Phase 4 classification job: incremental, failure-safe, bounded, resumable.

The job mirrors ``jobs/refresh_catalog.py``: a synchronous ``run(session, ...)``
seam with an injectable ``classify_fn`` plus a ``main()`` CLI. CI makes zero
provider calls and zero network calls: every test injects a recording fake
``classify_fn`` and drives an in-memory session.
"""

import re
from datetime import datetime

from sqlmodel import select

import curation
import curation_provider
import jobs.classify_catalog as job
from curation_provider import ClassificationResult
from models import EditorialDecision, Product

POLICY = curation.EDITORIAL_POLICY_VERSION
MODEL = curation_provider.EDITORIAL_PROVIDER_MODEL


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


def silent(*args, **kwargs):
    pass


def _product(session, *, asin, title, category="Hogar y cocina", slug="hogar-y-cocina",
             is_active=True):
    product = Product(
        asin=asin,
        title=title,
        title_normalized=title.lower(),
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


def _result(state="eligible", context=None, reason="ok"):
    return ClassificationResult(state=state, context=context, reason=reason)


class _Recorder:
    """Records every item; returns a per-title result (``None`` simulates failure)."""

    def __init__(self, results=None, default=None):
        self.calls = []
        self.results = dict(results or {})
        self.default = default if default is not None else _result()

    def __call__(self, item):
        self.calls.append(item)
        return self.results.get(item["title"], self.default)


def _decision(session, product_id):
    return session.exec(
        select(EditorialDecision).where(EditorialDecision.product_id == product_id)
    ).first()


def _pending(session):
    return curation.pending_products(session, policy_version=POLICY, model_id=MODEL)


# --------------------------------------------------------------------------- #
# 4.1 — incremental selection, active-only scope, dry-run
# --------------------------------------------------------------------------- #


def test_run_sends_only_pending_or_stale_products(session):
    current = _product(session, asin="CUR", title="Current")
    stale = _product(session, asin="STALE", title="Stale")
    fresh = _product(session, asin="FRESH", title="Fresh")

    # "current" already holds a decision whose fingerprint matches its inputs.
    curation.apply_decision(session, current, _result(), model_id=MODEL, policy_version=POLICY)
    # "stale" holds a decision whose stored fingerprint does not match.
    session.add(EditorialDecision(
        product_id=stale.id, state="eligible", reason="old",
        model_id=MODEL, policy_version=POLICY, input_fingerprint="deadbeef",
    ))
    session.commit()

    recorder = _Recorder()
    code = job.run(session, classify_fn=recorder, log=silent)

    assert code == 0
    assert [call["title"] for call in recorder.calls] == ["Stale", "Fresh"]


def test_run_never_sends_deactivated_products(session):
    _product(session, asin="ON", title="Active")
    _product(session, asin="OFF", title="Inactive", is_active=False)

    recorder = _Recorder()
    job.run(session, classify_fn=recorder, log=silent)

    assert [call["title"] for call in recorder.calls] == ["Active"]


def test_dry_run_makes_zero_calls_and_zero_writes(session):
    _product(session, asin="P1", title="Pending one")
    _product(session, asin="P2", title="Pending two")

    recorder = _Recorder()
    code = job.run(session, classify_fn=recorder, dry_run=True, log=silent)

    assert code == 0
    assert recorder.calls == []
    assert session.exec(select(EditorialDecision)).all() == []


def test_the_item_passed_to_classify_includes_the_category_slug(session):
    _product(session, asin="P1", title="Cafetera", category="Hogar y cocina",
             slug="hogar-y-cocina")

    recorder = _Recorder()
    job.run(session, classify_fn=recorder, log=silent)

    assert recorder.calls[0]["title"] == "Cafetera"
    assert recorder.calls[0]["category"] == "Hogar y cocina"
    assert recorder.calls[0]["category_slug"] == "hogar-y-cocina"


# --------------------------------------------------------------------------- #
# 4.2 — valid decisions are persisted (and only valid ones)
# --------------------------------------------------------------------------- #


def test_run_persists_a_valid_decision_for_a_pending_product(session):
    product = _product(session, asin="P1", title="Cafetera")

    job.run(session, classify_fn=_Recorder(default=_result(state="eligible", reason="gift")),
            log=silent)

    decision = _decision(session, product.id)
    assert decision is not None
    assert decision.state == "eligible"
    assert decision.context is None
    assert decision.reason == "gift"
    assert decision.model_id == MODEL
    assert decision.policy_version == POLICY
    assert decision.input_fingerprint == curation.compute_fingerprint(
        product.title_normalized, product.category, POLICY, MODEL
    )
    assert decision.classified_at.tzinfo is None


def test_a_contextual_decision_persists_its_context(session):
    product = _product(session, asin="P1", title="Cafetera")

    job.run(session, classify_fn=_Recorder(
        default=_result(state="contextual", context="hogar-y-cocina", reason="home only")),
        log=silent)

    decision = _decision(session, product.id)
    assert decision.state == "contextual"
    assert decision.context == "hogar-y-cocina"


def test_a_transport_failure_writes_no_row_and_leaves_the_product_unknown(session):
    product = _product(session, asin="P1", title="Cafetera")

    code = job.run(session, classify_fn=_Recorder(results={"Cafetera": None}), log=silent)

    assert code == 0
    assert _decision(session, product.id) is None
    assert curation.effective_state(_decision(session, product.id)) == "unknown"


def test_an_invalid_response_writes_no_row(session):
    product = _product(session, asin="P1", title="Cafetera")

    job.run(session, classify_fn=_Recorder(results={"Cafetera": None}), log=silent)

    assert session.exec(select(EditorialDecision)).all() == []
    assert product.id in [row.id for row in _pending(session)]


def test_a_transient_failure_retains_a_prior_valid_decision_and_leaves_it_pending(session):
    product = _product(session, asin="P1", title="Original")

    job.run(session, classify_fn=_Recorder(default=_result(state="eligible", reason="first")),
            log=silent)
    assert _decision(session, product.id).state == "eligible"

    # The title changes, so the stored fingerprint goes stale...
    product.title = "Original renamed"
    product.title_normalized = "original renamed"
    session.add(product)
    session.commit()

    # ...and the reclassification fails.
    job.run(session, classify_fn=_Recorder(results={"Original renamed": None}), log=silent)

    decision = _decision(session, product.id)
    assert decision.state == "eligible"       # prior decision retained
    assert decision.reason == "first"
    assert product.id in [row.id for row in _pending(session)]  # still pending


# --------------------------------------------------------------------------- #
# 4.2 — CLI shape
# --------------------------------------------------------------------------- #


def test_parse_args_supports_dry_run_limit_and_max_seconds():
    args = job._parse_args(["--dry-run", "--limit", "5", "--max-seconds", "60"])

    assert args.dry_run is True
    assert args.limit == 5
    assert args.max_seconds == 60


def test_main_uses_the_injected_session_and_returns_zero(session):
    _product(session, asin="P1", title="Cafetera")

    code = job.main(["--dry-run"], session=session)

    assert code == 0
