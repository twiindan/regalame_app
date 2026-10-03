"""Deprecated: kept only so the manual IDE run keeps working.

The scraping logic now lives in scraper.py, which the scheduled job uses too.

    python amazon_scrapper_all_categories.py
"""

import asyncio
import os

from scraper import scrape_all


def main():
    produced = asyncio.run(scrape_all(os.getcwd()))
    for list_key, path in sorted(produced.items()):
        print(f"{list_key}: {path}")


if __name__ == "__main__":
    main()
