# Refresco periódico del catálogo — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refrescar el catálogo de Amazon automáticamente, una vez por día, desde un servicio
cron en Railway, sin poder dañar el catálogo existente cuando el scraping falla.

**Architecture:** Un módulo `scraper.py` que aísla el fallo por sección, un orquestador
`jobs/refresh_catalog.py` que clasifica secciones (sana / sospechosa / ausente) e importa
sólo las sanas con `catalog.import_from_json()` (ya idempotente), y un servicio cron con su
propio Dockerfile en `scraper/` para no tocar el deploy del web.

**Tech Stack:** Python 3.13, FastAPI/SQLModel, SQLAlchemy 2.0, Playwright (sólo scraping),
pytest, Railway (servicio cron + Postgres).

**Spec:** `docs/superpowers/specs/2026-09-30-refresco-catalogo-cron-design.md`

**Baseline medido:** `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py` → **92 passed**.

---

## Restricción transversal: Playwright NO está instalado en el CI

`scraper.py` importa `playwright.async_api` en el nivel de módulo. El CI instala
`requirements-dev.txt`, que **no** incluye Playwright (decisión de diseño explícita). Si el
import es duro, la sola colección de `tests/test_scraper.py` rompe el CI y el venv nuevo del
worktree.

**Por eso el import es tolerante** (Task 3, Step 1). Esto no es defensividad decorativa: sin
esto, el CI rojo es garantizado. El contenedor del cron sí tiene Playwright instalado, así
que en producción el import real ocurre.

---

## Slice 1 — `scraper.py` (PR #1)

Extrae el scraping a un módulo importable, con el fallo de una sección contenido en esa
sección. Sin cambios de comportamiento respecto de
`amazon_scrapper_all_categories.py`, salvo el aislamiento de errores.

### Task 0: Worktree y baseline verde

**Files:** ninguno (setup).

- [ ] **Step 1: Crear el worktree**

```bash
git -C /Users/toni.robres/Pycharmprojects/regalame_gemini3 worktree add \
  /Users/toni.robres/Pycharmprojects/regalame_gemini3-worktrees/refresco-catalogo-cron \
  -b feat/refresh-catalog-01-scraper main
```

- [ ] **Step 2: Crear el venv del worktree e instalar**

`venv/` está en `.gitignore`, así que un worktree nuevo no lo tiene.

```bash
cd /Users/toni.robres/Pycharmprojects/regalame_gemini3-worktrees/refresco-catalogo-cron
python3 -m venv venv
./venv/bin/python -m pip install -q -r requirements-dev.txt
```

- [ ] **Step 3: Correr el baseline**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: `92 passed`

Si el número no es 92, PARÁ y reportá: el baseline cambió y el plan asume este punto de
partida.

### Task 1: `SECTIONS` y la consistencia con `catalog.DATA_FILES`

**Files:**
- Create: `scraper.py`
- Test: `tests/test_scraper.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scraper.py
"""Scraper module: section definitions and per-section failure isolation.

Playwright is deliberately absent from the CI install, so these tests never
launch a browser.
"""

from catalog import DATA_FILES
from scraper import SECTIONS


def test_sections_cover_every_catalog_list():
    """The scraped filenames must be the ones the importer already knows."""
    assert {section.list_key: section.filename for section in SECTIONS} == DATA_FILES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_scraper.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'scraper'`

- [ ] **Step 3: Write minimal implementation**

```python
# scraper.py
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
```

`SECTIONS` importa `dataclass` y `os`/`json`/`asyncio` que todavía no se usan: se usan en las
tareas siguientes. No los borres (el lint no está configurado en este repo).

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_scraper.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Verificar que el import no requiere Playwright**

Run: `./venv/bin/python -c "import scraper; print(scraper.async_playwright)"`
Expected: imprime algo como `None` o un callable, **sin** ImportError. Si revienta, el CI va a
romper en la Task 5.

- [ ] **Step 6: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat(scraper): extract Amazon list sections into a module"
```

### Task 2: Extraer la lógica de scraping (verbatim)

**Files:**
- Modify: `scraper.py` (append)

- [ ] **Step 1: Append the extraction functions, verbatim from the old script**

Cuerpo textual de `amazon_scrapper_all_categories.py:6-63`, sólo cambia la ubicación: la
búsqueda de categorías y la extracción de productos dejan de escribir el JSON y pasan a
devolver listas.

```python
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
```

- [ ] **Step 2: Verificar que el módulo sigue importable sin Playwright**

Run: `./venv/bin/python -c "import scraper; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add scraper.py
git commit -m "feat(scraper): move the extraction logic verbatim from the old script"
```

### Task 3: `scrape_all()` con fallo aislado por sección

**Files:**
- Modify: `scraper.py` (append)
- Test: `tests/test_scraper.py` (append)

- [ ] **Step 1: Write the failing test**

El valor de este test es que prueba la garantía que protege la DB: una sección rota no impide
las otras, y el browser se cierra igual.

```python
# tests/test_scraper.py (append)
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
```

Nota: `produced` mapea `list_key -> path` como **string** (`os.path.join`), no como `Path`.

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_scraper.py -q`
Expected: FAIL con `AttributeError: module 'scraper' has no attribute 'scrape_all'`

- [ ] **Step 3: Write minimal implementation**

```python
# scraper.py (append)
async def scrape_all(out_dir, sections=SECTIONS, log=print):
    """Scrape every section into ``out_dir``; a broken section is skipped.

    Returns a ``{list_key: path}`` map containing only the sections that produced
    products. A section that raises writes no file, which is what makes the
    import skip it and leave that list's ranks untouched.
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_scraper.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "feat(scraper): scrape all sections with per-section failure isolation"
```

### Task 4: `headless=True` y el wrapper del script viejo

**Files:**
- Modify: `amazon_scrapper_all_categories.py`

- [ ] **Step 1: Replace the old script with a thin wrapper**

El `headless=True` ya está en tu working tree sin commitear, pero el worktree nace de `main`,
así que la versión commiteada todavía dice `headless=False`. El wrapper elimina el problema de
raíz: ya no lanza un browser por su cuenta.

```python
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
```

- [ ] **Step 2: Verify the suite is still green**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: `94 passed` (92 del baseline + 2 nuevos)

- [ ] **Step 3: Commit**

```bash
git add amazon_scrapper_all_categories.py
git commit -m "refactor: turn the ad-hoc scraper script into a thin wrapper"
```

- [ ] **Step 4: Abrir el PR del slice 1**

Título: `feat(scraper): extract the Amazon scraping into a module`
Cuerpo: qué se movió (verbatim), el aislamiento por sección, y que `headless=True` es
requisito del cron.

---

## Slice 2 — El orquestador `jobs/refresh_catalog.py` (PR #2)

**Este slice es el corazón del diseño**: acá viven el guard de sanidad, la clasificación y el
exit code. Se valida entero contra SQLite, sin Docker ni Railway.

### Task 5: Paquete `jobs` y baseline de conteos

**Files:**
- Create: `jobs/__init__.py`
- Create: `jobs/refresh_catalog.py`
- Test: `tests/test_refresh_catalog.py`

- [ ] **Step 1: Create the package marker**

