"""Asset-delivery regression tests for the mobile-performance Phase A fixes.

Guards that base.html no longer pulls render-blocking third-party fonts or the
full Phosphor bundle, and that the self-hosted font asset is present.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

PHOSPHOR_WEIGHTS = ("regular", "bold", "fill", "duotone")
PHOSPHOR_UNUSED = ("light", "thin")


def test_home_self_hosts_inter(client):
    html = client.get("/").text

    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert "/static/css/fonts.css" in html
    assert "/static/fonts/inter-latin.woff2" in html


def test_home_loads_only_used_phosphor_weights(client):
    html = client.get("/").text

    for weight in PHOSPHOR_WEIGHTS:
        assert f"/src/{weight}/style.css" in html
    for weight in PHOSPHOR_UNUSED:
        assert f"/src/{weight}/style.css" not in html
    assert "unpkg.com/@phosphor-icons/web" not in html


def test_self_hosted_inter_font_exists_and_is_woff2():
    font = BASE_DIR / "static" / "fonts" / "inter-latin.woff2"

    assert font.is_file()
    assert font.read_bytes()[:4] == b"wOF2"


def test_self_hosted_font_css_exists():
    css = (BASE_DIR / "static" / "css" / "fonts.css").read_text(encoding="utf-8")

    assert "@font-face" in css
    assert "font-display: swap" in css
    assert "/static/fonts/inter-latin.woff2" in css
