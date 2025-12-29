import asyncio
import json
from playwright.async_api import async_playwright


async def scrape_amazon_movers():
    async with async_playwright() as p:
        # Lanzamos el navegador visible
        browser = await p.chromium.launch(headless=False)

        # Configuración de contexto para evitar bloqueos
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        print("Navegando a Tendencias de Amazon (Movers & Shakers)...")
        # URL proporcionada
        url = "https://www.amazon.com/-/es/gp/movers-and-shakers/electronics/"
        await page.goto(url, wait_until="domcontentloaded")

        # Pausa para cargar y por si aparece un Captcha
        print("Esperando carga de elementos...")
        await page.wait_for_timeout(5000)

        # Hacemos scroll progresivo para cargar los 50 productos
        for _ in range(5):
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(1)

        products = []
        # Amazon usa 'gridItemRoot' también para esta sección
        items = await page.query_selector_all("#gridItemRoot")

        print(f"Productos detectados: {len(items)}")

        for item in items[:50]:
            try:
                # Título
                # En Movers & Shakers, el título suele estar en un div con clase específica de clamp
                title_el = await item.query_selector("div[class*='-line-clamp-'], .p13n-sc-truncate-desktop-type2")
                title = await title_el.inner_text() if title_el else "N/A"

                # Imagen
                img_el = await item.query_selector("img.p13n-product-image")
                image = await img_el.get_attribute("src") if img_el else "N/A"

                # URL
                link_el = await item.query_selector("a.a-link-normal")
                url_path = await link_el.get_attribute("href") if link_el else ""
                full_url = f"https://www.amazon.com{url_path}" if url_path.startswith("/") else url_path

                # Precio
                # El precio a veces está dentro de un bloque específico de "tendencia"
                price_el = await item.query_selector("span.p13n-sc-price, .a-color-price")
                price = await price_el.inner_text() if price_el else "N/A"

                if title != "N/A":
                    products.append({
                        "title": title.strip(),
                        "image": image,
                        "url": full_url,
                        "price": price.strip()
                    })
            except Exception as e:
                continue

        await browser.close()
        return products


async def main():
    data = await scrape_amazon_movers()

    # Formateo JSON solicitado
    final_output = json.dumps(data, indent=4, ensure_ascii=False)
    print(final_output)

    # Guardar resultados
    with open("amazon_tendencias.json", "w", encoding="utf-8") as f:
        f.write(final_output)

    print(f"\nProceso terminado. {len(data)} tendencias extraídas.")


if __name__ == "__main__":
    asyncio.run(main())