```python
# jobs/__init__.py
"""Scheduled jobs that run outside the web process."""
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_refresh_catalog.py
"""Catalog refresh orchestration: health classification and failure containment."""

import json
import os

from sqlmodel import func, select

import jobs.refresh_catalog as refresh_catalog
from models import Product, ProductList
from scraper import SECTIONS

FILENAMES = {section.list_key: section.filename for section in SECTIONS}
FULL = {"bestsellers": 12, "trends": 12, "desired": 12}


def product_json(list_key, index, title=None):
    asin = f"B{list_key[:2].upper()}{index:07d}"
    return {"category": "Electrónica", "title": title or f"Producto {list_key} {index}",
            "image": f"https://img/{asin}.jpg",
            "url": f"https://www.amazon.es/dp/{asin}", "price": "19,99 €"}


def fake_scrape(counts):
    """A scrape_fn writing `counts[list_key]` items; None means the section failed."""
    def _scrape(out_dir):
        produced = {}
        for list_key, count in counts.items():
            if count is None:
                continue
            path = os.path.join(out_dir, FILENAMES[list_key])
            with open(path, "w", encoding="utf-8") as handle:
                json.dump([product_json(list_key, i) for i in range(count)], handle)
            produced[list_key] = path
        return produced
    return _scrape


def silent(*args, **kwargs):
    pass


def snapshot_catalog(session):
    products = sorted(tuple(row) for row in session.exec(
        select(Product.id, Product.title, Product.is_active, Product.updated_at)).all())
    lists = sorted(tuple(row) for row in session.exec(
        select(ProductList.product_id, ProductList.list_key, ProductList.rank)).all())
    return products, lists


def test_baseline_counts_reads_each_list(session, catalog_seed):
    """The health reference comes from the DB, so no new state is needed."""
    assert refresh_catalog.baseline_counts(session) == {"bestsellers": 2, "trends": 2}
```

`catalog_seed` es el fixture que ya existe en `tests/conftest.py`: 2 productos en
`bestsellers`, 2 en `trends`, ninguno en `desired`. Por eso el expected no es `FULL`.

- [ ] **Step 3: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'jobs.refresh_catalog'`

- [ ] **Step 4: Write minimal implementation**

```python
# jobs/refresh_catalog.py
"""Daily catalog refresh: scrape the Amazon lists and import them into the DB."""

from sqlmodel import func, select

from models import ProductList

# A section below this fraction of its previous count is treated as truncated.
MIN_HEALTHY_RATIO = 0.5


def baseline_counts(session):
    """Current number of products per list, read before the import."""
    rows = session.exec(
        select(ProductList.list_key, func.count()).group_by(ProductList.list_key)
    ).all()
    return {list_key: count for list_key, count in rows}
```

Sólo `baseline_counts`. `run()` no existe todavía: llega en la Task 7, cuando ya estén las
piezas puras que usa. Nada de stubs ni `NotImplementedError`.

- [ ] **Step 5: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add jobs/__init__.py jobs/refresh_catalog.py tests/test_refresh_catalog.py
git commit -m "feat(jobs): read the per-list baseline from the database"
```

### Task 6: El guard de sanidad (sección truncada)

Funciones puras, sin DB: el ciclo rojo→verde acá es limpio y no necesita marcar tests como
`xfail` para esquivar código que todavía no existe.

**Files:**
- Modify: `jobs/refresh_catalog.py`
- Test: `tests/test_refresh_catalog.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_refresh_catalog.py (append)
def test_a_healthy_section_passes_the_guard(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps([product_json("bestsellers", i) for i in range(12)]),
                    encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify(
        {"bestsellers": str(good)}, {"bestsellers": 12})

    assert set(healthy) == {"bestsellers"}
    assert suspicious == []


def test_a_truncated_section_is_suspicious(tmp_path):
    """Amazon returning 200 with a partial grid must not be taken as truth."""
    short = tmp_path / "short.json"
    short.write_text(json.dumps([product_json("bestsellers", i) for i in range(4)]),
                     encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify(
        {"bestsellers": str(short)}, {"bestsellers": 20})

    assert healthy == {}
    assert suspicious == ["bestsellers"]


def test_a_missing_file_is_suspicious():
    healthy, suspicious = refresh_catalog.classify(
        {"bestsellers": "/nonexistent/none.json"}, {})

    assert healthy == {}
    assert suspicious == ["bestsellers"]


def test_an_unreadable_file_is_suspicious(tmp_path):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify({"bestsellers": str(bad)}, {})

    assert healthy == {}
    assert suspicious == ["bestsellers"]


def test_a_first_run_has_no_reference_to_fall_short_of(tmp_path):
    """An empty DB must not make every section suspicious."""
    first = tmp_path / "first.json"
    first.write_text(json.dumps([product_json("bestsellers", 0)]), encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify({"bestsellers": str(first)}, {})

    assert set(healthy) == {"bestsellers"}
    assert suspicious == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: FAIL con `AttributeError: module 'jobs.refresh_catalog' has no attribute 'classify'`

- [ ] **Step 3: Write minimal implementation**

```python
# jobs/refresh_catalog.py — add below baseline_counts()
def _count_items(path):
    """Number of products in a produced file; 0 when missing or unreadable."""
    try:
        with open(path, encoding="utf-8") as handle:
            items = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return 0
    return len(items) if isinstance(items, list) else 0


def classify(produced, baseline):
    """Split produced files into (healthy, suspicious) list keys.

    A section is suspicious when it is unreadable, empty, or shorter than
    ``MIN_HEALTHY_RATIO`` of what that list had before. Suspicious sections are
    never imported, so their ranks and their products stay untouched. A list with
    no baseline (first run) has no reference to fall short of.
    """
    healthy, suspicious = {}, []
    for list_key, path in produced.items():
        count = _count_items(path)
        previous = baseline.get(list_key, 0)
        if count == 0 or (previous and count < previous * MIN_HEALTHY_RATIO):
            suspicious.append(list_key)
        else:
            healthy[list_key] = path
    return healthy, sorted(suspicious)
```

Y agregá `import json` al encabezado del módulo.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add jobs/refresh_catalog.py tests/test_refresh_catalog.py
git commit -m "feat(jobs): reject truncated or unreadable sections before importing"
```

### Task 7: `run()` — importar sólo lo sano

Acá nace el orquestador completo: `run()` más `_finish()`. Es la tarea más grande del plan y
por eso llega cuando las piezas puras (`baseline_counts`, `classify`) ya están verdes.

**Files:**
- Modify: `jobs/refresh_catalog.py`
- Test: `tests/test_refresh_catalog.py` (append)

- [ ] **Step 1: Write the failing tests**

El segundo test siembra un rank de `trends` que la corrida fallida **no podría reproducir**. Si
la sección fallida se importara igual, ese rank se borraría y el test lo detecta. Un test que
sólo comparara contra datos idénticos no probaría nada.

```python
# tests/test_refresh_catalog.py (append)
from datetime import datetime


def test_a_healthy_run_imports_every_section(session):
    code = refresh_catalog.run(session, scrape_fn=fake_scrape(FULL), log=silent)

    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 36
    assert set(session.exec(select(ProductList.list_key)).all()) == set(FULL)


def test_the_default_scrape_fn_awaits_the_real_async_scraper(session, monkeypatch):
    """The injected fakes are synchronous; the production scraper is a coroutine.

    No other test exercises the default ``scrape_fn``, so without this the whole
    unattended path could ship handing a coroutine object to ``classify``.
    """
    async def fake_async_scrape(out_dir):
        path = os.path.join(out_dir, FILENAMES["bestsellers"])
        with open(path, "w", encoding="utf-8") as handle:
            json.dump([product_json("bestsellers", i) for i in range(12)], handle)
        return {"bestsellers": path}

    monkeypatch.setattr(refresh_catalog, "scrape_all", fake_async_scrape)

    code = refresh_catalog.run(session, log=silent)

    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 12


def test_a_failed_section_keeps_its_ranks(session):
    ghost = Product(asin="GHOSTGHOST", title="Sólo en trends", title_normalized="solo en trends",
                    image_url=None, url="https://www.amazon.es/dp/GHOSTGHOST",
                    category="Varios", category_slug="varios",
                    price_numeric=None, price_raw="N/A", scraped_at=datetime(2026, 1, 1))
    session.add(ghost)
    session.commit()
    session.refresh(ghost)
    session.add(ProductList(product_id=ghost.id, list_key="trends", rank=7))
    session.commit()

    code = refresh_catalog.run(
        session, scrape_fn=fake_scrape(dict(FULL, trends=None)), log=silent)

    assert code == 0
    rows = session.exec(select(ProductList).where(ProductList.list_key == "trends")).all()
    assert [(row.product_id, row.rank) for row in rows] == [(ghost.id, 7)]


def test_a_failed_section_is_not_handed_to_the_import(session, monkeypatch):
    captured = {}
    real_import = refresh_catalog.import_from_json

    def spy(session, data_files=None, dry_run=False):
        captured["keys"] = sorted(data_files or {})
        return real_import(session, data_files=data_files, dry_run=dry_run)

    monkeypatch.setattr(refresh_catalog, "import_from_json", spy)

    refresh_catalog.run(session, scrape_fn=fake_scrape(dict(FULL, trends=None)), log=silent)

    assert captured["keys"] == ["bestsellers", "desired"]


def test_a_truncated_section_is_excluded_from_the_import(session):
    """The DB-level counterpart of the classify unit tests."""
    refresh_catalog.run(
        session, scrape_fn=fake_scrape({"bestsellers": 20, "trends": 20, "desired": 20}),
        log=silent)
    refresh_catalog.run(
        session, scrape_fn=fake_scrape({"bestsellers": 4, "trends": 20, "desired": 20}),
        log=silent)

    rows = session.exec(select(ProductList).where(ProductList.list_key == "bestsellers")).all()
    assert len(rows) == 20  # untouched: the 4-item section was rejected
```

