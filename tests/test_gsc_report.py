import sys
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
        _row("amigo invisible", page="/b", clicks=1, impressions=100, position=7.0),
        _row("otra cosa", page="/a", clicks=0, impressions=10, position=20.0),
    ]
    agg = {a["query"]: a for a in aggregate_by(rows, "query")}
    mine = agg["amigo invisible"]
    assert mine["clicks"] == 3
    assert mine["impressions"] == 200
    assert mine["ctr"] == 0.015
    assert mine["position"] == 6.0  # weighted by equal impressions


def test_aggregate_by_zero_impressions_is_safe():
    agg = aggregate_by([_row("q", clicks=0, impressions=0, position=0.0)], "query")
    assert agg[0]["position"] == 0.0
    assert agg[0]["ctr"] == 0.0
