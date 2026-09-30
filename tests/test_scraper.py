"""Scraper module: section definitions and per-section failure isolation.

Playwright is deliberately absent from the CI install, so these tests never
launch a browser.
"""

from catalog import DATA_FILES
from scraper import SECTIONS


def test_sections_cover_every_catalog_list():
    """The scraped filenames must be the ones the importer already knows."""
    assert {section.list_key: section.filename for section in SECTIONS} == DATA_FILES