`test_the_default_scrape_fn_awaits_the_real_async_scraper` es el que faltaba: es el único que toca
el `scrape_fn` por defecto. Sin él, la ruta desatendida podía romperse entera sin que ningún test se
enterara.

`captured["keys"]` se compara contra la lista ordenada alfabéticamente.

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: FAIL con `AttributeError: module 'jobs.refresh_catalog' has no attribute 'run'`

- [ ] **Step 3: Write minimal implementation**

```python
# jobs/refresh_catalog.py — imports become:
import asyncio
import json
import os
import tempfile

from sqlmodel import func, select

from catalog import import_from_json
from models import ProductList
from scraper import SECTIONS, scrape_all
```

```python
# jobs/refresh_catalog.py — add below classify()
def _scrape_into(out_dir):
    """Bridge the async scraper to the synchronous ``run`` seam.

    ``scraper.scrape_all`` is a coroutine function (it awaits Playwright), while
    ``run`` is synchronous and every injected fake is a plain callable. Without
    this bridge the production path hands a coroutine object to ``classify``.
    """
    return asyncio.run(scrape_all(out_dir))


def run(session, scrape_fn=_scrape_into, dry_run=False, data_dir=None, log=print):
    """Refresh the catalog. Returns the exit code (0 ok, 1 nothing imported).

    ``scrape_fn`` is a **synchronous** callable returning the ``{list_key: path}``
    map; the production default ``_scrape_into`` wraps the async scraper.
    """
    baseline = baseline_counts(session)
    if data_dir:
        produced = {
            section.list_key: os.path.join(data_dir, section.filename)
            for section in SECTIONS
            if os.path.exists(os.path.join(data_dir, section.filename))
        }
        return _finish(session, produced, baseline, dry_run, log)
    with tempfile.TemporaryDirectory(prefix="catalog_run_") as out_dir:
        produced = scrape_fn(out_dir)
        return _finish(session, produced, baseline, dry_run, log)


def _finish(session, produced, baseline, dry_run, log):
    healthy, suspicious = classify(produced, baseline)
    for list_key in suspicious:
        log(f"section={list_key} status=suspicious excluded")

    if not healthy:
        log("refresh: no healthy sections, nothing imported")
        return 1

    stats = import_from_json(session, data_files=healthy, dry_run=dry_run)
    log(f"import: created={stats['created']} updated={stats['updated']} "
        f"lists={stats['lists']} sections_ok={len(healthy)}")
    return 0
```

`scrape_fn` es inyectable: es lo que permite que todo este slice se testee sin browser.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS (11 passed)

- [ ] **Step 5: Commit**

```bash
git add jobs/refresh_catalog.py tests/test_refresh_catalog.py
git commit -m "feat(jobs): import only the healthy sections and report an exit code"
```

### Task 8: Las tres secciones fallando no escriben nada

**Files:**
- Test: `tests/test_refresh_catalog.py` (append)

- [ ] **Step 1: Write the test**

```python
# tests/test_refresh_catalog.py (append)
def test_a_run_with_no_healthy_section_writes_nothing(session):
    refresh_catalog.run(session, scrape_fn=fake_scrape(FULL), log=silent)
    before = snapshot_catalog(session)

    code = refresh_catalog.run(
        session,
        scrape_fn=fake_scrape({"bestsellers": None, "trends": None, "desired": None}),
        log=silent)

    assert code == 1
    assert snapshot_catalog(session) == before


def test_the_exit_code_is_zero_when_only_some_sections_survive(session):
    code = refresh_catalog.run(
        session, scrape_fn=fake_scrape(dict(FULL, desired=None)), log=silent)
    assert code == 0
```

- [ ] **Step 2: Run to verify the current state**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS — la implementación de Task 7 ya cubre esto. Si falla, hay un bug real: PARÁ y
reportá. Un test que nace verde porque el diseño ya lo cubría es correcto; no inventes código
para "hacerlo fallar".

- [ ] **Step 3: Commit**

```bash
git add tests/test_refresh_catalog.py
git commit -m "test(jobs): pin the no-destructive-write guarantee"
```

### Task 9: CLI (`--dry-run`, `--data-dir`) y el resumen

**Files:**
- Modify: `jobs/refresh_catalog.py`
- Test: `tests/test_refresh_catalog.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_refresh_catalog.py (append)
def test_data_dir_never_invokes_the_scraper(session, tmp_path):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    def exploding(out_dir):
        raise AssertionError("the scraper must not run with --data-dir")

    code = refresh_catalog.run(session, scrape_fn=exploding, data_dir=str(tmp_path), log=silent)
    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 36


def test_dry_run_writes_nothing(session, tmp_path):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    code = refresh_catalog.run(session, data_dir=str(tmp_path), dry_run=True, log=silent)
    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 0


def test_main_reports_the_run(session, tmp_path, capsys):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    code = refresh_catalog.main(["--data-dir", str(tmp_path)], session=session)

    assert code == 0
    assert "sections_ok=3" in capsys.readouterr().out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: FAIL con `AttributeError: module 'jobs.refresh_catalog' has no attribute 'main'`

- [ ] **Step 3: Write minimal implementation**

```python
# jobs/refresh_catalog.py — imports become:
import argparse
import json
import os
import sys
import tempfile

from sqlmodel import Session, func, select

from catalog import import_from_json
from database import engine
from models import ProductList
from scraper import SECTIONS, scrape_all
```

```python
# jobs/refresh_catalog.py (append)
def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Refresh the Amazon catalog")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report the changes without writing them")
    parser.add_argument("--data-dir", default=None,
                        help="Import the JSON files already in DIR instead of scraping")
    return parser.parse_args(argv)


def main(argv=None, session=None):
    """CLI entry point. Returns the exit code."""
    args = _parse_args(argv)
    if session is not None:
        return run(session, dry_run=args.dry_run, data_dir=args.data_dir)
    with Session(engine) as owned:
        return run(owned, dry_run=args.dry_run, data_dir=args.data_dir)


if __name__ == "__main__":
    sys.exit(main())
