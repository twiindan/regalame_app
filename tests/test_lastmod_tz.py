"""Postgres returns tz-aware datetimes; every lastmod value must be normalized
to naive UTC before comparison (``_newest_timestamp``) and before rendering
(``_sitemap_lastmod``). Regression test for the production 500: mixing the
MAX(Product.updated_at) (aware on Postgres) with the naive gate floor raised
``TypeError: can't compare offset-naive and offset-aware datetimes``.
"""
from datetime import datetime, timezone
from typing import Optional

from catalog import _as_naive_utc, _newest_timestamp


def test_aware_datetime_is_normalized_to_naive_utc():
    aware = datetime(2026, 4, 1, 11, 30, 0, tzinfo=timezone.utc)
    assert _as_naive_utc(aware) == datetime(2026, 4, 1, 11, 30, 0)
    assert _as_naive_utc(aware).tzinfo is None


def test_non_utc_aware_datetime_converts_to_utc_wall_time():
    aware = datetime(2026, 4, 1, 13, 30, 0, tzinfo=timezone(timedelta_hours(2)))
    assert _as_naive_utc(aware) == datetime(2026, 4, 1, 11, 30, 0)


def test_naive_datetime_passes_through():
    naive = datetime(2026, 4, 1, 9, 30, 0)
    assert _as_naive_utc(naive) is naive


def test_newest_timestamp_compares_aware_and_naive():
    """The exact production failure: aware MAX vs naive gate floor."""
    aware_max = datetime(2026, 3, 5, 6, 7, 8, tzinfo=timezone.utc)
    naive_gate = datetime(2026, 4, 1, 9, 30, 0)
    result: Optional[datetime] = _newest_timestamp(aware_max, naive_gate)
    assert result == naive_gate


def test_newest_timestamp_mixed_offsets_picks_real_newest():
    earlier = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone(timedelta_hours(1)))
    later = datetime(2026, 3, 5, 12, 30, 0, tzinfo=timezone.utc)
    # 12:30 UTC (later real instant) vs 12:00+01:00 = 11:00 UTC (earlier)
    assert _newest_timestamp(earlier, later) == datetime(2026, 3, 5, 12, 30)
    assert _newest_timestamp(later, earlier) == datetime(2026, 3, 5, 12, 30)


def timedelta_hours(n):
    from datetime import timedelta
    return timedelta(hours=n)
