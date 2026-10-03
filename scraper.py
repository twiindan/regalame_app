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


async def get_all_category_links(page):
    """Busca categorías en el panel lateral y se detiene al ver 'Ver más'."""
    print("Buscando categorías válidas...")
    await page.wait_for_selector("div[role='group'] a, #zg_left_col2 a")
    category_elements = await page.query_selector_all("div[role='group'] a, #zg_left_col2 a")

    links = []
    for el in category_elements:
        name = await el.inner_text()
        name_clean = name.strip()

        # STOP: Si encontramos "Ver más" o similares, dejamos de añadir
        if any(stop_word in name_clean.lower()
               for stop_word in ["ver más", "ver mas", "see more", "mostrar más"]):
            print(f"Final de categorías alcanzado en: '{name_clean}'")
            break

        url = await el.get_attribute("href")
        if url and name_clean:
            full_url = f"https://www.amazon.es{url}" if url.startswith("/") else url
            links.append({"name": name_clean, "url": full_url})

    return links


async def scrape_products(page, category_name):
    """Extrae 50 productos e incluye la categoría en cada uno."""
    for _ in range(4):
        await page.mouse.wheel(0, 1500)
        await asyncio.sleep(0.6)

    products = []
    items = await page.query_selector_all("#gridItemRoot")

    for item in items[:50]:
        try:
            title_el = await item.query_selector(
                "div[class*='-line-clamp-'], .p13n-sc-truncate-desktop-type2")
            title = await title_el.inner_text() if title_el else "N/A"

            img_el = await item.query_selector("img.p13n-product-image")
            image = await img_el.get_attribute("src") if img_el else "N/A"

            link_el = await item.query_selector("a.a-link-normal")
            url_path = await link_el.get_attribute("href") if link_el else ""

            price_el = await item.query_selector(
                "span.p13n-sc-price, .a-color-price, span[class*='sc-price']")
            price = await price_el.inner_text() if price_el else "N/A"

            if title != "N/A":
                products.append({
                    "category": category_name,
                    "title": title.strip(),
                    "image": image,
                    "url": (f"https://www.amazon.es{url_path}"
                            if url_path.startswith("/") else url_path),
                    "price": price.strip(),
                })
        except Exception:
            continue
    return products


async def scrape_section(page, section):
    """One section: navigate to its landing page, then scrape each category."""
    await page.goto(section.url, wait_until="domcontentloaded")
    products = []
    for category in await get_all_category_links(page):
        print(f"  -> {category['name']}")
        try:
            await page.goto(category["url"], wait_until="domcontentloaded")
            products.extend(await scrape_products(page, category["name"]))
            await asyncio.sleep(2)  # Respiro anti-bloqueo
        except Exception as exc:
            print(f"  ❌ Error en {category['name']}: {exc}")
            continue
    return products


async def scrape_all(out_dir, sections=SECTIONS, log=print):
    """Scrape every section into ``out_dir``; a broken section is skipped.

    Returns a ``{list_key: path}`` map containing only the sections that produced
    products. A section that raises writes no file, which is what makes the
    import skip it and leave that list's ranks untouched.

    ``log`` carries only these section-level status lines: the moved per-category
    helpers still print their progress to stdout directly.
    """
    if async_playwright is None:
        raise RuntimeError(
            "Playwright is not installed. Install requirements-scraper.txt to scrape."
        )

    produced = {}
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            for section in sections:
                try:
                    products = await scrape_section(page, section)
                except Exception as exc:
                    log(f"section={section.list_key} status=failed error={exc!r}")
                    continue
                if not products:
                    log(f"section={section.list_key} status=empty")
                    continue
                path = os.path.join(out_dir, section.filename)
                with open(path, "w", encoding="utf-8") as handle:
                    json.dump(products, handle, indent=4, ensure_ascii=False)
                produced[section.list_key] = path
                log(f"section={section.list_key} status=ok products={len(products)}")
        finally:
            await browser.close()
    return produced
