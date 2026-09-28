# Catálogo Navegable — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir el catálogo de productos (hoy leído desde tres JSON en cada request) en un motor consultable sobre la base de datos, con búsqueda, filtros, orden y paginación resueltos en el servidor, preservando URLs y SEO.

**Architecture:** Dos tablas nuevas (`Product`, `ProductList`) en `models.py`; un módulo nuevo `catalog.py` con normalización, parseo de precio, extracción de ASIN, motor de consulta (`search_products`) e import idempotente desde JSON; y una capa de rutas en `main.py` que consulta el catálogo y renderiza con Jinja + HTMX progresivo. `services.py` se limpia: pierde todo el código de catálogo y conserva sorteo, scraping y enlaces de afiliado.

**Tech Stack:** Python 3.14, FastAPI, SQLModel/SQLAlchemy, Alembic, Jinja2, HTMX 1.9.10, pytest + `fastapi.testclient`.

**Baseline:** 17 tests verdes con `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`. Los 2 tests de `tests/test_e2e.py` requieren Playwright + servidor y **no** forman parte del baseline.

**Convenciones obligatorias:**
- Todo con **TDD estricto**: test que falla → lo ves fallar → código mínimo → verde → commit.
- Comandos con el venv del worktree: `venv/bin/python`, `venv/bin/pytest`, `venv/bin/alembic`.
- Working directory: `/Users/toni.robres/Pycharmprojects/regalame_gemini3-worktrees/catalogo-navegable`.
- Commits convencionales, sin atribución a IA.
- Los artifacts de código y plantillas van en inglés (comentarios, identificadores). El copy visible al usuario permanece en español, como el resto de la app.

---

## Decisiones tomadas para cubrir huecos del diseño

El spec aprobado define el modelo, el motor y las rutas, pero deja cinco puntos sin resolver. Este plan los resuelve así (quedan explícitos para que puedas vetarlos antes de ejecutar):

| # | Hueco | Resolución | Por qué |
|---|---|---|---|
| G1 | El spec **elimina** `get_random_products()`, pero el dashboard lo usa 3 veces. Sin reemplazo, el dashboard pierde la variedad. | Se añade `"random"` como valor válido de `CatalogQuery.sort`, implementado con `ORDER BY random()` (portable en SQLite y PostgreSQL). | Mínimo cambio que preserva el comportamiento actual y reutiliza el motor en vez de añadir una función suelta. |
| G2 | `get_blog_post_detail()` se reimplementa sobre `search_products()`, pero el tope de `per_page` es 60 y el blog muestra **todos** los coincidentes. | `get_blog_post_detail()` pagina en bucle hasta agotar `total_pages`. | Usa solo la API pública y respeta el tope. |
| G3 | `_parse_price()` se mueve "sin reescribirse" (devuelve `0.0` al fallar), pero el modelo quiere `price_numeric = None` si no es convertible. | `_parse_price()` se mueve tal cual; **el import mapea** `parsed > 0` → valor, si no → `None`. | Honra ambas afirmaciones del spec. |
| G4 | El criterio `category` del blog usaba *containment* de slug; `search_products` usa match exacto. | Match exacto (como pide el spec). Verificado: las 11 entradas de `blog_config.py` matchean categorías existentes de forma exacta → sin regresión. | El spec dice que los filtros "son exactamente los del catálogo". |
| G5 | Las plantillas actuales usan `item.image` / `item.price`; el modelo define `image_url` / `price_raw`. | Se actualizan las plantillas a los nombres reales del modelo. | Sin capa de alias; la presentación referencia el modelo real. |

Además, **el tag de afiliado se inyecta en el render**: `url` se guarda sin tag, y las rutas pasan `generate_amazon_link` a Jinja como `amazon_link`, que envuelve los links "Ver en Amazon". El formulario de "Añadir" envía la URL cruda y `add_wish` ya aplica `generate_amazon_link()`.

---

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `models.py` (modificar) | Añade `Product` y `ProductList`. |
| `catalog.py` (crear) | Normalización (`slugify`, `normalize_text`), `extract_asin`, `_parse_price`, `CatalogQuery`/`CatalogResult`, `search_products`, `list_categories`, `import_from_json`. Sin dependencias de `services.py`. |
| `import_catalog.py` (crear) | CLI: importa los tres JSON. `--dry-run` opcional. |
| `alembic/versions/<rev>_add_product_tables.py` (crear) | Crea `product` y `productlist` con índices. |
| `services.py` (modificar) | Elimina el código de catálogo; conserva `perform_draw`, `generate_amazon_link`, `scrape_metadata`, `get_blog_posts_list`; reimplementa `get_blog_post_detail` sobre `catalog.search_products`. |
| `main.py` (modificar) | Ruta `/catalog`; migra `/bestsellers`, `/trends`, `/most-desired`, `/ideas/{slug}`, dashboard, sitemap y `/blog/{slug}`. |
| `templates/base.html` (modificar) | `{% block extra_head %}` + buscador global. |
| `templates/catalog.html` (crear) | Página de catálogo: filtros + include del partial. |
| `templates/partials/catalog_results.html` (crear) | Contador + grid + estado vacío + paginador (target HTMX). |
| `templates/dashboard.html` (modificar) | `image_url`/`price_raw`/`amazon_link`. |
| `templates/category_seo.html` (reescribir) | Landing SEO con paginación, canonical y prev/next; reusa el partial. |
| `templates/bestsellers.html`, `trends.html`, `most_desired.html` (borrar) | Reemplazadas por `catalog.html`. |
| `tests/conftest.py` (modificar) | Fixture `catalog_seed`. |
| `tests/test_catalog.py` (crear) | Unitarios + integración del motor e import. |
| `tests/test_catalog_routes.py` (crear) | Rutas `/catalog`, legacy, `/ideas/{slug}`, SEO, dashboard. |

---

## Task 1: Modelos `Product` y `ProductList`

**Files:**
- Modify: `models.py`
- Test: `tests/test_catalog.py` (crear)

- [ ] **Step 1: Write the failing test**

Create `tests/test_catalog.py`:

```python
from datetime import datetime

from sqlmodel import select

from models import Product, ProductList


def test_product_and_productlist_roundtrip(session):
    product = Product(
        asin="B0049U0DMC",
        title="Lavazza Qualità Oro",
        title_normalized="lavazza qualita oro",
        image_url="https://img.example/1.jpg",
        url="https://www.amazon.es/dp/B0049U0DMC",
        category="Alimentación y bebidas",
        category_slug="alimentacion-y-bebidas",
        price_numeric=25.69,
        price_raw="25,69 €",
        scraped_at=datetime(2026, 9, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    link = ProductList(product_id=product.id, list_key="bestsellers", rank=1)
    session.add(link)
    session.commit()

    stored = session.exec(select(Product).where(Product.asin == "B0049U0DMC")).first()
    assert stored is not None
    assert stored.title_normalized == "lavazza qualita oro"
    assert stored.price_numeric == 25.69
    assert stored.is_active is True
    assert stored.updated_at is not None

    stored_link = session.exec(select(ProductList).where(ProductList.list_key == "bestsellers")).first()
    assert stored_link.product_id == product.id
    assert stored_link.rank == 1


def test_productlist_unique_per_product_and_list(session):
    product = Product(
        asin="X1",
        title="T",
        title_normalized="t",
        url="https://www.amazon.es/dp/X1",
        category="Varios",
        category_slug="varios",
        scraped_at=datetime(2026, 9, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    session.add(ProductList(product_id=product.id, list_key="trends", rank=1))
    session.commit()
    session.add(ProductList(product_id=product.id, list_key="trends", rank=2))
    with pytest.raises(Exception):
        session.commit()
```

Add `import pytest` at the top of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_catalog.py -q`
Expected: FAIL — `ImportError: cannot import name 'Product' from 'models'`.

- [ ] **Step 3: Write minimal implementation**

In `models.py`, update the imports and add at the end of the file:

```python
from sqlalchemy import UniqueConstraint
```

```python
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asin: str = Field(unique=True, index=True)
    title: str
    title_normalized: str = Field(index=True)
    image_url: Optional[str] = None
    url: str
    category: str = Field(index=True)
    category_slug: str = Field(index=True)
    price_numeric: Optional[float] = Field(default=None, index=True)
    price_raw: Optional[str] = None
    scraped_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, index=True)