```

`session` es un seam de test: en producción `main()` abre su propia sesión contra
`DATABASE_URL`.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS (todos)

- [ ] **Step 5: Verificación end-to-end contra los JSON reales, sin browser**

Un worktree nuevo no tiene `database.db`, y SQLite no crea las tablas solo: hay que migrar
primero, o `baseline_counts` revienta con `no such table: productlist`.

```bash
./venv/bin/alembic upgrade head
./venv/bin/python -m jobs.refresh_catalog --data-dir . --dry-run
```

Expected: una línea `import: created=... updated=... lists=... sections_ok=3` con
`sections_ok=3`, y **cero** filas escritas (es `--dry-run`).

Los JSON de la raíz son del 21/01/2026, así que este paso prueba la mecánica completa, no la
frescura. La frescura se prueba recién con la corrida real del slice 3.

- [ ] **Step 6: Verify the full suite**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: todo verde, sin regresiones sobre los 96 del slice 1. Con los 16 tests nuevos de este
slice el total esperado es 112.

- [ ] **Step 7: Commit**

```bash
git add jobs/refresh_catalog.py tests/test_refresh_catalog.py
git commit -m "feat(jobs): add the refresh CLI with --dry-run and --data-dir"
```

- [ ] **Step 8: Abrir el PR del slice 2**

Título: `feat(jobs): refresh the catalog from the scraped sections`
Cuerpo: la tabla de comportamiento ante fallos del spec, y la evidencia del paso 5.

---

## Slice 2.5 — Hardening de los dos WARNING del review nativo (PR #3)

**Origen:** no estaba en el plan original. Sale de los dos hallazgos WARNING que dejaron los
reviews nativos de los slices 1 y 2. La numeración 2.5 conserva el orden de autoría; el orden de
merge en la cadena es: slice 1 → slice 2 → **este** → empaquetado → desactivación.

Los dos hallazgos tienen alcance real bajo (el `out_dir` es un tempdir nuevo y el scraper siempre
serializa UTF-8 válido con `json.dump`), pero los dos son caminos de aborto total de una corrida
desatendida y el arreglo es barato. El slice los cierra y deja el núcleo duro antes de que el
contenedor dependa de él.

### Task 16: la persistencia entra en el containment por sección

**Files:**
- Modify: `scraper.py`
- Test: `tests/test_scraper.py` (append)

- [ ] **Step 1: Write the failing test**

El modo de falla es real y silencioso: la escritura está fuera del `try` por sección, así que un
error de persistencia en la **tercera** sección aborta la corrida y descarta las dos que ya se
habían producido. El test lo fuerza sin mockear `open`: convierte el destino de una sección en un
directorio, y `open(path, "w")` sobre un directorio levanta `IsADirectoryError` (un `OSError`).

```python
# tests/test_scraper.py (append)
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_scraper.py -q`
Expected: FAIL — `IsADirectoryError` sale de `scrape_all` y el test nunca llega a los asserts.

- [ ] **Step 3: Write minimal implementation**

En `scraper.py`, el cuerpo del bucle de secciones pasa a rodear también la escritura:

```python
            for section in sections:
                try:
                    products = await scrape_section(page, section)
                except Exception as exc:
                    log(f"section={section.list_key} status=failed error={exc!r}")
                    continue
                if not products:
                    log(f"section={section.list_key} status=empty")
                    continue
                try:
                    path = os.path.join(out_dir, section.filename)
                    with open(path, "w", encoding="utf-8") as handle:
                        json.dump(products, handle, indent=4, ensure_ascii=False)
                except (OSError, ValueError) as exc:
                    # A write failure is contained to its own section: the sections
                    # already produced must survive, and a half-written file that is
                    # never added to `produced` is never imported.
                    log(f"section={section.list_key} status=unwritable error={exc!r}")
                    continue
                produced[section.list_key] = path
                log(f"section={section.list_key} status=ok products={len(products)}")
```

`(OSError, ValueError)` cubre los dos modos de falla **de los datos**: I/O (`OSError`) y
decodificación (`ValueError`, del que `json.JSONDecodeError` y `UnicodeDecodeError` son subclases).

A propósito **no** se captura `TypeError`: es lo que levanta `json.dump`/`json.dumps` con un objeto
no serializable (`json.dumps(object())` → `TypeError`, y `TypeError` no es subclase de `ValueError`).
Y está bien que no se capture: un `TypeError` ahí no significa "el dato es malo", significa
"`scrape_products` produjo algo que no se puede serializar", o sea un defecto de programación. Eso
debe romper ruidosamente en vez de quedar enmascarado como una sección `unwritable` que la corrida
reporta como si nada. Es inalcanzable hoy — los productos son dicts planos de strings del DOM — y esa
es exactamente la razón por la que no queremos silenciarlo el día que deje de serlo.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_scraper.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scraper.py tests/test_scraper.py
git commit -m "fix(scraper): contain write failures to their own section"
```

### Task 17: `UnicodeDecodeError` no escapa al guard

**Files:**
- Modify: `jobs/refresh_catalog.py`
- Test: `tests/test_refresh_catalog.py` (append)

- [ ] **Step 1: Write the failing tests**

`_count_items` captura `(OSError, json.JSONDecodeError)`, pero un archivo que no es UTF-8 válido
levanta `UnicodeDecodeError`, que es un `ValueError` y **no** está en ese tuple. El resultado no es
una sección sospechosa: es la corrida entera reventando, y ni las secciones sanas se importan.

```python
# tests/test_refresh_catalog.py (append)
def test_a_file_with_invalid_encoding_is_suspicious(tmp_path):
    """A decode error must not escape the guard and abort the whole run."""
    bad = tmp_path / "latin.json"
    bad.write_bytes(b'[{"title": "\xff\xfe not utf-8"}]')

    healthy, suspicious = refresh_catalog.classify({"bestsellers": str(bad)}, {})

    assert healthy == {}
    assert suspicious == ["bestsellers"]


def test_an_undecodable_section_does_not_stop_the_healthy_ones(session, tmp_path):
    """The claimed impact: healthy sections must still import."""
    for list_key in ("bestsellers", "desired"):
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(12)]), encoding="utf-8")
    (tmp_path / FILENAMES["trends"]).write_bytes(b'[{"title": "\xff\xfe"}]')

    code = refresh_catalog.run(session, data_dir=str(tmp_path), log=silent)

    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 24
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: FAIL en los dos — `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff`.

- [ ] **Step 3: Write minimal implementation**

En `jobs/refresh_catalog.py`, la cláusula de `_count_items` pasa a:

```python
    try:
        with open(path, encoding="utf-8") as handle:
            items = json.load(handle)
    except (OSError, ValueError):
        # ValueError covers both json.JSONDecodeError and UnicodeDecodeError: a file
        # that is not valid UTF-8 must be excluded as suspicious, not abort the run.
        return 0
```

`json.JSONDecodeError` ya es subclase de `ValueError`, así que la cláusula cubre los dos modos sin
perder precisión.

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS (19 passed)

- [ ] **Step 5: Commit**

```bash
git add jobs/refresh_catalog.py tests/test_refresh_catalog.py
git commit -m "fix(jobs): treat undecodable sections as suspicious instead of crashing"
```

### Task 18: el test de dry-run prueba también las listas

**Files:**
- Modify: `tests/test_refresh_catalog.py`

- [ ] **Step 1: Strengthen the existing test**

El hallazgo SUGGESTION del review: `test_dry_run_writes_nothing` sólo mira la tabla `Product`, así
que un dry-run que igual escribiera ranks de `ProductList` pasaría. El helper `snapshot_catalog`
ya cubre las dos tablas y ya se usa en otro test. El cambio es de tres líneas y hace que el nombre
del test sea verdad entero:

```python
def test_dry_run_writes_nothing(session, tmp_path):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    before = snapshot_catalog(session)

    code = refresh_catalog.run(session, data_dir=str(tmp_path), dry_run=True, log=silent)

    assert code == 0
    assert snapshot_catalog(session) == before
