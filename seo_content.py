"""Category-aware pSEO content for the ``/ideas/{slug}`` landings, plus the
FAQ content for the ``/amigo-invisible`` organizer landing.

Everything here is generic and factual: guidance derived from the category
name plus neutral answers that avoid invented numbers, ratings or superlative
claims. The blog cross-links reuse the curated posts already declared in
``blog_config`` instead of duplicating titles.
"""

from blog_config import BLOG_POSTS

# Price-focused posts used when a category has no dedicated curated post.
_PRICE_GUIDE_SLUGS = (
    "regalos-amigo-invisible-10-euros",
    "regalos-baratos-menos-20-euros",
)


def category_guide(name):
    """Return a short "how to choose" block for ``name``.

    The result is ``{"title", "intro", "tips"}`` where ``tips`` is a list of
    generic, factual considerations. No prices, ratings or "best" claims.
    """
    return {
        "title": f"Cómo elegir un regalo de {name}",
        "intro": (
            f"Elegir un regalo de {name} depende sobre todo de la persona y de "
            "la ocasión. Empieza por el destinatario, define un presupuesto y "
            "compara varias opciones de la categoría antes de decidirte."
        ),
        "tips": [
            "Piensa en los gustos y la edad de quien lo recibe, no solo en la categoría.",
            "Fija un presupuesto antes de mirar y compáralo con el precio de cada producto.",
            "Lee la descripción y las condiciones del vendedor para confirmar qué incluye.",
            "Revisa los plazos de envío si necesitas el regalo para una fecha concreta.",
            "Si hay una lista de deseos, es la referencia más fiable para no fallar.",
        ],
    }


def category_faq(name):
    """Return 2-3 neutral ``{"q", "a"}`` pairs for the ``name`` category."""
    return [
        {
            "q": f"¿Cómo elegir un regalo de {name}?",
            "a": (
                "Fíjate primero en la persona y la ocasión, y después compara "
                "varias opciones dentro de la categoría. Si existe una lista de "
                "deseos, revísala antes de comprar."
            ),
        },
        {
            "q": f"¿Cuánto debería gastar en un regalo de {name}?",
            "a": (
                "No hay una cifra única: depende de la ocasión y de la relación "
                "con quien lo recibe. Fija un presupuesto antes de mirar y "
                "ten en cuenta que los precios pueden cambiar con el tiempo."
            ),
        },
        {
            "q": f"¿Sirve un regalo de {name} para un amigo invisible?",
            "a": (
                "Sí, siempre que respetes el límite de precio acordado en el "
                "grupo. Revisa el importe pactado antes de elegir la opción."
            ),
        },
    ]


def amigo_invisible_faq():
    """Return 6 neutral ``{"q", "a"}`` pairs for the ``/amigo-invisible`` landing.

    Every answer describes only verified app behavior: admin-run draws with at
    least two participants, per-participant visibility of assignments, required
    accounts, public wishlist profiles, admin-managed exclusions and the
    orientative budget. No invented features, numbers or guarantees.
    """
    return [
        {
            "q": "¿Qué es el amigo invisible online?",
            "a": (
                "Es un intercambio de regalos en el que un sorteo asigna a cada "
                "participante a quién debe regalar. En Regálame creas un grupo, "
                "invitas a los participantes y el sorteo se realiza dentro de la "
                "aplicación."
            ),
        },
        {
            "q": "¿Cómo se hace el sorteo para que nadie sepa quién regala a quién?",
            "a": (
                "El administrador inicia el sorteo con al menos dos participantes "
                "y la asignación es aleatoria: nadie se asigna a sí mismo. Cada "
                "persona consulta su asignación iniciando sesión en la "
                "aplicación; los resultados no se envían por WhatsApp ni por "
                "correo electrónico."
            ),
        },
        {
            "q": "¿Hace falta que todos los participantes tengan cuenta?",
            "a": (
                "Sí. Cada participante necesita una cuenta y debe iniciar sesión "
                "para unirse al grupo con el enlace de invitación y consultar su "
                "asignación y las listas de deseos."
            ),
        },
        {
            "q": "¿Cómo se comparte la lista de deseos?",
            "a": (
                "Cada participante añade sus deseos desde su cuenta, con enlaces "
                "o texto. Las listas públicas se pueden ver sin cuenta a través "
                "del enlace del perfil, y también se pueden compartir por correo "
                "electrónico. Para reservar un regalo hay que iniciar sesión."
            ),
        },
        {
            "q": "¿Cómo se gestionan los vetos o exclusiones?",
            "a": (
                "Antes del sorteo, el administrador puede indicar pares de "
                "personas que no pueden regalarse entre sí. El sorteo respeta "
                "esas exclusiones, aunque demasiadas restricciones pueden impedir "
                "encontrar una combinación válida."
            ),
        },
        {
            "q": "¿Se puede fijar un presupuesto?",
            "a": (
                "Sí. Al crear el grupo, el administrador indica el nombre, la "
                "fecha y un presupuesto. Es orientativo: la aplicación no controla "
                "cuánto gasta cada persona."
            ),
        },
    ]


def related_posts(name):
    """Return curated blog posts matching ``name``, else price-based fallbacks.

    Matching is by ``criteria.category``. Each entry is a ``{"title", "slug"}``
    dict so the template can link to ``/blog/{slug}`` without extra lookups.
    """
    matches = [
        post for post in BLOG_POSTS
        if post.get("criteria", {}).get("category") == name
    ]
    if not matches:
        matches = [post for post in BLOG_POSTS if post["slug"] in _PRICE_GUIDE_SLUGS]
    return [{"title": post["title"], "slug": post["slug"]} for post in matches]
