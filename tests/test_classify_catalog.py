"""Phase 4 classification job: incremental, failure-safe, bounded, resumable.

The job mirrors ``jobs/refresh_catalog.py``: a synchronous ``run(session, ...)``
seam with an injectable ``classify_fn`` plus a ``main()`` CLI. CI makes zero
provider calls and zero network calls: every test injects a recording fake
``classify_fn`` and drives an in-memory session.
"""

import os
import re
import threading
import time
from datetime import datetime

import pytest
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


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Keep the 60 rpm production default from spending real seconds in tests.

    The rate-bound test injects its own virtual ``_sleep`` and overrides this.
    """
    monkeypatch.setattr(job, "_sleep", lambda seconds: None)


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
# 4.3 — idempotent and resumable
# --------------------------------------------------------------------------- #


def test_a_completed_backfill_re_run_makes_zero_calls_and_changes_no_rows(session):
    product = _product(session, asin="P1", title="Cafetera")

    job.run(session, classify_fn=_Recorder(), log=silent)
    before = _decision(session, product.id)
    stamp, fingerprint = before.classified_at, before.input_fingerprint

    recorder = _Recorder()
    code = job.run(session, classify_fn=recorder, log=silent)

    assert code == 0
    assert recorder.calls == []
    after = _decision(session, product.id)
    assert after.classified_at == stamp
    assert after.input_fingerprint == fingerprint


def test_an_interrupted_run_resumes_without_re_requesting_committed_products(session):
    for index in range(3):
        _product(session, asin=f"P{index}", title=f"T{index}")

    first = _Recorder()
    job.run(session, classify_fn=first, limit=2, log=silent)

    assert [call["title"] for call in first.calls] == ["T0", "T1"]
    assert len(session.exec(select(EditorialDecision)).all()) == 2

    second = _Recorder()
    job.run(session, classify_fn=second, log=silent)

    assert [call["title"] for call in second.calls] == ["T2"]
    assert len(session.exec(select(EditorialDecision)).all()) == 3
    assert _pending(session) == []


def test_the_run_limit_stops_cleanly_with_exit_zero(session):
    for index in range(3):
        _product(session, asin=f"P{index}", title=f"T{index}")

    logs = []
    code = job.run(session, classify_fn=_Recorder(), limit=2, log=logs.append)

    assert code == 0
    assert any("stopped=limit" in line for line in logs)
    assert len(session.exec(select(EditorialDecision)).all()) == 2
    assert len(_pending(session)) == 1


# --------------------------------------------------------------------------- #
# 4.4 — batched commits + progress logs
# --------------------------------------------------------------------------- #


def test_progress_log_lines_report_each_batch(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_COMMIT_EVERY", 2)
    for index in range(3):
        _product(session, asin=f"P{index}", title=f"T{index}")

    logs = []
    job.run(session, classify_fn=_Recorder(), log=logs.append)

    batches = [
        line for line in logs
        if re.search(r"batch=\d+ classified=\d+ pending=\d+ elapsed=", line)
    ]
    assert len(batches) == 2
    first = re.search(r"batch=(\d+) classified=(\d+) pending=(\d+)", batches[0])
    last = re.search(r"batch=(\d+) classified=(\d+) pending=(\d+)", batches[1])
    assert first.groups() == ("1", "2", "1")
    assert last.groups() == ("2", "3", "0")


# --------------------------------------------------------------------------- #
# 4.5 — configured bounds: rate, wall time, per-run cap
# --------------------------------------------------------------------------- #


class _FakeClock:
    """A virtual monotonic clock + sleep, shared by the job and the fake provider."""

    def __init__(self, start=1000.0):
        self.t = start

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += max(0.0, seconds)


def test_default_bounds_come_from_the_environment():
    assert job.EDITORIAL_JOB_RPM == int(os.getenv("EDITORIAL_JOB_RPM", "60"))
    assert job.EDITORIAL_JOB_MAX_SECONDS == int(os.getenv("EDITORIAL_JOB_MAX_SECONDS", "3300"))
    assert job.EDITORIAL_JOB_MAX_PRODUCTS == int(os.getenv("EDITORIAL_JOB_MAX_PRODUCTS", "500"))
    assert job.EDITORIAL_JOB_COMMIT_EVERY == int(os.getenv("EDITORIAL_JOB_COMMIT_EVERY", "25"))


def test_default_concurrency_is_one_from_the_environment():
    assert job.EDITORIAL_JOB_CONCURRENCY == int(os.getenv("EDITORIAL_JOB_CONCURRENCY", "1"))


def test_request_rate_never_exceeds_the_configured_rpm(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_RPM", 60)  # one request per second
    monkeypatch.setattr(job, "EDITORIAL_JOB_MAX_SECONDS", 3600)
    clock = _FakeClock()
    monkeypatch.setattr(job, "_now", clock.now)
    monkeypatch.setattr(job, "_sleep", clock.sleep)
    for index in range(3):
        _product(session, asin=f"P{index}", title=f"T{index}")

    starts = []

    def classify(item):
        starts.append(clock.now())
        clock.t += 0.25  # 250 ms provider latency, below the 1 s interval
        return _result()

    code = job.run(session, classify_fn=classify, log=silent)

    assert code == 0
    gaps = [later - earlier for earlier, later in zip(starts, starts[1:])]
    assert len(gaps) == 2
    assert all(gap >= 1.0 - 1e-9 for gap in gaps)


def test_the_run_stops_within_the_wall_time_bound(session, monkeypatch):
    clock = _FakeClock()
    monkeypatch.setattr(job, "_now", clock.now)
    monkeypatch.setattr(job, "_sleep", clock.sleep)
    monkeypatch.setattr(job, "EDITORIAL_JOB_RPM", 0)
    for index in range(3):
        _product(session, asin=f"P{index}", title=f"T{index}")

    logs = []

    def classify(item):
        clock.t += 10.0  # each call burns 10 s of the wall-time budget
        return _result()

    code = job.run(session, classify_fn=classify, max_seconds=15, log=logs.append)

    assert code == 0
    assert any("stopped=max_seconds" in line for line in logs)
    # Two calls fit in 15 s; the third is deferred to a future run.
    assert len(session.exec(select(EditorialDecision)).all()) == 2
    assert len(_pending(session)) == 1


def test_the_per_run_product_cap_stops_cleanly(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_MAX_PRODUCTS", 2)
    for index in range(3):
        _product(session, asin=f"P{index}", title=f"T{index}")

    logs = []
    code = job.run(session, classify_fn=_Recorder(), log=logs.append)

    assert code == 0
    assert any("stopped=max_products" in line for line in logs)
    assert len(session.exec(select(EditorialDecision)).all()) == 2
    assert len(_pending(session)) == 1


def test_an_explicit_limit_overrides_the_configured_product_cap(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_MAX_PRODUCTS", 5)
    for index in range(3):
        _product(session, asin=f"P{index}", title=f"T{index}")

    job.run(session, classify_fn=_Recorder(), limit=1, log=silent)

    assert len(session.exec(select(EditorialDecision)).all()) == 1


# --------------------------------------------------------------------------- #
# 4.6 — concurrency: bounded in-flight provider calls, main-thread DB writes
# --------------------------------------------------------------------------- #


class _ConcurrencyProbe:
    """Thread-safe ``classify_fn`` recording the peak number of in-flight calls."""

    def __init__(self, *, delay=0.03, result=None):
        self.delay = delay
        self.result = result if result is not None else _result()
        self.calls = []
        self._lock = threading.Lock()
        self.in_flight = 0
        self.peak = 0

    def __call__(self, item):
        with self._lock:
            self.calls.append(item)
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
        time.sleep(self.delay)
        with self._lock:
            self.in_flight -= 1
        return self.result


def test_concurrent_run_never_exceeds_the_configured_concurrency(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_CONCURRENCY", 3)
    monkeypatch.setattr(job, "EDITORIAL_JOB_RPM", 0)
    monkeypatch.setattr(job, "EDITORIAL_JOB_MAX_SECONDS", 3600)
    for index in range(9):
        _product(session, asin=f"P{index}", title=f"T{index}")
    probe = _ConcurrencyProbe(delay=0.03)

    code = job.run(session, classify_fn=probe, log=silent)

    assert code == 0
    assert probe.peak <= 3
    assert probe.peak >= 2  # prove the calls actually overlapped
    assert len(session.exec(select(EditorialDecision)).all()) == 9


def test_concurrent_run_persists_every_valid_decision(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_CONCURRENCY", 4)
    monkeypatch.setattr(job, "EDITORIAL_JOB_RPM", 0)
    for index in range(5):
        _product(session, asin=f"P{index}", title=f"T{index}")
    recorder = _Recorder()

    code = job.run(session, classify_fn=recorder, log=silent)

    assert code == 0
    assert len(recorder.calls) == 5
    assert len(session.exec(select(EditorialDecision)).all()) == 5
    assert _pending(session) == []


def test_concurrent_dry_run_makes_zero_calls(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_CONCURRENCY", 4)
    _product(session, asin="P1", title="Cafetera")
    recorder = _Recorder()

    code = job.run(session, classify_fn=recorder, dry_run=True, log=silent)

    assert code == 0
    assert recorder.calls == []
    assert session.exec(select(EditorialDecision)).all() == []


def test_concurrent_run_respects_the_rpm_bound(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_CONCURRENCY", 3)
    monkeypatch.setattr(job, "EDITORIAL_JOB_RPM", 600)  # 100 ms between starts
    monkeypatch.setattr(job, "EDITORIAL_JOB_MAX_SECONDS", 3600)
    monkeypatch.setattr(job, "_sleep", time.sleep)  # real pacing for this test
    for index in range(5):
        _product(session, asin=f"P{index}", title=f"T{index}")
    lock = threading.Lock()
    starts = []

    def classify(item):
        with lock:
            starts.append(time.monotonic())
        time.sleep(0.25)  # in flight across several pacing slots
        return _result()

    code = job.run(session, classify_fn=classify, log=silent)

    assert code == 0
    assert len(starts) == 5
    gaps = [later - earlier for earlier, later in zip(starts, starts[1:])]
    assert all(gap >= 0.1 - 0.03 for gap in gaps), gaps


def test_concurrent_run_honors_the_product_cap_and_reports_the_stop(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_CONCURRENCY", 3)
    monkeypatch.setattr(job, "EDITORIAL_JOB_RPM", 0)
    for index in range(6):
        _product(session, asin=f"P{index}", title=f"T{index}")
    logs = []

    code = job.run(session, classify_fn=_ConcurrencyProbe(delay=0.01), limit=4,
                   log=logs.append)

    assert code == 0
    assert any("stopped=limit" in line for line in logs)
    assert len(session.exec(select(EditorialDecision)).all()) == 4
    assert len(_pending(session)) == 2


# --------------------------------------------------------------------------- #
# 4.5 — a failed product never stops the run with other work
# --------------------------------------------------------------------------- #


def test_the_job_continues_with_other_work_after_a_failure(session):
    bad = _product(session, asin="BAD", title="Bad")
    good = _product(session, asin="GOOD", title="Good")

    recorder = _Recorder(results={"Bad": None}, default=_result(state="excluded", reason="no"))
    code = job.run(session, classify_fn=recorder, log=silent)

    assert code == 0
    assert [call["title"] for call in recorder.calls] == ["Bad", "Good"]
    assert _decision(session, bad.id) is None
    assert _decision(session, good.id).state == "excluded"


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


# --------------------------------------------------------------------------- #
# 4.7 — run logs: start config, per-product activity, failures, final summary
# --------------------------------------------------------------------------- #


def _lines(logs, needle):
    return [line for line in logs if needle in line]


def test_run_logs_a_start_line_with_the_run_configuration(session):
    _product(session, asin="P1", title="Cafetera")
    _product(session, asin="P2", title="Taza")

    logs = []
    job.run(session, classify_fn=_Recorder(), log=logs.append)

    start = _lines(logs, "classify: start")
    assert len(start) == 1
    assert "pending=2" in start[0]
    assert "concurrency=1" in start[0]
    assert f"model={MODEL}" in start[0]


def test_run_logs_one_activity_line_per_classified_product(session):
    _product(session, asin="P1", title="Cafetera")

    logs = []
    job.run(session, classify_fn=_Recorder(default=_result(state="eligible")),
            log=logs.append)

    activity = _lines(logs, "product=1/1")
    assert len(activity) == 1
    assert "title='Cafetera'" in activity[0]
    assert "state=eligible" in activity[0]


def test_run_logs_a_failed_product_without_stopping_the_run(session):
    bad = _product(session, asin="BAD", title="Bad")
    good = _product(session, asin="GOOD", title="Good")

    logs = []
    job.run(session, classify_fn=_Recorder(results={"Bad": None}, default=_result()),
            log=logs.append)

    failures = _lines(logs, "result=failed")
    assert len(failures) == 1
    assert "title='Bad'" in failures[0]
    assert _decision(session, good.id) is not None


def test_run_logs_a_final_summary_with_the_failed_count(session):
    _product(session, asin="BAD", title="Bad")
    _product(session, asin="GOOD", title="Good")

    logs = []
    job.run(session, classify_fn=_Recorder(results={"Bad": None}, default=_result()),
            log=logs.append)

    summary = _lines(logs, "classify: done")
    assert len(summary) == 1
    assert "processed=2" in summary[0]
    assert "classified=1" in summary[0]
    assert "failed=1" in summary[0]


def test_concurrent_failure_logs_the_underlying_error(session, monkeypatch):
    monkeypatch.setattr(job, "EDITORIAL_JOB_CONCURRENCY", 2)
    monkeypatch.setattr(job, "EDITORIAL_JOB_RPM", 0)
    _product(session, asin="BOOM", title="Boom")
    _product(session, asin="OK", title="Ok")

    def classify(item):
        if item["title"] == "Boom":
            raise RuntimeError("provider exploded")
        return _result()

    logs = []
    code = job.run(session, classify_fn=classify, log=logs.append)

    assert code == 0
    failures = _lines(logs, "result=failed")
    assert len(failures) == 1
    assert "title='Boom'" in failures[0]
    assert "provider exploded" in failures[0]