```

Antes de este cambio, el test se sembraba desde una DB vacía: con `before` vacío la comparación
prueba que no se escribió ni un producto ni un rank.

- [ ] **Step 2: Run and confirm it is still green**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS (19 passed) — `import_from_json` hace `rollback()` con `dry_run`, así que el
snapshot se mantiene. Si esto **fallara**, sería un hallazgo real: significaría que el dry-run
escribe ranks.

- [ ] **Step 3: Verify the full suite**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: 116 passed (113 + 3 nuevos)

- [ ] **Step 4: Commit**

```bash
git add tests/test_refresh_catalog.py
git commit -m "test(jobs): prove the dry run also leaves list ranks untouched"
```

### Ronda 2 del 2.5 — la frontera del `except` en la escritura

**Origen:** review de calidad del slice 2.5. Una sola corrección de fondo más tres cierres baratos.

El error de razonamiento de la Task 16: se argumentó que `TypeError` debe romper fuerte por ser un
defecto de código, pero la cláusula elegida (`ValueError` entero) contiene también el
`ValueError("Circular reference detected")` que `json.dump` levanta con un objeto cíclico — el mismo
tipo de defecto. La frontera correcta separa **error de dato** de **defecto de código**:

| Causa | Excepción | ¿Contener? |
|---|---|---|
| Disco lleno, permisos, path es directorio | `OSError` | Sí — dato/entorno |
| Texto que no se puede codificar en UTF-8 | `UnicodeEncodeError` | Sí — dato |
| Objeto cíclico | `ValueError` (no `UnicodeEncodeError`) | **No** — defecto de código |
| Objeto no serializable | `TypeError` | **No** — defecto de código |

- [ ] **Step 1: Narrow the write-path clause**

```python
                try:
                    path = os.path.join(out_dir, section.filename)
                    with open(path, "w", encoding="utf-8") as handle:
                        json.dump(products, handle, indent=4, ensure_ascii=False)
                except (OSError, UnicodeEncodeError) as exc:
                    # Only data problems are contained: I/O failures and text that cannot be
                    # encoded. A ValueError (circular reference) or TypeError (non-serializable
                    # object) is a defect in scrape_products and must propagate loudly instead of
                    # being masked as an unwritable section.
                    log(f"section={section.list_key} status=unwritable error={exc!r}")
                    continue
```

`_count_items` en `jobs/refresh_catalog.py` **se queda** con `(OSError, ValueError)`: ahí el
`ValueError` completo es correcto, porque todo lo que `open`+`json.load` pueden levantar con esas
banderas significa "esta sección no sirve".

- [ ] **Step 2: Pin the deliberate `TypeError` boundary**

Esta decisión se volvió load-bearing y no tenía cobertura: agregar `TypeError` a la cláusula
sobrevivía toda la suite. El test **nace verde** (el `TypeError` ya propaga hoy); lo que lo hace
valioso es que la mutación que agrega `TypeError` lo pone en rojo. No fuerces un rojo falso.

```python
# tests/test_scraper.py (append)
def test_a_non_serializable_payload_fails_loudly(monkeypatch, tmp_path):
    """A code defect must not be masked as an unwritable section."""
    browser = _FakeBrowser()
    monkeypatch.setattr(scraper, "async_playwright", lambda: _FakePlaywrightManager(browser))

    async def section_scraper(page, section):
        return [{"title": object()}]

    monkeypatch.setattr(scraper, "scrape_section", section_scraper)

    with pytest.raises(TypeError):
        asyncio.run(scraper.scrape_all(str(tmp_path)))
```

- [ ] **Step 3: `scrape_all`'s docstring names both failure modes**

El docstring decía sólo "a section that raises writes no file", pero ahora hay un segundo desenlace
contenido y es el contrato de `produced` para el orquestador:

```python
    """Scrape every section into ``out_dir``; a broken section is skipped.

    Returns a ``{list_key: path}`` map containing only the sections that produced
    products and persisted them. A section that fails to scrape, or that fails to
    write its file, is omitted from the map — which is what makes the import skip
    it and leave that list's ranks untouched.
    ...
    """
```

- [ ] **Step 4: `test_dry_run_writes_nothing` proves the claim in its name**

Dejarlo con la fixture sin sembrar hacía que `before` fuera `([], [])`, así que la aserción
equivalía a "las dos tablas quedaron vacías": probaba que el dry-run **no crea** filas, pero no
podía detectar uno que **borre o reescriba** ranks existentes. Sembrar el baseline hace que el test
valga lo que su mensaje de commit prometía:

```python
def test_dry_run_writes_nothing(session, catalog_seed, tmp_path):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    before = snapshot_catalog(session)

    code = refresh_catalog.run(session, data_dir=str(tmp_path), dry_run=True, log=silent)

    assert code == 0
    assert snapshot_catalog(session) == before
```

La fixture `catalog_seed` (2 en `bestsellers`, 2 en `trends`) deja `before` no vacío y ya se usa con
`session` en otro test del mismo archivo.

- [ ] **Step 5: Verify the full suite**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: 117 passed (116 + 1). Los otros tests no cambian.

- [ ] **Step 6: Commit**

```bash
git add scraper.py tests/test_scraper.py tests/test_refresh_catalog.py
git commit -m "fix(scraper): contain only data errors and pin the loud code-defect path"
```

### Cierre del slice 2.5

- [ ] Correr `./venv/bin/python -m jobs.refresh_catalog --data-dir . --dry-run` → `sections_ok=3`
- [ ] Abrir el PR apilado sobre `feat/refresh-catalog-02-orchestrator`

---

## Slice 3 — Empaquetado y despliegue en Railway (PR #3)

### Task 10: `requirements-scraper.txt` con Playwright pineado

**Files:**
- Create: `requirements-scraper.txt`

- [ ] **Step 1: Pin the version already in use**

Tu venv local tiene `playwright 1.57.0` instalado y el scraper funciona con esa versión. Ese
es el baseline a pinear, no la última publicada (hoy 1.63.0): pineamos lo probado, que es la
regla que este repo ya aprendió con sqlmodel.

```text
# Scraper-only dependencies. The web service never imports scraper.py and must
# not install a browser: this file exists so playwright can be pinned and drift
# cannot reach the cron unnoticed, the same way requirements.txt pins the web.
#
# The chromium build must match this playwright version, so the Dockerfile runs
# `playwright install --with-deps chromium` from inside this environment.
-r requirements.txt
playwright==1.57.0
```

- [ ] **Step 2: Verify the pin resolves**

Run: `./venv/bin/python -m pip install --dry-run -r requirements-scraper.txt`
Expected: resuelve `playwright==1.57.0` sin errores.

**Con `--dry-run`, a propósito.** La primera versión de este paso instalaba Playwright de verdad en
el venv del worktree, y eso rompe el invariante de que la suite corre sin browser (que es lo que
prueba que el import tolerante de `scraper.py` funciona). `pip install --dry-run` resuelve el árbol
de dependencias sin tocar el entorno.

- [ ] **Step 3: Commit**

```bash
git add requirements-scraper.txt
git commit -m "build: pin the scraper-only playwright dependency"
```

### Task 11: `.dockerignore`

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Create it**

El contexto de build es la raíz del repo, y ahí adentro hay un `venv/` (cientos de MB) y un
`database.db` de 3.8 MB. Sin `.dockerignore`, `COPY . .` se los traga.

```text
# Build context hygiene: the scraper image must not carry the dev venv, the
# local database, or the vcs metadata.
venv/
.venv/
.git/
.gitignore
.atl/
__pycache__/
*.pyc
.pytest_cache/
.idea/
.vscode/
database.db
*.db
tests/
docs/
.env
```

No se excluye nada que la web necesite (`main.py`, `templates/`, `static/`, `catalog.py`,
`models.py`, `services.py`, `alembic/`, `alembic.ini`, `Procfile`). Verificado: ningún
módulo referencia los directorios `bestsellers/` ni `tendencias/` (grep sobre `*.py` y
`*.html`).

- [ ] **Step 2: Verify nothing the web needs is excluded**

Run: `./venv/bin/python -c "import main; print('web imports ok')"`
Expected: `web imports ok`

- [ ] **Step 3: Commit**

```bash
git add .dockerignore
git commit -m "build: keep the dev venv and the local database out of the build context"
```

### Task 12: `scraper/Dockerfile`

**Files:**
- Create: `scraper/Dockerfile`

- [ ] **Step 1: Create it**

**No lo pongas en la raíz.** Railway, si encuentra un `Dockerfile` en la raíz, puede buildear el
servicio **web** con él y voltear el deploy de la app. Va en `scraper/`, y el servicio cron se
configura con la ruta del Dockerfile.

```dockerfile
# Scraper-only image for the scheduled catalog refresh.
#
# Lives outside the repository root on purpose: a root Dockerfile would make
# Railway build the WEB service with it and break the deploy. The web service
# keeps using nixpacks with the Procfile.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first so the browser layer is cached across code changes.
COPY requirements.txt requirements-scraper.txt ./
RUN pip install --no-cache-dir -r requirements-scraper.txt \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# The cron service overrides this with the schedule; the command must finish.
CMD ["python", "-m", "jobs.refresh_catalog"]
```

- [ ] **Step 2: Verify the build works locally**

Run:
```bash
docker build -f scraper/Dockerfile -t regalame-scraper-test .
```
Expected: build OK (avisa si tu Docker no está corriendo, y saltá al Step 3 marcándolo como no
verificado en el PR).

- [ ] **Step 3: Verify the container starts and can import the app**

Run:
```bash
docker run --rm -e DATABASE_URL=sqlite:///database.db regalame-scraper-test \
  python -c "import jobs.refresh_catalog, scraper; print(scraper.async_playwright is not None)"
