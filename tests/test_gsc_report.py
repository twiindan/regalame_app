import sys
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from gsc_report import aggregate_by, is_seasonal  # noqa: E402


def _row(query, page="https://regalame.app/", clicks=0, impressions=1, position=10.0):
    return {
        "query": query,
        "page": page,
        "clicks": clicks,
        "impressions": impressions,
        "position": position,
    }


def test_is_seasonal_matches_stems_case_insensitively():
    assert is_seasonal("Amigo Invisible online")
    assert is_seasonal("regalos para niños")
    assert is_seasonal("IDEAS DE NAVIDAD")
    assert not is_seasonal("minecraft skins")


def test_aggregate_by_query_sums_and_weights():
    rows = [
        _row("amigo invisible", page="/a", clicks=2, impressions=100, position=5.0),
        _row("amigo invisible", page="/b", clicks=1, impressions=10, position=7.0),
        _row("otra cosa", page="/a", clicks=0, impressions=10, position=20.0),
    ]
    agg = {a["query"]: a for a in aggregate_by(rows, "query")}
    mine = agg["amigo invisible"]
    assert mine["clicks"] == 3
    assert mine["impressions"] == 110
    assert mine["ctr"] == pytest.approx(3 / 110)
    assert mine["position"] == pytest.approx((5.0 * 100 + 7.0 * 10) / 110)  # weighted


def test_aggregate_by_zero_impressions_is_safe():
    agg = aggregate_by([_row("q", clicks=0, impressions=0, position=0.0)], "query")
    assert agg[0]["position"] == 0.0
    assert agg[0]["ctr"] == 0.0


from gsc_report import build_low_ctr, build_opportunities, build_per_url, build_top_queries  # noqa: E402


def _mix():
    return [
        _row("amigo invisible online", clicks=1, impressions=50, position=8.0),
        _row("amigo invisible", clicks=0, impressions=30, position=12.0),
        _row("regalos navidad", clicks=5, impressions=200, position=3.0),
        _row("minecraft", clicks=0, impressions=90, position=9.0),
        _row("amigo invisible app", clicks=0, impressions=15, position=2.0),
        _row("regalo barato", clicks=0, impressions=12, position=6.5),
        _row("amigo invisible 5", clicks=0, impressions=11, position=5.0),
        _row("amigo invisible 20", clicks=0, impressions=11, position=20.0),
        _row("amigo invisible quiet", clicks=0, impressions=5, position=10.0),
        _row("office chair", clicks=10, impressions=100, position=3.0),
    ]


def test_top_queries_filters_non_seasonal_and_sorts_by_impressions():
    top = build_top_queries(_mix())
    assert [t["query"] for t in top][:3] == ["regalos navidad", "amigo invisible online", "amigo invisible"]
    assert all("minecraft" != t["query"] for t in top)


def test_opportunities_window_is_half_open():
    hits = build_opportunities(_mix(), min_impressions=10)
    queries = [h["query"] for h in hits]
    assert "amigo invisible" in queries        # position 12
    assert "amigo invisible online" in queries  # position 8
    assert "regalos navidad" not in queries     # position 3 (< 5)
    assert "amigo invisible app" not in queries  # position 2 (< 5)
    assert "amigo invisible 5" in queries        # exactly 5.0 is included (low bound)
    assert "amigo invisible 20" not in queries   # exactly 20.0 is excluded (high bound)
    assert "amigo invisible quiet" not in queries  # impressions < min_impressions


def test_low_ctr_flags_good_position_low_clicks():
    hits = build_low_ctr(_mix())
    queries = [h["query"] for h in hits]
    assert "amigo invisible app" in queries     # position 2, ctr 0
    assert "minecraft" not in queries           # position 9 > 6, excluded
    assert "office chair" not in queries         # ctr 0.10 >= threshold: the ctr filter bites


def test_low_ctr_respects_clicks_not_stems():
    # 5/200 = 0.025 < 0.03 but has clicks; keep the view honest: any query under
    # the ctr threshold at good position is a candidate. "regalos navidad" HAS
    # 5 clicks so it still appears; assert exactly that.
    hits = build_low_ctr(_mix())
    queries = [h["query"] for h in hits]
    assert "regalos navidad" in queries


def test_per_url_aggregates_pages():
    rows = [
        _row("a", page="/p1", clicks=1, impressions=10, position=4.0),
        _row("b", page="/p1", clicks=1, impressions=30, position=8.0),
        _row("c", page="/p2", clicks=0, impressions=5, position=11.0),
    ]
    agg = {a["page"]: a for a in build_per_url(rows)}
    assert agg["/p1"]["impressions"] == 40
    assert agg["/p1"]["clicks"] == 2
    assert round(agg["/p1"]["position"], 2) == 7.0
    assert agg["/p2"]["impressions"] == 5


def test_views_empty_rows_return_empty_lists():
    assert build_top_queries([]) == []
    assert build_opportunities([]) == []
    assert build_low_ctr([]) == []
    assert build_per_url([]) == []


from gsc_report import render_markdown  # noqa: E402


def test_render_markdown_contains_views_and_no_data_messages():
    md = render_markdown([], site="https://regalame.app/", start="2026-08-05", end="2026-11-03")
    assert "GSC report — https://regalame.app/ (2026-08-05 .. 2026-11-03)" in md
    assert md.count("No data") == 4  # one per view
    assert "V1" in md and "V2" in md and "V3" in md and "V4" in md


def test_render_markdown_renders_rows_with_numbers():
    rows = [_row("amigo invisible", page="/a", clicks=2, impressions=100, position=5.0)]
    md = render_markdown(rows, site="s", start="d1", end="d2")
    assert "amigo invisible" in md
    assert "100" in md
    assert "/a" in md
