"""Scraper module: section definitions and per-section failure isolation.

Playwright is deliberately absent from the CI install, so these tests never
launch a browser.
"""

from catalog import DATA_FILES
from scraper import SECTIONS


def test_sections_cover_every_catalog_list():
    """The scraped filenames must be the ones the importer already knows."""
    assert {section.list_key: section.filename for section in SECTIONS} == DATA_FILES


import asyncio
import json

import scraper


class _FakeContext:
    """`scrape_all` only needs a page object to hand to the section scraper."""

    async def new_page(self):
        return object()


class _FakeBrowser:
    def __init__(self):
        self.closed = False

    async def new_context(self, **kwargs):
        return _FakeContext()

    async def close(self):
        self.closed = True


class _FakeChromium:
    def __init__(self, browser):
        self._browser = browser

    async def launch(self, **kwargs):
        return self._browser


class _FakePlaywright:
    def __init__(self, browser):
        self.chromium = _FakeChromium(browser)


class _FakePlaywrightManager:
    def __init__(self, browser):
        self._playwright = _FakePlaywright(browser)

    async def __aenter__(self):
        return self._playwright

    async def __aexit__(self, *exc):
        return False


def _item(list_key, index):
    return {"category": "Electrónica", "title": f"Producto {index}",
            "image": "https://img/x.jpg", "price": "19,99 €",
            "url": f"https://www.amazon.es/dp/B{list_key[:2].upper()}{index:07d}"}


def test_a_failing_section_does_not_stop_the_others(monkeypatch, tmp_path):
    browser = _FakeBrowser()
    monkeypatch.setattr(scraper, "async_playwright", lambda: _FakePlaywrightManager(browser))

    async def section_scraper(page, section):
        if section.list_key == "trends":
            raise RuntimeError("boom")
        return [_item(section.list_key, 0)]

    monkeypatch.setattr(scraper, "scrape_section", section_scraper)

    produced = asyncio.run(scraper.scrape_all(str(tmp_path)))

    assert set(produced) == {"bestsellers", "desired"}
    assert (tmp_path / "amazon_bestsellers_total.json").exists()
    assert not (tmp_path / "amazon_tendencias_total.json").exists()
    with open(produced["bestsellers"], encoding="utf-8") as handle:
        assert json.load(handle) == [_item("bestsellers", 0)]
    assert browser.closed is True