```
Expected: `True` — o sea, dentro del contenedor Playwright **sí** está instalado. Ese es
justamente el punto del archivo separado.

- [ ] **Step 4: Commit**

```bash
git add scraper/Dockerfile
git commit -m "build: add the scraper image outside the repo root"
```

### Task 13: Documentar el despliegue del cron

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a deployment section**

Después de la sección `## 🚢 Despliegue (Railway)`:

```markdown
### Refresco periódico del catálogo (servicio cron)

El catálogo se refresca solo, una vez por día, desde un segundo servicio del mismo proyecto
de Railway. Ese servicio **no** es el web: la web sigue usando el `Procfile`.

1. En Railway, crea un servicio nuevo en el mismo proyecto, apuntando al mismo repositorio.
2. En la configuración del servicio:
   - **Root directory:** la raíz del repositorio.
   - **Dockerfile path:** `scraper/Dockerfile`.
   - **Cron schedule:** `0 4 * * *`.
   - **Start command:** `python -m jobs.refresh_catalog`.
3. Variables de entorno: sólo `DATABASE_URL`, referenciando el Postgres del proyecto
   (`${{Postgres.DATABASE_URL}}`). No hacen falta `SECRET_KEY` ni las de email.
4. Verifica la primera corrida en los logs: una línea `section=... status=...` por sección y
   un resumen `import: created=... updated=... lists=... sections_ok=...`.

Un `sections_ok` menor a 3 significa que alguna sección falló o salió sospechosa. El catálogo
existente queda intacto: la corrida siguiente lo reintenta.

**Prueba local, sin browser y sin red:**

```bash
python -m jobs.refresh_catalog --data-dir . --dry-run
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document the scheduled catalog refresh service"
```

- [ ] **Step 3: Abrir el PR del slice 3**

Título: `build: run the catalog refresh as a scheduled Railway service`
Cuerpo: la advertencia del Dockerfile fuera de la raíz, el pin de Playwright, y la evidencia
de los steps 2-3 de la Task 12 (o la nota de no verificado si no había Docker).

---

## Slice 4 — Desactivación de productos obsoletos (PR #4)

### Task 14: `catalog.deactivate_absent_products()`

**Files:**
- Modify: `catalog.py`
- Test: `tests/test_catalog_deactivation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_catalog_deactivation.py
"""Deactivating the products that left every scraped list."""

from datetime import datetime

from sqlmodel import select

from catalog import deactivate_absent_products
from models import Product, ProductList, utcnow_naive


def make_product(session, asin, active=True, updated_at=None):
    product = Product(asin=asin, title=asin, title_normalized=asin.lower(),
                      image_url=None, url=f"https://www.amazon.es/dp/{asin}",
                      category="Varios", category_slug="varios",
                      price_numeric=None, price_raw="N/A",
                      scraped_at=datetime(2026, 1, 1), is_active=active,
                      updated_at=updated_at or utcnow_naive())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def test_a_product_in_no_list_is_deactivated(session):
    ghost = make_product(session, "GHOSTGHOST")
    counted = make_product(session, "COUNTEDAAA")
    session.add(ProductList(product_id=counted.id, list_key="bestsellers", rank=1))
    session.commit()

    deactivated = deactivate_absent_products(session, list_keys=["bestsellers"])

    assert deactivated == 1
    session.refresh(ghost)
    session.refresh(counted)
    assert ghost.is_active is False
    assert counted.is_active is True


def test_a_product_in_another_list_survives(session):
    survivor = make_product(session, "SURVIVORAA")
    session.add(ProductList(product_id=survivor.id, list_key="trends", rank=1))
    session.commit()

    deactivated = deactivate_absent_products(session, list_keys=["bestsellers", "trends"])

    assert deactivated == 0
    session.refresh(survivor)
    assert survivor.is_active is True


def test_an_already_inactive_product_is_not_counted_twice(session):
    make_product(session, "SLEEPYAAAA", active=False)
    assert deactivate_absent_products(session, list_keys=["bestsellers"]) == 0


def test_deactivation_refreshes_updated_at(session):
    stamp = datetime(2026, 1, 1)
    ghost = make_product(session, "STAMPSTAMP", updated_at=stamp)

    deactivate_absent_products(session, list_keys=["bestsellers"])

    session.refresh(ghost)
    assert ghost.updated_at > stamp
```

`updated_at` se pasa explícito en el pasado en lugar de leer el valor recién creado: comparar
contra `utcnow_naive()` de hace microsegundos es un test que puede oscilar.

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_catalog_deactivation.py -q`
Expected: FAIL con `ImportError: cannot import name 'deactivate_absent_products'`

- [ ] **Step 3: Write minimal implementation**

En `catalog.py`, agregá `update` al import de sqlalchemy (línea 14) y la función:

```python
# catalog.py — line 14 becomes:
from sqlalchemy import case, delete, func, update
```

```python
# catalog.py — add after list_categories()
def deactivate_absent_products(session: Session, list_keys: list[str]) -> int:
    """Mark inactive every product that appears in none of ``list_keys``.

    Only the refresh job calls this, and only on a healthy run, where
    ``list_keys`` is every scraped list: a product still present in any list is
    never touched. Rows are flagged, never deleted, so existing URLs keep
    resolving. Returns the number of products deactivated.
    """
    present = select(ProductList.product_id).where(ProductList.list_key.in_(list_keys))
    absent = session.exec(
        select(Product.id).where(
            Product.is_active == True,  # noqa: E712
            Product.id.not_in(present),
        )
    ).all()
    if not absent:
        return 0
    session.exec(
        update(Product)
        .where(Product.id.in_(absent))
        .values(is_active=False, updated_at=utcnow_naive())
    )
    session.commit()
    return len(absent)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_catalog_deactivation.py -q`
Expected: PASS (4 passed)

`utcnow_naive` ya está importado en `catalog.py:17`.

- [ ] **Step 5: Commit**

```bash
git add catalog.py tests/test_catalog_deactivation.py
git commit -m "feat(catalog): deactivate the products that left every list"
```

### Ronda 2 del slice 4 — el guard cuenta lo que el import importa (aplicar DESPUÉS del Task 15)

**Orden de lectura:** este bloque toca `_count_items` (que existe desde el Task 5) y el gate de
`_finish` (que recién se cablea en el Task 15), así que va al final. Leelo como la ronda 2 completa
del slice, no como parte del Task 14.

