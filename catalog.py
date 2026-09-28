"""Queryable product catalog: normalization, parsing and DB-backed search."""

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import case, func
from sqlmodel import Session, select

from models import Product, ProductList

DEFAULT_PER_PAGE = 24
MAX_PER_PAGE = 60
VALID_SORTS = {"relevance", "price_asc", "price_desc", "newest", "random"}


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


def _like_escape(text):
    """Escape LIKE metacharacters so user input is matched literally."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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
    escaped = _like_escape(term)

    min_price, max_price = query.min_price, query.max_price
    if min_price is not None and max_price is not None and min_price > max_price:
        min_price, max_price = max_price, min_price

    per_page = query.per_page or DEFAULT_PER_PAGE
    per_page = max(1, min(int(per_page), MAX_PER_PAGE))

    filters = [Product.is_active == True]  # noqa: E712
    if term:
        filters.append(Product.title_normalized.like(f"%{escaped}%", escape="\\"))
    if query.category_slug:
        filters.append(Product.category_slug == query.category_slug)
    if query.source:
        filters.append(
            select(ProductList.id)
            .where(ProductList.product_id == Product.id, ProductList.list_key == query.source)
            .exists()
        )
    if min_price is not None or max_price is not None:
        filters.append(Product.price_numeric.is_not(None))
    if min_price is not None:
        filters.append(Product.price_numeric >= min_price)
    if max_price is not None:
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
        order_by = [case((Product.title_normalized.like(f"{escaped}%", escape="\\"), 0), else_=1), rank]
    else:
        order_by = [rank]

    order_by = order_by + [Product.id.asc()]

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


def list_categories(session: Session) -> list[tuple[str, str]]:
    """Return (display_name, slug) pairs for active products, accent-insensitively sorted."""
    rows = session.exec(
        select(Product.category, Product.category_slug)
        .where(Product.is_active == True)  # noqa: E712
        .group_by(Product.category, Product.category_slug)
    ).all()
    pairs = ((name, slug) for name, slug in rows)
    return sorted(pairs, key=lambda pair: (normalize_text(pair[0]), pair[1]))