class ProductList(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("product_id", "list_key", name="uq_productlist_product_list"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    list_key: str = Field(index=True)
    rank: int
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_catalog.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add models.py tests/test_catalog.py
git commit -m "feat: add Product and ProductList models"
```

---

## Task 2: Migración Alembic

**Files:**
- Create: `alembic/versions/9f1c7b2a4d3e_add_product_tables.py`

- [ ] **Step 1: Confirm the current head**

Run: `venv/bin/alembic heads`
Expected: `2b292b3ec677 (head)`

- [ ] **Step 2: Write the migration**

Create `alembic/versions/9f1c7b2a4d3e_add_product_tables.py`:

```python
"""add product and productlist tables

Revision ID: 9f1c7b2a4d3e
Revises: 2b292b3ec677
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401  (kept for parity with existing migrations)


revision: str = "9f1c7b2a4d3e"
down_revision: Union[str, Sequence[str], None] = "2b292b3ec677"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asin", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("title_normalized", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("category_slug", sa.String(), nullable=False),
        sa.Column("price_numeric", sa.Float(), nullable=True),
        sa.Column("price_raw", sa.String(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asin"),
    )
    op.create_index("ix_product_asin", "product", ["asin"])
    op.create_index("ix_product_title_normalized", "product", ["title_normalized"])
    op.create_index("ix_product_category", "product", ["category"])
    op.create_index("ix_product_category_slug", "product", ["category_slug"])
    op.create_index("ix_product_price_numeric", "product", ["price_numeric"])
    op.create_index("ix_product_is_active", "product", ["is_active"])

    op.create_table(
        "productlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("list_key", sa.String(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "list_key", name="uq_productlist_product_list"),
    )
    op.create_index("ix_productlist_product_id", "productlist", ["product_id"])
    op.create_index("ix_productlist_list_key", "productlist", ["list_key"])


def downgrade() -> None:
    op.drop_index("ix_productlist_list_key", table_name="productlist")
    op.drop_index("ix_productlist_product_id", table_name="productlist")
    op.drop_table("productlist")
    op.drop_index("ix_product_is_active", table_name="product")
    op.drop_index("ix_product_price_numeric", table_name="product")
    op.drop_index("ix_product_category_slug", table_name="product")
    op.drop_index("ix_product_category", table_name="product")
    op.drop_index("ix_product_title_normalized", table_name="product")
    op.drop_index("ix_product_asin", table_name="product")
    op.drop_table("product")
```

- [ ] **Step 3: Verify upgrade and downgrade against a scratch database**

Run:

```bash
rm -f _migration_check.db
DATABASE_URL="sqlite:///./_migration_check.db" venv/bin/alembic upgrade head
DATABASE_URL="sqlite:///./_migration_check.db" venv/bin/alembic downgrade -1
rm -f _migration_check.db
```

Expected: `Running upgrade ... -> 9f1c7b2a4d3e` and then a clean `Running downgrade 9f1c7b2a4d3e -> 2b292b3ec677`, no errors.

- [ ] **Step 4: Confirm no model drift remains**

Run: `venv/bin/alembic check 2>&1 | tail -5`
Expected: `No new upgrade operations detected.` (if a database is already at head). If `alembic check` errors because no DB exists, skip it — the upgrade/downgrade round-trip already proves the migration.

- [ ] **Step 5: Commit**

```bash
git add alembic/versions/9f1c7b2a4d3e_add_product_tables.py
git commit -m "feat: add alembic migration for product tables"
```

---

## Task 3: Helpers de `catalog.py` (`slugify`, `normalize_text`, `extract_asin`, `_parse_price`)

**Files:**
- Create: `catalog.py`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_catalog.py`:

```python
from catalog import _parse_price, extract_asin, normalize_text, slugify


def test_normalize_text_lowercases_and_strips_accents():
    assert normalize_text("Café") == "cafe"
    assert normalize_text("  Alimentación y Bebidas ") == "alimentacion y bebidas"
    assert normalize_text(None) == ""


def test_slugify_matches_existing_behavior():
    assert slugify("Hogar y cocina") == "hogar-y-cocina"
    assert slugify("Alimentación y bebidas") == "alimentacion-y-bebidas"


def test_extract_asin_from_dp_url():
    assert extract_asin("https://www.amazon.es/Lavazza-1kg/dp/B0049U0DMC/ref=zg_bs?psc=1") == "B0049U0DMC"


def test_extract_asin_from_gp_product_url():
    assert extract_asin("https://www.amazon.es/gp/product/B085LCQNZV?ref=x") == "B085LCQNZV"


def test_extract_asin_fallback_is_stable_and_distinct():
    a = extract_asin("https://www.amazon.es/algo-sin-asin/ref=x")
    b = extract_asin("https://www.amazon.es/algo-sin-asin/ref=x")
    c = extract_asin("https://www.amazon.es/otra-cosa/ref=x")
    assert a == b
    assert a.startswith("h")
    assert a != c


def test_parse_price_european_comma():
    assert _parse_price("19,99 €") == 19.99


def test_parse_price_eur_prefix():
    assert _parse_price("EUR 20.50") == 20.5


def test_parse_price_european_thousands():
    assert _parse_price("1.234,56") == 1234.56


def test_parse_price_non_numeric_returns_zero():
    assert _parse_price("N/A") == 0.0
    assert _parse_price(None) == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_catalog.py -q -k "normalize or slugify or asin or parse_price"`
Expected: FAIL — `ModuleNotFoundError: No module named 'catalog'`.

- [ ] **Step 3: Write minimal implementation**

Create `catalog.py`:

```python
"""Queryable product catalog: normalization, parsing and DB-backed search."""

import hashlib
import re
import unicodedata
from urllib.parse import urlparse


def slugify(value):
    """Normalize text for URLs (e.g. "Hogar y cocina" -> "hogar-y-cocina").

    Moved verbatim from services.py.
    """
    value = str(value)
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-")


def normalize_text(value):
    """Lowercase and strip accents/diacritics for accent-insensitive search."""
    value = str(value or "")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", value.lower()).strip()


ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")


def extract_asin(url):
    """Return the Amazon ASIN, or a stable hash of the URL path when absent."""
    match = ASIN_RE.search(url or "")
    if match:
        return match.group(1)
    path = urlparse(url or "").path
    return "h" + hashlib.sha1(path.encode("utf-8")).hexdigest()[:15]


def _parse_price(price_str):
    """Parse prices like "19,99 €" or "EUR 20.50" to float.

    Moved verbatim from services.py; returns 0.0 when it cannot parse.
    """
    if not price_str:
        return 0.0

    clean = price_str.lower().replace("€", "").replace("eur", "").strip()

    if "," in clean and "." in clean:
        clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        clean = clean.replace(",", ".")

    try:
        return float(clean)
    except ValueError:
        return 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_catalog.py -q -k "normalize or slugify or asin or parse_price"`
Expected: PASS (9 passed).

- [ ] **Step 5: Commit**

```bash
git add catalog.py tests/test_catalog.py
git commit -m "feat: add catalog normalization and parsing helpers"
```

---

## Task 4: `search_products` — filtros, orden y paginación

**Files:**
- Modify: `catalog.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Add the seed fixture**

Append to `tests/conftest.py`:

```python
@pytest.fixture(name="catalog_seed")
def catalog_seed_fixture(session: Session):
    """Insert a small, known catalog: 3 products across 2 categories and 2 lists."""
    from datetime import datetime
    from models import Product, ProductList

    def make(asin, title, category, slug, price, image, url, when):
        return Product(
            asin=asin,
            title=title,
            title_normalized=__import__("catalog").normalize_text(title),
            image_url=image,
            url=url,
            category=category,
            category_slug=slug,
            price_numeric=price,
            price_raw=f"{price} €" if price is not None else "N/A",
            scraped_at=when,
        )

    products = [
        make("A1", "Café molido", "Alimentación y bebidas", "alimentacion-y-bebidas", 10.0,
             "img-a1.jpg", "https://www.amazon.es/dp/A1", datetime(2026, 1, 1)),
        make("A2", "Cafetera express", "Alimentación y bebidas", "alimentacion-y-bebidas", 100.0,
             "img-a2.jpg", "https://www.amazon.es/dp/A2", datetime(2026, 3, 1)),
        make("B1", "Auriculares bluetooth", "Electrónica", "electronica", None,
             "img-b1.jpg", "https://www.amazon.es/dp/B1", datetime(2026, 2, 1)),
    ]
    session.add_all(products)
    session.commit()
    for p in products:
        session.refresh(p)

    session.add_all([
        ProductList(product_id=products[0].id, list_key="bestsellers", rank=1),
        ProductList(product_id=products[1].id, list_key="bestsellers", rank=2),
        ProductList(product_id=products[1].id, list_key="trends", rank=1),
        ProductList(product_id=products[2].id, list_key="trends", rank=2),
    ])
    session.commit()
    return products
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_catalog.py`:

```python
from catalog import CatalogResult, CatalogQuery, search_products


def test_search_by_text_is_accent_and_case_insensitive(session, catalog_seed):
    result = search_products(session, CatalogQuery(q="CAFE"))
    assert result.total == 2


def test_search_ignores_terms_shorter_than_two_chars(session, catalog_seed):
    result = search_products(session, CatalogQuery(q="a"))
    assert result.total == 3


def test_filter_by_category_slug(session, catalog_seed):
    result = search_products(session, CatalogQuery(category_slug="electronica"))
    assert result.total == 1
    assert result.items[0].asin == "B1"


def test_filter_by_source_uses_product_list(session, catalog_seed):
    result = search_products(session, CatalogQuery(source="trends"))
    assert result.total == 2
    assert {p.asin for p in result.items} == {"A2", "B1"}


def test_price_range_excludes_null_prices(session, catalog_seed):
    result = search_products(session, CatalogQuery(min_price=1.0, max_price=200.0))
    assert result.total == 2
    assert all(p.price_numeric is not None for p in result.items)


def test_min_price_greater_than_max_is_swapped(session, catalog_seed):
    result = search_products(session, CatalogQuery(min_price=200.0, max_price=1.0))
    assert result.total == 2


def test_filters_combine(session, catalog_seed):
    result = search_products(session, CatalogQuery(source="bestsellers", category_slug="alimentacion-y-bebidas"))
    assert result.total == 2
    result = search_products(session, CatalogQuery(source="trends", category_slug="alimentacion-y-bebidas"))
    assert result.total == 1
    assert result.items[0].asin == "A2"


def test_sort_price_asc_puts_nulls_last(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="price_asc"))
    assert [p.asin for p in result.items] == ["A1", "A2", "B1"]


def test_sort_price_desc_puts_nulls_last(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="price_desc"))
    assert [p.asin for p in result.items] == ["A2", "A1", "B1"]


def test_sort_newest_orders_by_scraped_at_desc(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="newest"))
    assert [p.asin for p in result.items] == ["A2", "B1", "A1"]


def test_sort_random_returns_all_items(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="random"))
    assert result.total == 3
    assert len(result.items) == 3


def test_relevance_with_query_prioritizes_prefix_matches(session, catalog_seed):
    result = search_products(session, CatalogQuery(q="cafe"))
    assert result.items[0].asin == "A1"


def test_relevance_without_query_uses_rank(session, catalog_seed):
    result = search_products(session, CatalogQuery(source="bestsellers"))
    assert [p.asin for p in result.items] == ["A1", "A2"]


def test_pagination_reports_total_and_total_pages(session, catalog_seed):
    result = search_products(session, CatalogQuery(per_page=2, page=1))
    assert isinstance(result, CatalogResult)
    assert result.total == 3
    assert result.total_pages == 2
    assert len(result.items) == 2

    page2 = search_products(session, CatalogQuery(per_page=2, page=2))
    assert len(page2.items) == 1


def test_per_page_is_capped_at_60(session, catalog_seed):
    result = search_products(session, CatalogQuery(per_page=500))
    assert result.per_page == 60


def test_page_out_of_range_clamps_to_last(session, catalog_seed):
    result = search_products(session, CatalogQuery(per_page=2, page=99))
    assert result.page == 2


def test_page_below_one_clamps_to_first(session, catalog_seed):
    result = search_products(session, CatalogQuery(page=0))
    assert result.page == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_catalog.py -q -k "search or filter or price or sort or pagination or page or per_page or relevance"`
Expected: FAIL — `ImportError: cannot import name 'CatalogQuery' from 'catalog'`.

- [ ] **Step 4: Write minimal implementation**

Append to `catalog.py` (update the imports at the top of the module first):

```python
# --- top of catalog.py: add these imports and constants ---
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import case, func
from sqlmodel import Session, select

from models import Product, ProductList

DEFAULT_PER_PAGE = 24
MAX_PER_PAGE = 60
VALID_SORTS = {"relevance", "price_asc", "price_desc", "newest", "random"}


# --- append at the end of catalog.py ---
@dataclass
class CatalogQuery:
    q: Optional[str] = None
    category_slug: Optional[str] = None
    source: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort: str = "relevance"
    page: int = 1
    per_page: int = DEFAULT_PER_PAGE


@dataclass
class CatalogResult:
    items: list
    total: int
    page: int
    per_page: int
    total_pages: int


def _rank_subquery(source: Optional[str]):
    """Minimum list rank for a product, restricted to `source` when given."""
    conditions = [ProductList.product_id == Product.id]
    if source:
        conditions.append(ProductList.list_key == source)
    return (
        select(func.coalesce(func.min(ProductList.rank), 10**9))
        .where(*conditions)
        .correlate(Product)
        .scalar_subquery()
    )


def search_products(session: Session, query: CatalogQuery) -> CatalogResult:
    term = normalize_text(query.q) if query.q else ""
    if len(term) < 2:
        term = ""

    min_price, max_price = query.min_price, query.max_price
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    per_page = query.per_page or DEFAULT_PER_PAGE
    per_page = max(1, min(int(per_page), MAX_PER_PAGE))

    filters = [Product.is_active == True]  # noqa: E712
    if term:
        filters.append(Product.title_normalized.like(f"%{term}%"))
    if query.category_slug:
        filters.append(Product.category_slug == query.category_slug)
    if query.source:
        filters.append(
            select(ProductList.id)
            .where(ProductList.product_id == Product.id, ProductList.list_key == query.source)
            .exists()
        )
    if min_price is not None:
        filters.append(Product.price_numeric.is_not(None))
        filters.append(Product.price_numeric >= min_price)
    if max_price is not None:
        filters.append(Product.price_numeric.is_not(None))
        filters.append(Product.price_numeric <= max_price)

    total = session.exec(select(func.count()).select_from(Product).where(*filters)).one()
    total_pages = max(1, math.ceil(total / per_page)) if total else 1

    page = query.page if isinstance(query.page, int) else 1
    page = max(1, min(page, total_pages))

    rank = _rank_subquery(query.source)
    if query.sort == "price_asc":
        order_by = [Product.price_numeric.is_(None).asc(), Product.price_numeric.asc()]
    elif query.sort == "price_desc":
        order_by = [Product.price_numeric.is_(None).asc(), Product.price_numeric.desc()]
    elif query.sort == "newest":
        order_by = [Product.scraped_at.desc()]
    elif query.sort == "random":
        order_by = [func.random()]
    elif term:
        order_by = [case((Product.title_normalized.like(f"{term}%"), 0), else_=1), rank]
    else:
        order_by = [rank]

    offset = (page - 1) * per_page
    items = session.exec(
        select(Product).where(*filters).order_by(*order_by).offset(offset).limit(per_page)
    ).all()

    return CatalogResult(
        items=list(items),
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_catalog.py -q`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add catalog.py tests/conftest.py tests/test_catalog.py
git commit -m "feat: add catalog search engine with filters, sorting and pagination"
```

---

## Task 5: `list_categories`

**Files:**
- Modify: `catalog.py`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_catalog.py`:

```python
from catalog import list_categories


def test_list_categories_returns_name_slug_pairs_sorted(session, catalog_seed):
    cats = list_categories(session)
    assert cats == [
        ("Alimentación y bebidas", "alimentacion-y-bebidas"),
        ("Electrónica", "electronica"),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/bin/pytest tests/test_catalog.py -q -k list_categories`
Expected: FAIL — `ImportError: cannot import name 'list_categories'`.

- [ ] **Step 3: Write minimal implementation**

Append to `catalog.py`:

```python
def list_categories(session: Session):
    """Return sorted (display_name, slug) pairs for active products."""
    rows = session.exec(
        select(Product.category, Product.category_slug)
        .where(Product.is_active == True)  # noqa: E712
        .group_by(Product.category, Product.category_slug)
        .order_by(Product.category.asc())
    ).all()
    return [(name, slug) for name, slug in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/bin/pytest tests/test_catalog.py -q -k list_categories`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add catalog.py tests/test_catalog.py
git commit -m "feat: add catalog list_categories"
```

---

## Task 6: Import JSON → DB idempotente + CLI

**Files:**
- Modify: `catalog.py`
- Create: `import_catalog.py`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_catalog.py` (add `import json` and `import os` at the top of the file):

```python
from catalog import import_from_json


def _write_json(tmp_path, name, items):
    path = tmp_path / name
    path.write_text(json.dumps(items), encoding="utf-8")
    return str(path)


def _raw_item(asin, title, category, price):
    return {
        "title": title,
        "category": category,
        "price": price,
        "image": f"img-{asin}.jpg",
        "url": f"https://www.amazon.es/dp/{asin}/ref=x",
    }


def test_import_creates_products_and_list_ranks(session, tmp_path):
    files = {"bestsellers": _write_json(tmp_path, "b.json", [
        _raw_item("A1", "Café molido", "Alimentación y bebidas", "10,00 €"),
        _raw_item("A2", "Cafetera", "Alimentación y bebidas", "100,50 €"),
    ])}
    stats = import_from_json(session, data_files=files)
    assert stats["created"] == 2

    from models import Product, ProductList
    assert session.exec(select(Product)).all().__len__() == 2

    rows = session.exec(select(ProductList).order_by(ProductList.rank)).all()
    assert [r.rank for r in rows] == [1, 2]

    a1 = session.exec(select(Product).where(Product.asin == "A1")).first()
    assert a1.title_normalized == "cafe molido"
    assert a1.category_slug == "alimentacion-y-bebidas"
    assert a1.price_numeric == 10.0
    assert a1.price_raw == "10,00 €"


def test_import_marks_unparseable_price_as_none(session, tmp_path):
    from models import Product
    files = {"trends": _write_json(tmp_path, "t.json", [
        _raw_item("N1", "Sin precio", "Varios", "N/A"),
    ])}
    import_from_json(session, data_files=files)
    product = session.exec(select(Product).where(Product.asin == "N1")).first()
    assert product.price_numeric is None
    assert product.price_raw == "N/A"


def test_import_is_idempotent(session, tmp_path):
    from models import Product, ProductList
    files = {"bestsellers": _write_json(tmp_path, "b.json", [
        _raw_item("A1", "Café", "Alimentación y bebidas", "10,00 €"),
        _raw_item("A2", "Cafetera", "Alimentación y bebidas", "100,50 €"),
    ])}
    import_from_json(session, data_files=files)
    counts = (
        len(session.exec(select(Product)).all()),
        len(session.exec(select(ProductList)).all()),
    )

    import_from_json(session, data_files=files)
    counts_again = (
        len(session.exec(select(Product)).all()),
        len(session.exec(select(ProductList)).all()),
    )
    assert counts == counts_again == (2, 2)


def test_import_dry_run_does_not_write(session, tmp_path):
    from models import Product
    files = {"bestsellers": _write_json(tmp_path, "b.json", [
        _raw_item("A1", "Café", "Alimentación y bebidas", "10,00 €"),
    ])}
    stats = import_from_json(session, data_files=files, dry_run=True)
    assert stats["created"] == 1
    assert session.exec(select(Product)).all() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_catalog.py -q -k import`
Expected: FAIL — `ImportError: cannot import name 'import_from_json'`.

- [ ] **Step 3: Write minimal implementation**

Add to the imports at the top of `catalog.py`:

```python
import json
import os
from sqlalchemy import delete
```

Append to `catalog.py`:

```python
DATA_FILES = {
    "bestsellers": "amazon_bestsellers_total.json",
    "desired": "amazon_mas_deseados_total.json",
    "trends": "amazon_tendencias_total.json",
}


def import_from_json(session: Session, data_files=None, dry_run: bool = False):
    """Idempotent JSON -> DB import. Upserts by ASIN and rebuilds list ranks."""
    data_files = data_files or DATA_FILES
    stats = {"created": 0, "updated": 0, "lists": 0}

    for list_key, path in data_files.items():
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            items = json.load(handle)

        scraped_at = datetime.utcfromtimestamp(os.path.getmtime(path))
        ranked = []

        for rank, item in enumerate(items, start=1):
            url = item.get("url")
            if not url:
                continue

            asin = extract_asin(url)
            title = item.get("title", "")
            category = item.get("category") or "Varios"
            price_raw = item.get("price")
            parsed = _parse_price(price_raw)
            price_numeric = parsed if parsed > 0 else None

            product = session.exec(select(Product).where(Product.asin == asin)).first()
            if product is None:
                product = Product(
                    asin=asin,
                    title=title,
                    title_normalized=normalize_text(title),
                    image_url=item.get("image"),
                    url=url,
                    category=category,
                    category_slug=slugify(category),
                    price_numeric=price_numeric,
                    price_raw=price_raw,
                    scraped_at=scraped_at,
                )
                session.add(product)
                session.flush()
                stats["created"] += 1
            else:
                product.title = title
                product.title_normalized = normalize_text(title)
                product.image_url = item.get("image")
                product.url = url
                product.category = category
                product.category_slug = slugify(category)
                product.price_numeric = price_numeric
                product.price_raw = price_raw
                product.scraped_at = scraped_at
                product.updated_at = datetime.utcnow()
                product.is_active = True
                session.add(product)
                stats["updated"] += 1

            ranked.append((product.id, rank))

        session.exec(delete(ProductList).where(ProductList.list_key == list_key))
        for product_id, rank in ranked:
            session.add(ProductList(product_id=product_id, list_key=list_key, rank=rank))
            stats["lists"] += 1

    if dry_run:
        session.rollback()
    else:
        session.commit()
    return stats
```

Create `import_catalog.py`:

```python
"""CLI: import the Amazon catalog JSON files into the database.

Run the Alembic migration first; this script does not create tables.

    python import_catalog.py
    python import_catalog.py --dry-run
"""

import argparse

from sqlmodel import Session

from catalog import import_from_json
from database import engine


def main():
    parser = argparse.ArgumentParser(description="Import Amazon catalog JSON into the database")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    with Session(engine) as session:
        stats = import_from_json(session, dry_run=args.dry_run)

    mode = "DRY RUN" if args.dry_run else "IMPORT"
    print(f"[{mode}] created={stats['created']} updated={stats['updated']} lists={stats['lists']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_catalog.py -q`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add catalog.py import_catalog.py tests/test_catalog.py
git commit -m "feat: add idempotent catalog import and CLI"
```

---

## Task 7: `/catalog` route + templates + global search box

**Files:**
- Modify: `main.py`
- Modify: `templates/base.html`
- Create: `templates/catalog.html`
- Create: `templates/partials/catalog_results.html`
- Test: `tests/test_catalog_routes.py` (crear)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_catalog_routes.py`:

```python
def test_catalog_page_returns_200(client, catalog_seed):
    response = client.get("/catalog")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_catalog_with_filters_returns_200(client, catalog_seed):
    response = client.get("/catalog?q=cafe&category=alimentacion-y-bebidas&min=1&max=50&sort=price_asc")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_catalog_is_always_noindex(client, catalog_seed):
    # Design §9: /catalog is never indexable, with or without filters.
    assert "noindex" in client.get("/catalog").text
    assert "noindex" in client.get("/catalog?q=cafe").text
    assert "noindex" in client.get("/catalog?sort=price_asc").text
    assert "noindex" in client.get("/catalog?page=2").text


def test_catalog_returns_real_products_without_javascript(client, catalog_seed):
    response = client.get("/catalog")
    assert 'href="https://www.amazon.es/dp/A1?tag=' in response.text or "tag=" in response.text
    assert "img-a1.jpg" in response.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_catalog_routes.py -q`
Expected: FAIL — 404 on `/catalog` (assert status 200 fails).

- [ ] **Step 3: Implement the route**

In `main.py`, update the catalog-related imports (keep `scrape_metadata, generate_amazon_link, perform_draw, get_blog_posts_list` for now):

```python
from services import (
    scrape_metadata, generate_amazon_link, perform_draw,
    get_random_products, get_all_products,
    get_products_by_category_slug, get_all_categories_info,
    get_blog_posts_list, get_blog_post_detail
)
from catalog import CatalogQuery, search_products, list_categories, VALID_SORTS
from urllib.parse import urlencode
```

Add the shared catalog context helper and the route. Place it right before `# --- Rutas de Catálogo (Ver Más) ---`:

```python
def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value, default=1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _catalog_context(
    session: Session,
    user,
    *,
    base_path: str,
    title: str,
    source: Optional[str] = None,
    q: Optional[str] = None,
    category: Optional[str] = None,
    min_value: Optional[str] = None,
    max_value: Optional[str] = None,
    sort: str = "relevance",
    page: str = "1",
    always_indexable: bool = False,
    force_noindex: bool = False,
):
    requested_page = _to_int(page, 1)
    query = CatalogQuery(
        q=q or None,
        category_slug=category or None,
        source=source,
        min_price=_to_float(min_value),
        max_price=_to_float(max_value),
        sort=sort if sort in VALID_SORTS else "relevance",
        page=requested_page,
    )
    result = search_products(session, query)

    params = {}
    if query.q:
        params["q"] = query.q
    if query.category_slug:
        params["category"] = query.category_slug
    if source:
        params["source"] = source
    if query.min_price is not None:
        params["min"] = query.min_price
    if query.max_price is not None:
        params["max"] = query.max_price
    if query.sort != "relevance":
        params["sort"] = query.sort
    filter_qs = urlencode(params)

    categories = list_categories(session)

    def _catalog_url(**overrides):
        merged = {k: v for k, v in params.items() if k not in overrides}
        for key, value in overrides.items():
            if value is not None:
                merged[key] = value
        query_string = urlencode(merged)
        return f"{base_path}?{query_string}" if query_string else base_path

    has_filters = bool(query.q or query.category_slug or query.source
                       or query.min_price is not None or query.max_price is not None)
    # `/catalog` is always noindex (design §9). Elsewhere, any page carrying q,
    # sort or page params is noindex. Use the *requested* page, not the clamped
    # one (an out-of-range ?page=99 still carries a page param). `/ideas/{slug}`
    # opts out via always_indexable.
    noindex = force_noindex or (
        not always_indexable and (bool(q) or (sort != "relevance") or requested_page > 1)
    )

    return {
        "user": user,
        "result": result,
        "categories": categories,
        "category_all_url": _catalog_url(category=None),
        "category_links": [
            {
                "name": name,
                "slug": slug,
                "url": _catalog_url(category=slug),
                "active": query.category_slug == slug,
            }
            for name, slug in categories
        ],
        "query": query,
        "source": source,
        "base_path": base_path,
        "title": title,
        "filter_qs": filter_qs,
        "has_filters": has_filters,
        "noindex": noindex,
        "amazon_link": generate_amazon_link,
    }


@app.get("/catalog", response_class=HTMLResponse)
async def catalog_page(
    request: Request,
    q: Optional[str] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    min: Optional[str] = None,
    max: Optional[str] = None,
    sort: str = "relevance",
    page: str = "1",
    user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    context = _catalog_context(
        session, user,
        base_path="/catalog", title="Catálogo",
        source=source, q=q, category=category, min_value=min, max_value=max,
        sort=sort, page=page, force_noindex=True,
    )
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/catalog_results.html", context)
    return templates.TemplateResponse(request, "catalog.html", context)
```

Note: `catalog_page` accepts `min`/`max` as parameter names to match the query string (they shadow builtins only inside this function — acceptable and intentional).

- [ ] **Step 4: Add `extra_head` block and global search to `templates/base.html`**

Immediately before `</head>`, add:

```html
    {% block extra_head %}{% endblock %}
```

Inside the navbar, after the `Regálame` logo `<div>` and before `<div class="flex items-center space-x-4">`, add a compact search form (works without JS):

```html
                <form action="/catalog" method="GET" class="hidden md:block flex-1 max-w-xs mx-6">
                    <input type="search" name="q" placeholder="Buscar productos..."
                           class="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-400">
                </form>
```

Also add a link to `/catalog` in the nav links block:

```html
                        <a href="/catalog" class="text-sm text-gray-400 hover:text-white transition-colors">Catálogo</a>
```

- [ ] **Step 5: Create `templates/partials/catalog_results.html`**

```html
<div id="catalog-results">
    <p class="text-sm text-gray-400 mb-4">
        {% if result.total %}
            Mostrando {{ (result.page - 1) * result.per_page + 1 }}–{{ [result.page * result.per_page, result.total] | min }} de {{ result.total }}
        {% else %}
            0 resultados
        {% endif %}
    </p>

    {% if result.items %}
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {% for item in result.items %}
        <div class="product-card glass-panel rounded-2xl overflow-hidden hover:bg-white/10 transition-all hover:-translate-y-1 hover:shadow-2xl hover:shadow-indigo-900/20 group flex flex-col">
            <div class="relative h-48 overflow-hidden bg-white p-4">
                <img src="{{ item.image_url or '' }}" alt="{{ item.title }}" loading="lazy" class="w-full h-full object-contain transition-transform duration-500 group-hover:scale-110">
                <div class="absolute top-2 right-2">
                    <span class="text-xs font-bold text-indigo-900 bg-indigo-100/90 px-2 py-1 rounded-md shadow-sm backdrop-blur-sm">{{ item.category }}</span>
                </div>
                <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3 pt-8">
                    <span class="text-lg font-bold text-white drop-shadow-md">{{ item.price_raw or "Sin precio" }}</span>
                </div>
            </div>
            <div class="p-4 flex flex-col flex-grow">
                <h3 class="font-bold text-gray-100 mb-2 leading-tight line-clamp-2 min-h-[2.5rem]" title="{{ item.title }}">{{ item.title }}</h3>
                <div class="mt-auto pt-4 flex gap-3">
                    <a href="{{ amazon_link(item.url) }}" target="_blank"
                       class="flex-1 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-500 border border-yellow-500/30 py-2 rounded-xl text-center text-sm font-bold transition-all flex items-center justify-center gap-2">
                        <i class="ph-bold ph-amazon-logo text-lg"></i>
                        <span class="hidden sm:inline">Ver</span>
                    </a>
                    {% if user %}
                    <form hx-post="/wishes" hx-swap="none" class="flex-1">
                        <input type="hidden" name="content" value="{{ item.url }}">
                        <input type="hidden" name="manual_title" value="{{ item.title }}">
                        <input type="hidden" name="manual_image" value="{{ item.image_url or '' }}">
                        <button type="submit" onclick="showToast(this)"
                                class="w-full bg-indigo-500 hover:bg-indigo-400 text-white shadow-lg shadow-indigo-900/30 py-2 rounded-xl text-center text-sm font-bold transition-all flex items-center justify-center gap-2 transform active:scale-95">
                            <i class="ph-bold ph-plus-circle text-lg"></i>
                            <span class="hidden sm:inline">Añadir</span>
                        </button>
                    </form>
                    {% else %}
                    <a href="/" class="flex-1 bg-white/10 hover:bg-white/20 text-gray-300 py-2 rounded-xl text-center text-sm font-bold transition-all flex items-center justify-center">
                        <i class="ph-bold ph-sign-in"></i>
                    </a>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div id="no-results" class="text-center py-20">
        <div class="bg-white/5 rounded-full w-20 h-20 flex items-center justify-center mx-auto mb-4">
            <i class="ph-duotone ph-magnifying-glass text-4xl text-gray-500"></i>
        </div>
        <h3 class="text-xl font-bold text-gray-400">
            {% if has_filters %}No hay resultados para tu búsqueda{% else %}No hay productos disponibles{% endif %}
        </h3>
    </div>
    {% endif %}

    {% if result.total_pages > 1 %}
    <nav class="flex flex-wrap justify-center gap-2 mt-10">
        {% if result.page > 1 %}
        <a href="{{ base_path }}?{{ filter_qs }}&page={{ result.page - 1 }}"
           hx-get="{{ base_path }}?{{ filter_qs }}&page={{ result.page - 1 }}"
           hx-target="#catalog-results" hx-push-url="true"
           class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10">Anterior</a>
        {% endif %}
        {% for p in range(1, result.total_pages + 1) %}
        <a href="{{ base_path }}?{{ filter_qs }}&page={{ p }}"
           hx-get="{{ base_path }}?{{ filter_qs }}&page={{ p }}"
           hx-target="#catalog-results" hx-push-url="true"
           class="px-4 py-2 rounded-lg border {% if p == result.page %}bg-indigo-500 border-indigo-400 text-white{% else %}bg-white/5 border-white/10 text-gray-300 hover:bg-white/10{% endif %}">{{ p }}</a>
        {% endfor %}
        {% if result.page < result.total_pages %}
        <a href="{{ base_path }}?{{ filter_qs }}&page={{ result.page + 1 }}"
           hx-get="{{ base_path }}?{{ filter_qs }}&page={{ result.page + 1 }}"
           hx-target="#catalog-results" hx-push-url="true"
           class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10">Siguiente</a>
        {% endif %}
    </nav>
    {% endif %}
</div>
```

- [ ] **Step 6: Create `templates/catalog.html`**

```html
{% extends "base.html" %}

{% block title %}{{ title }} | Regálame{% endblock %}
{% block description %}Explora el catálogo de regalos: busca, filtra por categoría, fuente y precio, y ordena los resultados.{% endblock %}
{% block extra_head %}{% if noindex %}<meta name="robots" content="noindex, follow">{% endif %}{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
    <div class="text-center mb-8 mt-4">
        <h1 class="text-4xl md:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 mb-3">{{ title }}</h1>
    </div>

    <form method="GET" action="{{ base_path }}"
          hx-get="{{ base_path }}" hx-target="#catalog-results" hx-push-url="true"
          class="glass-panel rounded-2xl p-5 mb-8 space-y-4">
        {% if source %}<input type="hidden" name="source" value="{{ source }}">{% endif %}

        <div class="flex flex-col md:flex-row gap-3">
            <input type="search" name="q" value="{{ query.q or '' }}" placeholder="Buscar productos..."
                   class="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-400">
            <select name="sort" class="bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-gray-200">
                <option value="relevance" {% if query.sort == "relevance" %}selected{% endif %}>Relevancia</option>
                <option value="price_asc" {% if query.sort == "price_asc" %}selected{% endif %}>Precio: menor a mayor</option>
                <option value="price_desc" {% if query.sort == "price_desc" %}selected{% endif %}>Precio: mayor a menor</option>
                <option value="newest" {% if query.sort == "newest" %}selected{% endif %}>Más recientes</option>
            </select>
            <input type="number" step="0.01" name="min" value="{{ query.min_price if query.min_price is not none else '' }}" placeholder="Precio mín."
                   class="w-full md:w-32 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-gray-200 placeholder-gray-500">
            <input type="number" step="0.01" name="max" value="{{ query.max_price if query.max_price is not none else '' }}" placeholder="Precio máx."
                   class="w-full md:w-32 bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-gray-200 placeholder-gray-500">
            <button type="submit" class="bg-indigo-500 hover:bg-indigo-400 text-white px-6 py-2.5 rounded-xl font-bold transition-all">Filtrar</button>
        </div>

        {% if not source %}
        <div class="flex flex-wrap gap-2">
            <a href="{{ base_path }}{% if query.q or query.min_price is not none or query.max_price is not none or query.sort != 'relevance' %}?{% endif %}{% if query.q %}q={{ query.q }}&{% endif %}{% if query.min_price is not none %}min={{ query.min_price }}&{% endif %}{% if query.max_price is not none %}max={{ query.max_price }}&{% endif %}{% if query.sort != 'relevance' %}sort={{ query.sort }}{% endif %}"
               hx-get="{{ base_path }}" hx-target="#catalog-results" hx-push-url="true"
               class="px-4 py-2 rounded-full text-sm font-bold {% if not query.category_slug %}bg-white text-indigo-900{% else %}bg-white/10 text-gray-300 hover:bg-white/20{% endif %}">Todas</a>
            {% for name, slug in categories %}
            <a href="{{ base_path }}?category={{ slug }}{% if query.q %}&q={{ query.q }}{% endif %}{% if query.min_price is not none %}&min={{ query.min_price }}{% endif %}{% if query.max_price is not none %}&max={{ query.max_price }}{% endif %}{% if query.sort != 'relevance' %}&sort={{ query.sort }}{% endif %}"
               hx-get="{{ base_path }}?category={{ slug }}{% if query.q %}&q={{ query.q }}{% endif %}{% if query.min_price is not none %}&min={{ query.min_price }}{% endif %}{% if query.max_price is not none %}&max={{ query.max_price }}{% endif %}{% if query.sort != 'relevance' %}&sort={{ query.sort }}{% endif %}"
               hx-target="#catalog-results" hx-push-url="true"
               class="px-4 py-2 rounded-full text-sm font-bold {% if query.category_slug == slug %}bg-white text-indigo-900{% else %}bg-white/10 text-gray-300 hover:bg-white/20{% endif %}">{{ name }}</a>
            {% endfor %}
        </div>
        {% endif %}
    </form>

    {% include "partials/catalog_results.html" %}
</div>
{% endblock %}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_catalog_routes.py -q`
Expected: PASS (7 passed).

- [ ] **Step 8: Commit**

```bash
git add main.py templates/base.html templates/catalog.html templates/partials/catalog_results.html tests/test_catalog_routes.py
git commit -m "feat: add server-rendered catalog page with filters and pagination"
```

---

## Task 8: `get_blog_post_detail` sobre `search_products`

**Files:**
- Modify: `services.py`
- Modify: `main.py`
- Test: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_catalog.py`:

```python
def test_get_blog_post_detail_filters_from_db(session, catalog_seed):
    from services import get_blog_post_detail

    post, products = get_blog_post_detail(session, "regalos-amigo-invisible-10-euros")
    assert post is not None
    assert {p.asin for p in products} == {"A1"}  # only price <= 10 and parseable


def test_get_blog_post_detail_unknown_slug(session):
    from services import get_blog_post_detail

    post, products = get_blog_post_detail(session, "no-existe")
    assert post is None
    assert products == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_catalog.py -q -k blog`
Expected: FAIL — `TypeError: get_blog_post_detail() takes 1 positional argument but 2 were given`.

- [ ] **Step 3: Reimplement `get_blog_post_detail`**

In `services.py`, **delete the local `def slugify(value)`** and add this import near the top instead (the implementations are byte-identical, so the remaining legacy callers inside `services.py` keep working until Task 10 deletes them):

```python
from catalog import CatalogQuery, MAX_PER_PAGE, search_products, slugify
```

Replace the body of `get_blog_post_detail` with:

```python
def get_blog_post_detail(session: Session, slug: str):
    """
    Busca un post por slug y resuelve sus productos desde el catálogo.

    Retorna: (post_metadata, filtered_products)
    """
    post = next((p for p in BLOG_POSTS if p["slug"] == slug), None)
    if not post:
        return None, []

    criteria = post.get("criteria", {})
    category_slug = slugify(criteria["category"]) if "category" in criteria else None

    products = []
    page = 1
    while True:
        result = search_products(session, CatalogQuery(
            category_slug=category_slug,
            max_price=criteria.get("max_price"),
            page=page,
            per_page=MAX_PER_PAGE,
        ))
        products.extend(result.items)
        if page >= result.total_pages or not result.items:
            break
        page += 1

    if not post.get("hero_image") and products:
        post["hero_image"] = products[0].image_url

    return post, products
```

Remove the now-unused `_parse_price` reference inside the old body (it is replaced entirely).

- [ ] **Step 4: Update the blog route in `main.py` to pass the session**

Change the `/blog/{slug}` route:

```python
@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post_detail(
    request: Request,
    slug: str,
    user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    post, products = get_blog_post_detail(session, slug)
    if not post:
        raise HTTPException(status_code=404, detail="Artículo no encontrado")

    return templates.TemplateResponse(request, "blog_post.html", {
        "user": user,
        "post": post,
        "items": products,
        "amazon_link": generate_amazon_link,
        "title": post["title"]
    })
```

- [ ] **Step 5: Update `templates/blog_post.html` for the new field names**

Replace every occurrence of `item.image` with `item.image_url` and `item.price` with `item.price_raw`, and any `href="{{ item.url }}"` with `href="{{ amazon_link(item.url) }}"`. Verify with:

Run: `grep -n "item\." templates/blog_post.html`
Expected: no `item.image` or `item.price` remaining (only `item.image_url`, `item.price_raw`, `item.title`, `item.url` inside `amazon_link`/hidden inputs).

- [ ] **Step 6: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_catalog.py -q -k blog`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services.py main.py templates/blog_post.html tests/test_catalog.py
git commit -m "refactor: resolve blog detail products through the catalog engine"
```

---

## Task 9: Migrar rutas legacy, dashboard, `/ideas/{slug}` y sitemap

**Files:**
- Modify: `main.py`
- Modify: `templates/dashboard.html`
- Rewrite: `templates/category_seo.html`
- Delete: `templates/bestsellers.html`, `templates/trends.html`, `templates/most_desired.html`
- Test: `tests/test_catalog_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_catalog_routes.py`:

```python
def test_legacy_catalog_routes_return_200(client, catalog_seed):
    assert client.get("/bestsellers").status_code == 200
    assert client.get("/trends").status_code == 200
    assert client.get("/most-desired").status_code == 200


def test_bestsellers_only_shows_its_source(client, catalog_seed):
    response = client.get("/bestsellers")
    assert "Café molido" in response.text
    assert "Auriculares bluetooth" not in response.text


def test_ideas_slug_returns_200_and_paginates(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas")
    assert response.status_code == 200
    assert "Café molido" in response.text


def test_ideas_slug_has_canonical_and_prev_next(client, catalog_seed):
    response = client.get("/ideas/alimentacion-y-bebidas?page=1")
    assert 'rel="canonical"' in response.text


def test_ideas_unknown_slug_is_empty_not_redirect(client, catalog_seed):
    response = client.get("/ideas/inexistente")
    assert response.status_code == 200


def test_sitemap_lists_categories(client, catalog_seed):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "/ideas/alimentacion-y-bebidas" in response.text
    assert "/catalog" not in response.text


def test_dashboard_returns_200(auth_client):
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/bin/pytest tests/test_catalog_routes.py -q -k "legacy or bestsellers or ideas or sitemap or dashboard"`
Expected: FAIL (empty DB → `/ideas/...` redirects with 303, sitemap lacks the category, etc.).

- [ ] **Step 3: Migrate the legacy source routes**

In `main.py`, replace the `trends_page`, `most_desired_page` and `bestsellers_page` bodies with calls to `_catalog_context`. Replace the three route functions with:

```python
@app.get("/trends", response_class=HTMLResponse)
async def trends_page(
    request: Request, q: Optional[str] = None, category: Optional[str] = None,
    min: Optional[str] = None, max: Optional[str] = None,
    sort: str = "relevance", page: str = "1",
    user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    context = _catalog_context(session, user, base_path="/trends",
                               title="Tendencias del Momento", source="trends",
                               q=q, category=category, min_value=min, max_value=max, sort=sort, page=page)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/catalog_results.html", context)
    return templates.TemplateResponse(request, "catalog.html", context)


@app.get("/most-desired", response_class=HTMLResponse)
async def most_desired_page(
    request: Request, q: Optional[str] = None, category: Optional[str] = None,
    min: Optional[str] = None, max: Optional[str] = None,
    sort: str = "relevance", page: str = "1",
    user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    context = _catalog_context(session, user, base_path="/most-desired",
                               title="Los Más Deseados", source="desired",
                               q=q, category=category, min_value=min, max_value=max, sort=sort, page=page)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/catalog_results.html", context)
    return templates.TemplateResponse(request, "catalog.html", context)


@app.get("/bestsellers", response_class=HTMLResponse)
async def bestsellers_page(
    request: Request, q: Optional[str] = None, category: Optional[str] = None,
    min: Optional[str] = None, max: Optional[str] = None,
    sort: str = "relevance", page: str = "1",
    user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    context = _catalog_context(session, user, base_path="/bestsellers",
                               title="Top Ventas & Ideas", source="bestsellers",
                               q=q, category=category, min_value=min, max_value=max, sort=sort, page=page)
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "partials/catalog_results.html", context)
    return templates.TemplateResponse(request, "catalog.html", context)
```

- [ ] **Step 4: Migrate the dashboard**

Replace the dashboard body:

```python
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(require_user),
    session: Session = Depends(get_session)
):
    recommendations = search_products(session, CatalogQuery(source="bestsellers", sort="random", per_page=10)).items
    trending_items = search_products(session, CatalogQuery(source="trends", sort="random", per_page=10)).items
    desired_items = search_products(session, CatalogQuery(source="desired", sort="random", per_page=10)).items

    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "recommendations": recommendations,
        "trending_items": trending_items,
        "desired_items": desired_items,
        "amazon_link": generate_amazon_link,
    })
```

In `templates/dashboard.html`, replace `{{ item.image }}` → `{{ item.image_url or '' }}`, `{{ item.price }}` → `{{ item.price_raw or 'N/A' }}`, and `href="{{ item.url }}"` → `href="{{ amazon_link(item.url) }}"`. Keep the hidden `name="content" value="{{ item.url }}"` as-is.

- [ ] **Step 5: Migrate `/ideas/{slug}`**

Replace `category_seo_page`:

```python
@app.get("/ideas/{category_slug}", response_class=HTMLResponse)
async def category_seo_page(
    request: Request,
    category_slug: str,
    page: str = "1",
    user: Optional[User] = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    context = _catalog_context(
        request, session, user,
        base_path=f"/ideas/{category_slug}",
        title=category_slug.replace("-", " ").title(),
        category=category_slug, page=page, always_indexable=True,
    )
    context["category_name"] = next(
        (name for name, slug in context["categories"] if slug == category_slug),
        category_slug.replace("-", " ").title(),
    )
    context["other_categories"] = [c for c in context["categories"] if c[1] != category_slug]
    context["canonical_url"] = f"/ideas/{category_slug}"
    context["prev_page"] = context["result"].page - 1 if context["result"].page > 1 else None
    context["next_page"] = context["result"].page + 1 if context["result"].page < context["result"].total_pages else None
    context["page_title"] = context["category_name"]
    return templates.TemplateResponse(request, "category_seo.html", context)
```

Note: unknown slugs return an empty page with 200 (spec: "Estado vacío, sin redirección").

- [ ] **Step 6: Rewrite `templates/category_seo.html`**

```html
{% extends "base.html" %}

{% block title %}Las Mejores Ideas de Regalo para {{ category_name }} (2026) | Regálame{% endblock %}
{% block description %}Encuentra el regalo perfecto en nuestra selección de {{ category_name }}. Comparativa de precios y tendencias para el Amigo Invisible y cumpleaños.{% endblock %}
{% block extra_head %}
<link rel="canonical" href="{{ canonical_url }}">
{% if prev_page %}<link rel="prev" href="{{ base_path }}?page={{ prev_page }}">{% endif %}
{% if next_page %}<link rel="next" href="{{ base_path }}?page={{ next_page }}">{% endif %}
{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
    <div class="text-center mb-12 mt-4">
        <span class="text-indigo-400 text-sm font-bold tracking-widest uppercase mb-2 block">Guía de Regalos</span>
        <h1 class="text-4xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 mb-6 drop-shadow-sm leading-tight">
            Top Regalos de {{ category_name }}
        </h1>
        <p class="text-gray-300 text-lg max-w-3xl mx-auto">
            Explora nuestra colección curada de los productos más deseados de <strong>{{ category_name }}</strong>.
        </p>
    </div>

    {% include "partials/catalog_results.html" %}

    <div class="border-t border-white/10 pt-12 mt-12">
        <h3 class="text-2xl font-bold text-center mb-8 text-gray-200">Otras categorías populares</h3>
        <div class="flex flex-wrap justify-center gap-3">
            {% for name, slug in other_categories %}
            <a href="/ideas/{{ slug }}"
               class="bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white px-4 py-2 rounded-full text-sm transition-all hover:-translate-y-0.5">{{ name }}</a>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
```

- [ ] **Step 7: Migrate the sitemap and delete obsolete templates**

In `sitemap_xml`, replace:

```python
    categories = get_all_categories_info()
    for _, slug in categories:
```

with:

```python
    categories = list_categories(session)
    for _, slug in categories:
```

Then delete the obsolete templates:

```bash
git rm templates/bestsellers.html templates/trends.html templates/most_desired.html
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `venv/bin/pytest tests/test_catalog_routes.py -q`
Expected: PASS (all).

- [ ] **Step 9: Commit**

```bash
git add main.py templates/dashboard.html templates/category_seo.html tests/test_catalog_routes.py
git commit -m "refactor: serve legacy catalog routes, ideas and dashboard from the catalog engine"
```

---

## Task 10: Limpieza de `services.py` + regresión completa

**Files:**
- Modify: `services.py`
- Test: full suite

- [ ] **Step 1: Confirm nothing still imports the dead functions**

Run: `grep -rn "get_random_products\|get_all_products\|get_all_products_unified\|get_products_by_category_slug\|get_all_categories_info\|_load_json" main.py services.py catalog.py import_catalog.py`
Expected: no matches. If any remain, migrate that caller before deleting.

- [ ] **Step 2: Delete the dead catalog code from `services.py`**

Remove these functions entirely: `_load_json`, `get_random_products`, `get_all_products`, `get_all_products_unified`, `get_products_by_category_slug`, `get_all_categories_info`, `_parse_price`, and the `DATA_FILES` dict. `slugify` already moved to `catalog.py` in Task 8 — confirm it is not defined in `services.py` anymore.

Remove the now-unused imports at the top of `services.py`: `random`, `json`, `unicodedata`, `re` (verify `re` is not used by `scrape_metadata` first with `grep -n "re\." services.py`). Keep `os` (used by `generate_amazon_link` for `AMAZON_TAG`), `requests`, `BeautifulSoup`, `Session`, `select`, `GroupMember`, `GroupExclusion`, `BLOG_POSTS`, and `from catalog import ...`.

- [ ] **Step 3: Verify `services.py` still imports cleanly**

Run: `venv/bin/python -c "import services; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Run the full regression suite**

Run: `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: all green — the original 17 plus the new catalog tests, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add services.py
git commit -m "refactor: remove JSON catalog code from services"
```

---

## Task 11: Verificación end-to-end manual

**Files:** none (verification only)

- [ ] **Step 1: Dry-run the real import**

Run: `venv/bin/python import_catalog.py --dry-run`
Expected: prints `[DRY RUN] created=... updated=... lists=...` with a non-zero `created` close to ~4350 rows across the three files and no traceback.

- [ ] **Step 2: Import for real against a scratch database and verify idempotency**

Run:

```bash
rm -f _catalog_check.db
DATABASE_URL="sqlite:///./_catalog_check.db" venv/bin/alembic upgrade head
DATABASE_URL="sqlite:///./_catalog_check.db" venv/bin/python import_catalog.py
DATABASE_URL="sqlite:///./_catalog_check.db" venv/bin/python import_catalog.py
DATABASE_URL="sqlite:///./_catalog_check.db" venv/bin/python -c "
from sqlmodel import Session, select, func
from database import engine
from models import Product, ProductList
with Session(engine) as s:
    print('products:', s.exec(select(func.count()).select_from(Product)).one())
    print('list rows:', s.exec(select(func.count()).select_from(ProductList)).one())
"
rm -f _catalog_check.db
```

Expected: both import runs succeed; the second run reports `created=0`; `products` and `list rows` counts are identical between runs.

- [ ] **Step 3: Boot the app and check the key URLs by hand**

Run: `venv/bin/uvicorn main:app --port 8099` (in one terminal), then:

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8099/catalog?q=cafe&sort=price_asc"
curl -s "http://127.0.0.1:8099/catalog?page=2" | grep -c 'class="product-card"'
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8099/ideas/electronica"
```

Expected: `200`, a non-zero card count, `200`. Stop the server afterwards.

- [ ] **Step 4: Final full regression**

Run: `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
Expected: all green.

- [ ] **Step 5: Commit (only if any fix was needed in this task)**

If steps 1–3 required fixes, commit them:

```bash
git add -A
git commit -m "fix: address issues found in catalog end-to-end verification"
```

If no fixes were needed, do not create an empty commit — the plan is complete and ready for review.

---

## Self-Review

**Spec coverage:**
- §5 modelo de datos → Task 1 (+ índices en Task 2).
- §6 módulos (`catalog.py`, limpieza de `services.py`, reimplementación de `get_blog_post_detail`) → Tasks 3–6, 8, 10.
- §7 import idempotente + CLI + migración → Tasks 2, 6, 11.
- §8 semántica de búsqueda (q, category, source, precio, sort, paginación, tope 60, clamp) → Tasks 4, 5.
- §9 rutas, URLs y SEO (`/catalog`, legacy, `/ideas/{slug}`, noindex, canonical, prev/next, sitemap, sin JS) → Tasks 7, 9.
- §10 UX (buscador global, filtros, grid, contador, paginador, estado vacío) → Tasks 7, 9.
- §11 errores y casos borde → Tasks 4, 7, 9 (clamp, swap, estado vacío sin redirección, `N/A`).
- §12 testing → tests unitarios, de integración, de idempotencia, de rutas y regresión en Tasks 1–11.
- §13 migración y despliegue → Tasks 2, 11.
- §15 criterios de aceptación → cubiertos por los tests de Tasks 4, 6, 7, 9, 11 (criterio 7 = Task 10 step 4).

**Placeholder scan:** sin `TBD`/`TODO`; cada paso de código incluye el código completo.

**Type consistency:** `CatalogQuery`/`CatalogResult` (Task 4) se usan sin cambios en Tasks 5–9; `search_products(session, query)`, `list_categories(session)`, `get_blog_post_detail(session, slug)`, `import_from_json(session, data_files=None, dry_run=False)`, `MAX_PER_PAGE`, `VALID_SORTS`, `amazon_link` en el contexto de plantillas — todos consistentes entre tareas.

**Huecos resueltos:** G1 (Task 4 `random` + Task 9 dashboard), G2 (Task 8 bucle), G3 (Task 6 mapeo a `None`), G4 (Task 8 match exacto, verificado sin regresión), G5 (Tasks 8, 9 renombres de plantilla).

---

## Execution Handoff

Plan completo. Dos opciones de ejecución:

1. **Subagent-Driven (recomendada)** — despacho un subagente fresco por tarea, reviso entre tareas, iteración rápida.
2. **Inline Execution** — ejecuto las tareas en esta sesión con checkpoints por lotes.

¿Cuál preferís?
