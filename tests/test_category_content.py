"""Unique per-category SEO content on ``/ideas/{slug}`` landings.

Covers:
- categories with a ``CATEGORY_CONTENT`` entry get topic-specific guide text
  (intro + tips) and FAQ that never collide with the generic templates;
- categories without an entry keep the exact generic fallback;
- no content string invents prices, ratings, percentages, discounts or
  superlative claims (strict editorial policy);
- the rendered ``/ideas/{slug}`` landing shows the specific content.
"""

import re
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from seo_content import CATEGORY_CONTENT, category_faq, category_guide

# A category with no dedicated entry: must keep the untouched generic text.
_FALLBACK_NAME = "CD y vinilos"

_GENERIC_TIPS = [
    "Piensa en los gustos y la edad de quien lo recibe, no solo en la categoría.",
    "Fija un presupuesto antes de mirar y compáralo con el precio de cada producto.",
    "Lee la descripción y las condiciones del vendedor para confirmar qué incluye.",
    "Revisa los plazos de envío si necesitas el regalo para una fecha concreta.",
    "Si hay una lista de deseos, es la referencia más fiable para no fallar.",
]


def test_specific_guide_differs_from_generic():
    """An entry category never returns the templated guide text."""
    generic = category_guide(_FALLBACK_NAME)
    assert generic["tips"] == _GENERIC_TIPS
    for slug, entry in CATEGORY_CONTENT.items():
        guide = category_guide(entry["name"])
        assert guide["intro"] != (
            f"Elegir un regalo de {entry['name']} depende sobre todo de la persona y de "
            "la ocasión. Empieza por el destinatario, define un presupuesto y "
            "compara varias opciones de la categoría antes de decidirte."
        ), slug
        assert guide["tips"] != _GENERIC_TIPS, slug


def test_specific_guide_from_slug_or_name():
    """Slug and display-name forms resolve to the same entry."""
    for slug, entry in CATEGORY_CONTENT.items():
        assert category_guide(entry["name"]) == category_guide(slug)
        assert category_faq(entry["name"]) == category_faq(slug)


def test_fallback_generic_intact():
    """A category without an entry keeps the exact pre-existing generic text."""
    guide = category_guide(_FALLBACK_NAME)
    assert guide["title"] == "Cómo elegir un regalo de CD y vinilos"
    assert guide["intro"] == (
        "Elegir un regalo de CD y vinilos depende sobre todo de la persona y de "
        "la ocasión. Empieza por el destinatario, define un presupuesto y "
        "compara varias opciones de la categoría antes de decidirte."
    )
    assert guide["tips"] == _GENERIC_TIPS


def test_fallback_faq_generic_intact():
    faq = category_faq(_FALLBACK_NAME)
    assert [item["q"] for item in faq] == [
        "¿Cómo elegir un regalo de CD y vinilos?",
        "¿Cuánto debería gastar en un regalo de CD y vinilos?",
        "¿Sirve un regalo de CD y vinilos para un amigo invisible?",
    ]


def test_specific_faq_present_and_topic_bound():
    for slug, entry in CATEGORY_CONTENT.items():
        faq = category_faq(entry["name"])
        assert 2 <= len(faq) <= 3, slug
        generic_questions = {
            f"¿Cómo elegir un regalo de {entry['name']}?",
            f"¿Cuánto debería gastar en un regalo de {entry['name']}?",
            f"¿Sirve un regalo de {entry['name']} para un amigo invisible?",
        }
        questions = {item["q"] for item in faq}
        assert not questions & generic_questions, slug
        for item in faq:
            assert item["q"] and item["a"], slug


def test_coverage_and_shape():
    assert len(CATEGORY_CONTENT) >= 10
    for slug, entry in CATEGORY_CONTENT.items():
        assert slug == slug.strip().lower()
        assert entry["intro"].strip()
        assert 4 <= len(entry["tips"]) <= 5, slug
        assert 2 <= len(entry["faq"]) <= 3, slug


_FORBIDDEN_PATTERNS = [
    r"[€$£¥]",                       # currency symbols
    r"(?i)\beuros?\b",               # currency words
    r"(?i)\bmejor(?:es)? del \w+",   # superlative claims
    r"(?i)\bel mejor\b",
    r"(?i)\btop\s*\d+",
    r"(?i)\b(?:barat|chollo|descuento|rebaj|ofert|promoci|gratis)",
    r"\d+\s*(?:estrellas|/5|★)",     # rating figures
    r"%",                            # percentages
    r"\d",                           # no invented figures at all
]


@pytest.mark.parametrize(
    "slug,entry", sorted(CATEGORY_CONTENT.items()),
    ids=[slug for slug, _ in sorted(CATEGORY_CONTENT.items())])
def test_no_invented_claims_in_category_content(slug, entry):
    strings = [entry["intro"], *entry["tips"]]
    for item in entry["faq"]:
        strings.extend([item["q"], item["a"]])
    for text in strings:
        for pattern in _FORBIDDEN_PATTERNS:
            assert re.search(pattern, text) is None, (slug, pattern, text)


def test_rendered_landing_shows_specific_content(client, catalog_seed):
    response = client.get("/ideas/electronica")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.find(string=re.compile("compatib", re.I)) is not None


def test_rendered_landing_keeps_generic_fallback(client, session, catalog_seed):
    from models import Product, ProductList

    product = Product(
        asin="C1", title="Vinilo de colección",
        title_normalized="vinilo de coleccion",
        image_url="img-c1.jpg", url="https://www.amazon.es/dp/C1",
        category="CD y vinilos", category_slug="cd-y-vinilos",
        price_numeric=None, price_raw="N/A",
        scraped_at=datetime(2026, 2, 1), updated_at=datetime(2026, 2, 1),
    )
    session.add(product)
    session.commit()
    session.add(ProductList(product_id=product.id, list_key="trends", rank=9))
    session.commit()

    response = client.get("/ideas/cd-y-vinilos")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")
    assert soup.find(string=re.compile(
        "depende sobre todo de la persona y de la ocasión", re.I)) is not None
