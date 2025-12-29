import asyncio
import json
from playwright.async_api import async_playwright


async def scrape_amazon_wished():
    async with async_playwright() as p:
        # Lanzamos el navegador visible para evitar bloqueos
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        print("Navegando a 'Los más deseados' de Amazon...")
        # URL de los más deseados (Most Wished For)
        url = "https://www.amazon.es/gp/most-wished-for/electronics/"
        await page.goto(url, wait_until="domcontentloaded")

        # Pausa para asegurar carga y resolver posibles captchas
        await page.wait_for_timeout(4000)

        # Scroll para cargar los 50 productos (Amazon usa carga dinámica)
        print("Cargando lista completa...")
        for _ in range(5):
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(1)

        products = []
        # Localizamos los items por el selector estándar de Amazon para estas listas
        items = await page.query_selector_all("#gridItemRoot")

        print(f"Productos detectados: {len(items)}")

        for item in items[:50]:
            try:
                # Título: buscamos en las clases de clamp que Amazon usa para truncar nombres
                title_el = await item.query_selector("div[class*='-line-clamp-'], .p13n-sc-truncate-desktop-type2")
                title = await title_el.inner_text() if title_el else "N/A"

                # Imagen
                img_el = await item.query_selector("img.p13n-product-image")
                image = await img_el.get_attribute("src") if img_el else "N/A"

                # URL
                link_el = await item.query_selector("a.a-link-normal")
                url_path = await link_el.get_attribute("href") if link_el else ""
                full_url = f"https://www.amazon.es{url_path}" if url_path.startswith("/") else url_path

                # Precio
                # En 'Most Wished For' el precio a veces tiene clases secundarias
                price_el = await item.query_selector("span.p13n-sc-price, .a-color-price, span[class*='sc-price']")
                price = await price_el.inner_text() if price_el else "Consultar"

                if title != "N/A":
                    products.append({
                        "title": title.strip(),
                        "image": image,
                        "url": full_url,
                        "price": price.strip()
                    })
            except Exception:
                continue

        await browser.close()
        return products


async def main():
    data = await scrape_amazon_wished()

    # Formato JSON solicitado
    final_output = json.dumps(data, indent=4, ensure_ascii=False)
    print(final_output)

    # Guardar resultados en un archivo específico
    with open("amazon_mas_deseados.json", "w", encoding="utf-8") as f:
        f.write(final_output)

    print(f"\nProceso terminado. Se han extraído {len(data)} productos deseados.")


if __name__ == "__main__":
    asyncio.run(main())