**Origen:** review de calidad del slice 4. El hallazgo grande es que el punto ciego del guard
—documentado desde el slice 2 y entonces benigno— pasa a ser **destructivo** al combinarse con la
desactivación.

El guard cuenta **entradas crudas** del JSON, pero `import_from_json` descarta entradas sin `url` y
colapsa ASINs repetidos. Un archivo inflado con duplicados (≥50% de entradas crudas, pocos ASINs
únicos) pasa como "sano", los ranks se reconstruyen con esos pocos ASINs, y si las tres listas vienen
así la desactivación da de baja todo lo que no esté en esos conjuntos — en silencio, con exit 0.
Se auto-cura en la próxima corrida sana (`import_from_json` vuelve a activar lo que reaparece), así
que el hueco es de hasta un día, no pérdida permanente. Pero es evitable en la raíz.

**El arreglo no es un tope arbitrario: es contar lo mismo que el import.**

- [ ] **Step 1: `_count_items` pasa a contar ASINs únicos**

Renombrá la función para que el nombre diga la verdad, y usá el **mismo** criterio que el import:

```python
def _count_importable(path):
    """Number of distinct ASINs the import would create from a produced file.

    Mirrors import_from_json: entries without a url are skipped and repeated ASINs
    collapse to one product, so the guard compares like with like against the
    per-list baseline of distinct ProductList rows. Counting raw JSON entries
    instead would let a duplicate-padded file pass as healthy while importing a
    handful of products — and with deactivation wired in, that would retire most
    of the catalog.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            items = json.load(handle)
    except (OSError, ValueError):
        return 0
    if not isinstance(items, list):
        return 0
    return len({
        extract_asin(item.get("url"))
        for item in items
        if isinstance(item, dict) and item.get("url")
    })
```

Actualizá los dos sitios que la llaman (`classify` y la línea de log de sospechosas), y sumá
`extract_asin` al import de `catalog`:

```python
from catalog import deactivate_absent_products, extract_asin, import_from_json
```

- [ ] **Step 2: el test que mata el punto ciego**

```python
# tests/test_refresh_catalog.py (append)
def test_a_duplicate_padded_section_is_suspicious(tmp_path):
    """The guard must count what the import imports, not raw JSON entries."""
    padded = tmp_path / "padded.json"
    items = []
    for index in (0, 1):
        for _ in range(10):
            items.append(product_json("bestsellers", index))
    padded.write_text(json.dumps(items), encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify(
        {"bestsellers": str(padded)}, {"bestsellers": 20})

    assert healthy == {}
    assert suspicious == ["bestsellers"]
```

Con el código viejo, `_count_items` devuelve 20 → pasa el guard → el test **falla**. Con el nuevo,
2 ASINs únicos < 10 → sospechosa. Es el pin exacto del hallazgo.

No hace falta una variante end-to-end: la ruta "una sección no sana ⇒ no se desactiva nada" ya está
sujeta por `test_a_partial_run_deactivates_nothing`.

- [ ] **Step 3: la función queda total para un universo vacío**

`list_keys=[]` compila a `NOT IN (subquery vacía)`, que es verdadero para **todas** las filas: hoy
desactivaría el catálogo entero. El único llamador está detrás del gate, pero el costo de un futuro
llamador distraído es catastrófico.

```python
    if not list_keys:
        # An empty universe means nothing was considered, so nothing can be retired.
        return 0
```

```python
# tests/test_catalog_deactivation.py (append)
def test_an_empty_universe_deactivates_nothing(session):
    ghost = make_product(session, "GHOSTGHOST")
    counted = make_product(session, "COUNTEDAAA")
    session.add(ProductList(product_id=counted.id, list_key="bestsellers", rank=1))
    session.commit()

    assert deactivate_absent_products(session, list_keys=[]) == 0

    session.refresh(ghost)
    session.refresh(counted)
    assert ghost.is_active is True
    assert counted.is_active is True
```

- [ ] **Step 4: se va la cláusula muerta del gate**

La revisión lo demostró por mutación: quitar `not suspicious` **no rompe ningún test**, porque
`len(healthy) == len(SECTIONS)` ya lo implica (healthy y suspicious particionan `produced`, y
`produced ⊆ SECTIONS` en las dos rutas de `run`).

```python
    # len(healthy) == len(SECTIONS) already implies suspicious == []: healthy and
    # suspicious partition produced, and produced is always a subset of SECTIONS.
    if not dry_run and len(healthy) == len(SECTIONS):
```

- [ ] **Step 5: verificar y commitear**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: 126 passed (124 + 2).

```bash
git add jobs/refresh_catalog.py catalog.py tests/test_catalog_deactivation.py tests/test_refresh_catalog.py
git commit -m "fix(jobs): count importable ASINs in the health guard"
```

### Ronda 3 del slice 4 — la barra estricta para desactivar (aplicar DESPUÉS del Task 15)

**Origen:** hallazgo WARNING de la lente nativa R3 sobre el slice 5, con disposición `worsened`.

El agujero: el gate exige `len(healthy) == len(SECTIONS)`, pero `classify` llama "sana" a una sección
que trae **≥50% del baseline** (`MIN_HEALTHY_RATIO`). Una sección que cae de 50 a 25 productos
—página truncada— sigue contando como sana; con las tres así, el gate pasa y la desactivación retira
los 25 que faltan, que no se fueron de Amazon: el scrape vino incompleto.

La tolerancia del guard está bien para el **import** (importar de menos es seguro). Aplicada a la
**desactivación** retira productos. Es el mismo mecanismo del punto ciego de duplicados que se
arregló en la ronda 2, entrando por otra puerta.

**Por qué la barra estricta es defendible y no conservadora de más:** las listas de Amazon vienen
topadas a 50 ítems por categoría (`scrape_products` corta con `items[:50]`), así que una sección
estable cuando el scrape funciona y una caída grande significan scrape degradado, no rotación real.
Equivocarse del lado estricto sólo **posterga** una retirada; equivocarse del otro lado hace
desaparecer productos del catálogo.

- [ ] **Step 1: el helper de completitud**

```python
def _every_section_complete(produced, baseline):
    """Whether every scraped section reached at least its previous size.

    The import tolerates a section shrinking to ``MIN_HEALTHY_RATIO`` of its baseline,
    because importing fewer products is safe. Retiring products is not: the Amazon
    lists are capped at 50 items per category, so a working scrape keeps a section's
    size stable and a drop means a degraded scrape rather than genuine churn. Demanding
    a complete run can only delay a retirement; tolerating a short one can make
    products disappear.
    """
    return all(
        _count_importable(path) >= baseline.get(list_key, 0)
        for list_key, path in produced.items()
    )
```

- [ ] **Step 2: el gate la usa, y dice por qué saltea**

```python
    # Deactivation runs only on a complete, fully healthy run: on a partial run a
    # product could be absent merely because its own section failed or came back short.
    # len(healthy) == len(SECTIONS) already implies suspicious == []: healthy and
    # suspicious partition produced, and produced is always a subset of SECTIONS.
    if not dry_run and len(healthy) == len(SECTIONS):
        if _every_section_complete(produced, baseline):
            log(f"deactivated={deactivate_absent_products(session, list_keys=sorted(healthy))}")
        else:
            log("deactivation skipped: at least one section came back shorter than its baseline")
```

El `else` importa: sin esa línea, una corrida sana pero corta no dejaría **ninguna** traza de por qué
no se retiró nada.

- [ ] **Step 3: el test que mata el agujero**

