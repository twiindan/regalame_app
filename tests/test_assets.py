"""Asset-delivery regression tests for the mobile-performance Phase A fixes.

Guards that base.html no longer pulls render-blocking third-party fonts or the
full Phosphor bundle, and that the self-hosted font asset is present.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def test_home_self_hosts_inter(client):
    html = client.get("/").text

    assert "fonts.googleapis.com" not in html
    assert "fonts.gstatic.com" not in html
    assert "/static/css/fonts.css" in html
    assert "/static/fonts/inter-latin.woff2" in html


def test_self_hosted_inter_font_exists_and_is_woff2():
    font = BASE_DIR / "static" / "fonts" / "inter-latin.woff2"

    assert font.is_file()
    assert font.read_bytes()[:4] == b"wOF2"


def test_self_hosted_font_css_exists():
    css = (BASE_DIR / "static" / "css" / "fonts.css").read_text(encoding="utf-8")

    assert "@font-face" in css
    assert "font-display: swap" in css
    assert "/static/fonts/inter-latin.woff2" in css


def test_home_serves_prebuilt_tailwind_without_play_cdn(client):
    html = client.get("/").text

    assert "cdn.tailwindcss.com" not in html
    assert "tailwind.config" not in html
    assert "/static/css/tailwind.css" in html


def test_prebuilt_tailwind_css_exists_and_covers_used_utilities():
    css = (BASE_DIR / "static" / "css" / "tailwind.css").read_text(encoding="utf-8")

    assert ".animate-fade-in-up" in css
    assert ".grid-cols-1" in css
    assert r".h-\[500px\]" in css


def _used_single_color_icons():
    import re
    pattern = re.compile(r'ph(-bold|-fill|-duotone)?\s+ph-([a-z0-9-]+)')
    used = set()
    sources = list((BASE_DIR / "templates").rglob("*.html")) + [BASE_DIR / "main.py"]
    for source in sources:
        for weight, name in pattern.findall(source.read_text(encoding="utf-8")):
            weight = weight.lstrip("-") or "regular"
            if weight != "duotone":
                used.add((weight, name))
    return used


def test_home_uses_local_phosphor_icons(client):
    html = client.get("/").text

    assert "@phosphor-icons/web" not in html
    assert "cdn.jsdelivr.net" not in html
    assert "/static/css/phosphor.css" in html


def test_local_phosphor_icons_cover_every_used_icon():
    css = (BASE_DIR / "static" / "css" / "phosphor.css").read_text(encoding="utf-8")
    used = _used_single_color_icons()

    assert len(used) >= 30, f"icon scan seems broken: {sorted(used)}"
    for weight, name in used:
        svg = BASE_DIR / "static" / "icons" / weight / f"{name}.svg"
        assert svg.is_file(), f"missing icon asset: {svg}"
        selector = f".ph.ph-{name}" if weight == "regular" else f".ph-{weight}.ph-{name}"
        assert selector in css, f"missing css rule: {selector}"
