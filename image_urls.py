"""Amazon product-image WebP upgrade helper.

Amazon's image CDN serves a WebP variant of the *same* resolution when the
``_AC_`` transform segment in the path gains the ``_FMwebp_`` marker. Measured
against ``images-eu.ssl-images-amazon.com``: a 33,484-byte JPEG became a
16,248-byte WebP (~37-44% smaller) at identical dimensions.

Because the browser can fetch the smaller asset straight from Amazon's own edge
cache, there is deliberately no proxy, resizer, or other runtime dependency: we
only rewrite the URL at the ``<img src>`` render site and never touch persisted
values or metadata (``manual_image``, JSON-LD, Open Graph, etc.).
"""

from urllib.parse import urlsplit, urlunsplit

_AMAZON_IMAGE_HOSTS = frozenset(
    {
        "images-eu.ssl-images-amazon.com",
        "images-na.ssl-images-amazon.com",
        "m.media-amazon.com",
    }
)

# Sentinel inserted into the ``_AC_`` transform segment to request WebP.
_WEBP_MARKER = "_FMwebp_"


def amazon_webp_url(url):
    """Return `url` as an Amazon WebP variant when it is a rewritable Amazon
    image URL; otherwise return it unchanged (no-op)."""
    if not url or not isinstance(url, str):
        return url
    # Idempotent: never double-append the marker.
    if _WEBP_MARKER in url:
        return url

    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return url

    if parts.scheme not in ("http", "https"):
        return url
    if (host or "").lower() not in _AMAZON_IMAGE_HOSTS:
        return url

    path = parts.path
    if "._AC_" not in path or not path.endswith(".jpg"):
        return url

    new_path = path[: -len(".jpg")] + _WEBP_MARKER + ".jpg"
    return urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))
