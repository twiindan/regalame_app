import asyncio
import json
from playwright.async_api import async_playwright


async def scrape_amazon():
    async with async_playwright() as p:
        # Lanzamos Chromium con argumentos que ayudan a evitar la detección
        browser = await p.chromium.launch(headless=False)

        # Configuramos el contexto para que parezca un navegador real
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-ES",
            timezone_id="Europe/Madrid"
        )

        page = await context.new_page()

        print("Navegando a Amazon...")
        # Usamos la categoría de Electrónica (puedes cambiar esta URL por cualquier Best Seller)
        await page.goto("https://www.amazon.es/gp/bestsellers/electronics/", wait_until="domcontentloaded")

        # Pausa de seguridad: Si ves un captcha, resuélvelo manualmente en la ventana
        print("Esperando carga... Si ves un captcha, resuélvelo en la ventana del navegador.")
        await page.wait_for_timeout(5000)

        # Scroll para cargar los 50 productos (Amazon usa carga perezosa)
        for i in range(5):
            await page.mouse.wheel(0, 1200)
            await asyncio.sleep(1)

        products = []
        # Localizamos los items por el ID de la cuadrícula
        items = await page.query_selector_all("#gridItemRoot")

        print(f"Productos detectados: {len(items)}")

        for item in items[:50]:
            try:
                # Título
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
                price_el = await item.query_selector("span.p13n-sc-price")
                price = await price_el.inner_text() if price_el else "Consultar"

                if title != "N/A":
                    products.append({
                        "title": title.strip(),
                        "image": image,
                        "url": full_url,
                        "price": price.strip()
                    })
            except:
                continue

        await browser.close()
        return products


async def main():
    data = await scrape_amazon()

    # Imprimimos el JSON en el formato exacto que pediste
    final_json = json.dumps(data, indent=4, ensure_ascii=False)
    print(final_json)

    # Guardamos en archivo
    with open("mis_productos_amazon.json", "w", encoding="utf-8") as f:
        f.write(final_json)

    print(f"\nProceso terminado. {len(data)} productos capturados.")


if __name__ == "__main__":
    asyncio.run(main())