```python
# tests/test_refresh_catalog.py (append)
def test_a_short_but_healthy_run_deactivates_nothing(session):
    """All three sections healthy, but one came back shorter: nothing may be retired."""
    refresh_catalog.run(
        session,
        scrape_fn=fake_scrape({"bestsellers": 20, "trends": 20, "desired": 20}),
        log=silent)
    ghost = _ghost_product()
    session.add(ghost)
    session.commit()
    session.refresh(ghost)

    # 15 of 20: above MIN_HEALTHY_RATIO, so the section is healthy — and short.
    refresh_catalog.run(
        session,
        scrape_fn=fake_scrape({"bestsellers": 15, "trends": 20, "desired": 20}),
        log=silent)

    session.refresh(ghost)
    assert ghost.is_active is True
```

Con el código de la ronda 2, bestsellers (15 ≥ 10) es sana, el gate pasa y el fantasma queda
inactivo → el test **falla**. Es el pin exacto del hallazgo.

- [ ] **Step 4: `extract_asin` no puede tumbar la corrida**

`_count_importable` llama `extract_asin(item.get("url"))` fuera del `try`, y `extract_asin` hace
`re.search`, que levanta `TypeError` con un valor que no sea string. Un `url` verdadero pero no-string
en un archivo pasado con `--data-dir` aborta la corrida entera, en vez de marcar esa sección como
sospechosa. Filtralo por tipo, que además es lo correcto semánticamente: una url que no es string no
es importable.

```python
        return len({
            extract_asin(item["url"])
            for item in items
            if isinstance(item, dict)
            and isinstance(item.get("url"), str)
            and item["url"]
        })
```

```python
# tests/test_refresh_catalog.py (append)
def test_a_non_string_url_does_not_crash_the_guard(tmp_path):
    weird = tmp_path / "weird.json"
    weird.write_text(json.dumps([{"url": 12345}]), encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify({"bestsellers": str(weird)}, {})

    assert healthy == {}
    assert suspicious == ["bestsellers"]
```

- [ ] **Step 5: el UPDATE deja de expandir un parámetro por id**

`Product.id.in_(absent)` con una lista de Python emite un bind por id. En una limpieza grande —primer
arranque con muchos obsoletos— puede pasar el límite de parámetros del backend y **fallar después de
que `import_from_json` ya commiteó**, dejando la desactivación a medias en una corrida por lo demás
exitosa. El `SELECT` se queda (da el conteo y el early return); lo que cambia es el `UPDATE`, que usa
el mismo predicado que el `SELECT` en vez de la lista:

```python
    session.exec(
        update(Product)
        .where(
            Product.is_active == True,  # noqa: E712
            Product.id.not_in(present),
        )
        .values(is_active=False, updated_at=utcnow_naive())
    )
    session.commit()
    return len(absent)
```

Sin test nuevo: el comportamiento ya está sujeto por los tests existentes, y el límite de parámetros
no es reproducible con un catálogo de prueba chico. Es una remoción de riesgo, no un cambio de
contrato.

- [ ] **Step 6: verificar y commitear**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: 128 passed (126 + 2).

```bash
git add jobs/refresh_catalog.py catalog.py tests/test_refresh_catalog.py
git commit -m "fix(jobs): require a complete run before retiring products"
```

### Task 15: Cablear la desactivación en el job (sólo en corrida sana)

**Files:**
- Modify: `jobs/refresh_catalog.py`
- Test: `tests/test_refresh_catalog.py` (append)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_refresh_catalog.py (append)
def _ghost_product():
    return Product(asin="GHOSTGHOST", title="Fantasma", title_normalized="fantasma",
                   image_url=None, url="https://www.amazon.es/dp/GHOSTGHOST",
                   category="Varios", category_slug="varios",
                   price_numeric=None, price_raw="N/A", scraped_at=datetime(2026, 1, 1))


def test_a_healthy_run_deactivates_the_ghost(session):
    ghost = _ghost_product()
    session.add(ghost)
    session.commit()
    session.refresh(ghost)
    session.add(ProductList(product_id=ghost.id, list_key="trends", rank=3))
    session.commit()

    refresh_catalog.run(session, scrape_fn=fake_scrape(FULL), log=silent)

    session.refresh(ghost)
    assert ghost.is_active is False


def test_a_partial_run_deactivates_nothing(session):
    ghost = _ghost_product()
    session.add(ghost)
    session.commit()
    session.refresh(ghost)
    session.add(ProductList(product_id=ghost.id, list_key="trends", rank=3))
    session.commit()

    refresh_catalog.run(session, scrape_fn=fake_scrape(dict(FULL, trends=None)), log=silent)

    session.refresh(ghost)
    assert ghost.is_active is True


def test_dry_run_never_deactivates(session):
    ghost = _ghost_product()
    session.add(ghost)
    session.commit()
    session.refresh(ghost)

    refresh_catalog.run(session, scrape_fn=fake_scrape(FULL), dry_run=True, log=silent)

    session.refresh(ghost)
    assert ghost.is_active is True
```

**No hay que quitarle la pertenencia a mano.** Al revés: sembrar el fantasma en `trends` es lo que
hace fuerte al test. `import_from_json` **borra y reconstruye** los ranks de cada lista que procesa
(`catalog.py:278-283`), así que una corrida sana con el scrape completo descarta la pertenencia del
fantasma —su ASIN no está en los archivos— y lo deja ausente de las tres listas. Ese es exactamente
el camino real que queremos probar.

Un `session.exec(delete(...))` manual antes del `run` haría pasar el test igual, pero **midiendo otra
cosa**: saltaría el rebuild que es el que realmente deja obsoleto al producto. No lo agregues.

- [ ] **Step 2: Run test to verify it fails**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: FAIL en `test_a_healthy_run_deactivates_the_ghost`
(`assert True is False`); los otros dos pasan por accidente y quedan como regresión.

- [ ] **Step 3: Write minimal implementation**

```python
# jobs/refresh_catalog.py — import line becomes:
from catalog import deactivate_absent_products, import_from_json
```

```python
# jobs/refresh_catalog.py — _finish() gets the tail:
def _finish(session, produced, baseline, dry_run, log):
    healthy, suspicious = classify(produced, baseline)
    for list_key in suspicious:
        log(f"section={list_key} status=suspicious excluded")

    if not healthy:
        log("refresh: no healthy sections, nothing imported")
        return 1

    stats = import_from_json(session, data_files=healthy, dry_run=dry_run)
    log(f"import: created={stats['created']} updated={stats['updated']} "
        f"lists={stats['lists']} sections_ok={len(healthy)}")

    # Deactivation runs only on a fully healthy run: on a partial run a product
    # could be absent merely because its section failed.
    if not dry_run and not suspicious and len(healthy) == len(SECTIONS):
        log(f"deactivated={deactivate_absent_products(session, list_keys=sorted(healthy))}")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./venv/bin/python -m pytest tests/test_refresh_catalog.py -q`
Expected: PASS (todos)

- [ ] **Step 5: Verify the full suite**

Run: `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: todo verde.

- [ ] **Step 6: Commit**

```bash
git add jobs/refresh_catalog.py tests/test_refresh_catalog.py
git commit -m "feat(jobs): deactivate obsolete products on a healthy run only"
```

- [ ] **Step 7: Abrir el PR del slice 4**

Título: `feat(jobs): retire the products that left every Amazon list`

---

## Verificación final (antes del cierre)

- [ ] **Suite completa:** `./venv/bin/python -m pytest -q --ignore=tests/test_e2e.py` → todo verde.
- [ ] **El CI no instala Playwright:** confirmar en el log del PR que
  `pip install -r requirements-dev.txt` no trae playwright y que
  `pytest --ignore=tests/test_e2e.py` colecta `tests/test_scraper.py` sin error.
- [ ] **La web sigue con `Procfile`:** en Railway, el servicio web no cambió su builder.
- [ ] **Corrida real del cron:** la primera ejecución en la nube deja en los logs una línea por
  sección y el resumen final. Si `sections_ok` es 0, revisar el bloqueo anti-bot antes de
  tocar cualquier otra cosa.
- [ ] **Frescura visible:** en producción, `scraped_at` del catálogo corresponde al día de la
  corrida.
