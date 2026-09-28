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
