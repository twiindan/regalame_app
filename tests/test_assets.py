"""Asset-delivery regression tests for the mobile-performance Phase A/B fixes.

Guards that base.html no longer pulls render-blocking third-party fonts or the
full Phosphor bundle, that the self-hosted font asset is present, and that the
prebuilt Tailwind/Phosphor stylesheets actually cover every class and icon the
templates use — including classes only applied by inline JavaScript at runtime,
which a static ``class="..."`` scan would miss.
"""

import importlib.util
import re
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SVG_TAG = "{http://www.w3.org/2000/svg}svg"

# Characters Tailwind escapes (with a backslash) inside generated selectors.
_CSS_SPECIAL_CHARS = "./%[]()#,'\"!<>@:"

_JS_CLASS_LIST = re.compile(r"classList\.(?:add|remove|toggle)\(([^)]*)\)")
_JS_CLASS_NAME = re.compile(r"""className\s*=\s*(['"])(.*?)\1""")
_STRING_LITERAL = re.compile(r"""(['"])(.*?)\1""")


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


def test_prebuilt_tailwind_css_is_generated_from_v4_tokens():
    """The templates use v4-only utility names (bg-linear-*, outline-hidden,
    shadow-xs); the committed sheet must therefore be a v4 build, not a stale
    v3 artifact. These tokens do not exist in any v3-generated sheet, so a
    stale artifact fails here even though the v3-compatible substrings above
    would still pass."""
    css = (BASE_DIR / "static" / "css" / "tailwind.css").read_text(encoding="utf-8")

    assert ".bg-linear-to-r" in css
    assert ".outline-hidden" in css
    assert ".shadow-xs" in css


def _js_toggled_class_tokens():
    """Class tokens applied at runtime by inline JS (classList/className)."""
    tokens = set()
    for source in (BASE_DIR / "templates").rglob("*.html"):
        text = source.read_text(encoding="utf-8")
        for args in _JS_CLASS_LIST.findall(text):
            for _, literal in _STRING_LITERAL.findall(args):
                tokens.update(literal.split())
        for _, value in _JS_CLASS_NAME.findall(text):
            tokens.update(value.split())
    return tokens


def _escape_tailwind_class(cls):
    """Mirror Tailwind's escaping of CSS-significant characters in a selector."""
    return "".join(
        "\\" + char if char in _CSS_SPECIAL_CHARS else char for char in cls
    )


def test_js_toggled_tailwind_classes_are_present_in_generated_css():
    tailwind_css = (BASE_DIR / "static" / "css" / "tailwind.css").read_text(
        encoding="utf-8"
    )
    phosphor_css = (BASE_DIR / "static" / "css" / "phosphor.css").read_text(
        encoding="utf-8"
    )
    tokens = _js_toggled_class_tokens()

    assert tokens, "inline-JS class scan found nothing; is the scan broken?"
    for token in sorted(tokens):
        if token == "ph" or token.startswith("ph-"):
            assert token in phosphor_css, f"icon class toggled in JS has no rule: {token}"
        else:
            escaped = "." + _escape_tailwind_class(token)
            assert escaped in tailwind_css or ("." + token) in tailwind_css, (
                f"Tailwind class toggled in JS is missing from tailwind.css: {token}"
            )


def test_server_serves_both_stylesheets(client):
    for path in ("/static/css/tailwind.css", "/static/css/phosphor.css"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.text.strip(), f"empty stylesheet body: {path}"


def test_home_uses_local_phosphor_icons(client):
    html = client.get("/").text

    assert "@phosphor-icons/web" not in html
    assert "cdn.jsdelivr.net" not in html
    assert "/static/css/phosphor.css" in html


def test_duotone_icons_are_inlined_as_svg_not_icon_font(auth_client):
    for template in (BASE_DIR / "templates").rglob("*.html"):
        text = template.read_text(encoding="utf-8")
        assert not re.search(r"<i\b[^>]*\bph-duotone\b", text), (
            f"duotone icon-font <i> tag found in {template}"
        )

    html = auth_client.get("/dashboard").text
    match = re.search(r"<svg[^>]*class=\"ph-duotone[^>]*>", html)
    assert match is not None, "the inline duotone <svg> is not actually served"
    assert 'width="1em"' in match.group(0) and 'height="1em"' in match.group(0), (
        "the inline duotone <svg> is not sized with width/height=1em"
    )


def _scan_used_icons():
    """Load the generator itself as the single source of truth for icon usages."""
    spec = importlib.util.spec_from_file_location(
        "build_phosphor_icons", BASE_DIR / "tools" / "build_phosphor_icons.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.scan_used_icons()


def test_every_used_icon_asset_exists_parses_and_is_wired():
    css = (BASE_DIR / "static" / "css" / "phosphor.css").read_text(encoding="utf-8")
    used = _scan_used_icons()

    assert len(used) >= 30, f"icon scan seems broken: {sorted(used)}"
    for weight, name in used:
        svg = BASE_DIR / "static" / "icons" / weight / f"{name}.svg"
        assert svg.is_file(), f"missing icon asset: {svg}"
        root = ET.fromstring(svg.read_bytes())
        assert root.tag == SVG_TAG, f"not an SVG root: {svg} -> {root.tag}"

        if weight == "regular":
            selector = f".ph.ph-{name}"
        else:
            selector = f".ph-{weight}.ph-{name}"
        url = f"/static/icons/{weight}/{name}.svg"
        rule = re.search(re.escape(selector) + r"\{[^}]*\}", css)
        assert rule is not None, f"missing css rule: {selector}"
        assert f'mask-image:url("{url}")' in rule.group(0), (
            f"{selector} does not resolve to {url} in phosphor.css"
        )
