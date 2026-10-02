"""Scraper module: section definitions and per-section failure isolation.

Playwright is deliberately absent from the CI install, so these tests never
launch a browser.
"""

import asyncio
import json

import pytest

import scraper
from catalog import DATA_FILES
from scraper import SECTIONS


def test_sections_cover_every_catalog_list():
    """The scraped filenames must be the ones the importer already knows."""
    assert {section.list_key: section.filename for section in SECTIONS} == DATA_FILES


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

    log_lines = []
    produced = asyncio.run(scraper.scrape_all(str(tmp_path), log=log_lines.append))

    assert set(produced) == {"bestsellers", "desired"}
    assert (tmp_path / "amazon_bestsellers_total.json").exists()
    assert not (tmp_path / "amazon_tendencias_total.json").exists()
    with open(produced["bestsellers"], encoding="utf-8") as handle:
        assert json.load(handle) == [_item("bestsellers", 0)]
    assert browser.closed is True
    assert "section=trends status=failed error=RuntimeError('boom')" in log_lines


def test_scrape_all_requires_playwright(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper, "async_playwright", None)

    with pytest.raises(RuntimeError, match="requirements-scraper.txt"):
        asyncio.run(scraper.scrape_all(str(tmp_path)))


def test_an_empty_section_writes_no_file(monkeypatch, tmp_path):
    browser = _FakeBrowser()
    monkeypatch.setattr(scraper, "async_playwright", lambda: _FakePlaywrightManager(browser))

    async def section_scraper(page, section):
        if section.list_key == "desired":
            return []
        return [_item(section.list_key, 0)]

    monkeypatch.setattr(scraper, "scrape_section", section_scraper)

    log_lines = []
    produced = asyncio.run(scraper.scrape_all(str(tmp_path), log=log_lines.append))

    assert set(produced) == {"bestsellers", "trends"}
    assert not (tmp_path / "amazon_mas_deseados_total.json").exists()
    assert (tmp_path / "amazon_bestsellers_total.json").exists()
    assert "section=desired status=empty" in log_lines


def test_an_unwritable_section_does_not_abort_the_run(monkeypatch, tmp_path):
    """A write failure must not discard the sections already produced."""
    browser = _FakeBrowser()
    monkeypatch.setattr(scraper, "async_playwright", lambda: _FakePlaywrightManager(browser))

    async def section_scraper(page, section):
        return [_item(section.list_key, 0)]

    monkeypatch.setattr(scraper, "scrape_section", section_scraper)

    # The target path is a directory, so writing to it raises IsADirectoryError.
    (tmp_path / "amazon_tendencias_total.json").mkdir()

    log_lines = []
    produced = asyncio.run(scraper.scrape_all(str(tmp_path), log=log_lines.append))

    assert set(produced) == {"bestsellers", "desired"}
    assert (tmp_path / "amazon_bestsellers_total.json").exists()
    assert (tmp_path / "amazon_mas_deseados_total.json").exists()
    assert any("section=trends status=unwritable" in line for line in log_lines)
