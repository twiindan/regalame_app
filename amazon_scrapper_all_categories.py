import asyncio
import json
import os
from playwright.async_api import async_playwright


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
        if any(stop_word in name_clean.lower() for stop_word in ["ver más", "ver mas", "see more", "mostrar más"]):
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
            title_el = await item.query_selector("div[class*='-line-clamp-'], .p13n-sc-truncate-desktop-type2")
            title = await title_el.inner_text() if title_el else "N/A"

            img_el = await item.query_selector("img.p13n-product-image")
            image = await img_el.get_attribute("src") if img_el else "N/A"

            link_el = await item.query_selector("a.a-link-normal")
            url_path = await link_el.get_attribute("href") if link_el else ""

            price_el = await item.query_selector("span.p13n-sc-price, .a-color-price, span[class*='sc-price']")
            price = await price_el.inner_text() if price_el else "N/A"

            if title != "N/A":
                products.append({
                    "category": category_name,  # Nueva estructura
                    "title": title.strip(),
                    "image": image,
                    "url": f"https://www.amazon.es{url_path}" if url_path.startswith("/") else url_path,
                    "price": price.strip()
                })
        except:
            continue
    return products


async def run_mega_scraper():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        sections = [
            {"name": "Bestsellers", "url": "https://www.amazon.es/gp/bestsellers/",
             "file": "amazon_bestsellers_total.json"},
            {"name": "Tendencias", "url": "https://www.amazon.es/gp/movers-and-shakers/",
             "file": "amazon_tendencias_total.json"},
            {"name": "Deseados", "url": "https://www.amazon.es/gp/most-wished-for/",
             "file": "amazon_mas_deseados_total.json"}
        ]

        for section in sections:
            print(f"\n🚀 PROCESANDO SECCIÓN: {section['name']}")
            await page.goto(section['url'], wait_until="domcontentloaded")

            categories = await get_all_category_links(page)
            all_section_products = []  # Lista única para el fichero final

            for cat in categories:
                print(f"  -> {cat['name']}")
                try:
                    await page.goto(cat['url'], wait_until="domcontentloaded")
                    cat_products = await scrape_products(page, cat['name'])
                    all_section_products.extend(cat_products)
                    await asyncio.sleep(2)  # Respiro anti-bloqueo
                except Exception as e:
                    print(f"  ❌ Error en {cat['name']}: {e}")
                    continue

            # Guardar el fichero único de la sección
            with open(section['file'], "w", encoding="utf-8") as f:
                json.dump(all_section_products, f, indent=4, ensure_ascii=False)
            print(f"✅ Fichero generado: {section['file']} con {len(all_section_products)} productos.")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_mega_scraper())