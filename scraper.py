"""Amazon product scraping for the three catalog lists.

Extracted from amazon_scrapper_all_categories.py. The DOM selectors and the
extraction logic are verbatim; the structural changes are that a section failure
is contained to that section, and that the output directory is injected.

Playwright is intentionally NOT in requirements.txt: the web service never
imports this module. Install requirements-scraper.txt to actually scrape.
"""

import asyncio
import json
import os
from dataclasses import dataclass

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - CI and the web install have no browser
    async_playwright = None


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Section:
    list_key: str
    name: str
    url: str
    filename: str


SECTIONS = (
    Section("bestsellers", "Bestsellers", "https://www.amazon.es/gp/bestsellers/",
            "amazon_bestsellers_total.json"),
    Section("trends", "Tendencias", "https://www.amazon.es/gp/movers-and-shakers/",
            "amazon_tendencias_total.json"),
    Section("desired", "Deseados", "https://www.amazon.es/gp/most-wished-for/",
            "amazon_mas_deseados_total.json"),
)
