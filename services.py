import random
import os
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from sqlalchemy import func
from models import GroupMember, GroupExclusion, ConversionEvent
from blog_config import BLOG_POSTS
from catalog import CatalogQuery, MAX_PER_PAGE, search_products, slugify

logger = logging.getLogger(__name__)

# --- PRIVACY-SCOPED CONVERSION EVENTS ---
#
# The allowlist is the whole vocabulary we are allowed to persist. A conversion
# row carries only the event name and a naive UTC timestamp; adding an event is
# a deliberate, reviewed change to this frozenset. Never store identifying data.
CONVERSION_EVENTS = frozenset({
    "signup", "login", "group_created", "invitation_accepted",
    "invitation_sent", "wish_added", "wish_reserved", "draw_performed",
})


def record_conversion(session: Session, name: str) -> None:
    """Append one conversion event for an allowlisted name.

    Unknown names are ignored (nothing is stored). Recording is a resilient
    side-channel: it must never break or fail the user action that triggered it.
    """
    if name not in CONVERSION_EVENTS:
        return

    try:
        session.add(ConversionEvent(name=name))
        session.commit()
    except Exception:
        # Analytics must never break the user action it observes. Roll back a
        # poisoned transaction so the caller's session stays usable, log, and
        # return quietly.
        try:
            session.rollback()
        except Exception:
            pass
        logger.warning("Failed to record conversion event %r", name, exc_info=True)


def conversion_counts(session: Session, since=None) -> dict:
    """Read-only aggregates over conversion events.

    Returns ``{"totals": {name: count}, "per_day": {"YYYY-MM-DD": count}}``
    restricted to events at or after ``since`` (a naive UTC datetime) when given.
    Only aggregates leave this function; no row-level data is exposed.
    """
    totals_stmt = select(ConversionEvent.name, func.count()).group_by(ConversionEvent.name)
    per_day_stmt = (
        select(func.date(ConversionEvent.occurred_at), func.count())
        .group_by(func.date(ConversionEvent.occurred_at))
    )
    if since is not None:
        totals_stmt = totals_stmt.where(ConversionEvent.occurred_at >= since)
        per_day_stmt = per_day_stmt.where(ConversionEvent.occurred_at >= since)

    totals = {name: count for name, count in session.exec(totals_stmt).all()}
    per_day = {str(day): count for day, count in session.exec(per_day_stmt).all()}
    return {"totals": totals, "per_day": per_day}


# The placeholder affiliate tag keeps working without configuration but is not
# a real monetization value. Warn once per process so the misconfiguration is
# visible without spamming every link generation.
_amazon_tag_warned = False

# --- SCRAPING & UTILS (EXISTENTE) ---

def scrape_metadata(url: str):
    """
    Extrae título e imagen (OG tags o selectores específicos) de una URL dada.
    Optimizado para Amazon.
    """
    if not url:
        return {"title": "Sin título", "image_url": None}
        
    try:
        # Headers más robustos para simular navegador real
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Intentar sacar imagen
        image_url = None
        
        # Estrategia A: Meta Tags estándar
        og_image = soup.find("meta", property="og:image")
        if og_image:
            image_url = og_image.get("content")
            
        # Estrategia B: Selectores específicos de Amazon (si falla A)
        if not image_url and "amazon" in url:
            # ID común para imagen principal en desktop
            img_tag = soup.select_one("#landingImage, #imgBlkFront, #main-image")
            if img_tag:
                # A veces la url está en 'src' o 'data-old-hires'
                image_url = img_tag.get("data-old-hires") or img_tag.get("src")
        
        # 2. Intentar sacar título
        title = None
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content")
        
        if not title:
            # Fallback al tag <title>
            title = soup.title.string if soup.title else url
            
        # Limpieza de título Amazon (quitar "Amazon.es: ...")
        if title:
            title = title.replace("Amazon.es: ", "").replace(" : Amazon.es", "").strip()
            # Cortar si es demasiado largo
            if len(title) > 80:
                title = title[:77] + "..."

        return {
            "title": title.strip(),
            "image_url": image_url
        }
    except Exception as e:
        print(f"Error scraping metadata: {e}")
        return {
            "title": url,
            "image_url": None
        }

def generate_amazon_link(query_or_url: str):
    """
    Genera un enlace con tag de afiliado.
    - Si es una query de texto: crea link de búsqueda.
    - Si es una URL de Amazon: inyecta el tag de afiliado.
    """
    global _amazon_tag_warned
    tag = os.getenv("AMAZON_TAG")
    if not tag:
        if not _amazon_tag_warned:
            logger.warning(
                "AMAZON_TAG is not set; affiliate links fall back to the "
                "'tu_tag_defecto-21' placeholder tag."
            )
            _amazon_tag_warned = True
        tag = "tu_tag_defecto-21"
    
    # Caso 1: Es una URL de Amazon
    if "amazon" in query_or_url and ("http://" in query_or_url or "https://" in query_or_url):
        
        parsed = urlparse(query_or_url)
        query_params = parse_qs(parsed.query)
        
        # Sobrescribir o añadir el tag
        query_params["tag"] = [tag]
        
        # Reconstruir URL
        new_query = urlencode(query_params, doseq=True)
        new_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        return new_url

    # Caso 2: Es texto plano (búsqueda)
    base_url = "https://www.amazon.es/s?k="
    formatted_query = query_or_url.strip().replace(" ", "+")
    return f"{base_url}{formatted_query}&tag={tag}"

def perform_draw(group_id: int, session: Session):
    """
    Realiza el sorteo circular respetando las exclusiones (GroupExclusion).
    Usa un algoritmo de reintento aleatorio (Monte Carlo) para encontrar una solución válida.
    """
    # 1. Obtener miembros y exclusiones
    members_links = session.exec(select(GroupMember).where(GroupMember.group_id == group_id)).all()
    exclusions = session.exec(select(GroupExclusion).where(GroupExclusion.group_id == group_id)).all()
    
    if len(members_links) < 2:
        raise ValueError("Se necesitan al menos 2 miembros para realizar el sorteo.")

    user_ids = [m.user_id for m in members_links]
    
    # Crear un set de pares prohibidos para búsqueda rápida: (giver_id, forbidden_id)
    forbidden_pairs = set((e.giver_id, e.forbidden_giftee_id) for e in exclusions)
    
    # 2. Intentar encontrar una combinación válida (máx 100 intentos)
    # Para grupos pequeños (<20) esto suele encontrar solución en el primer o segundo intento.
    attempts = 0
    max_attempts = 100
    valid_assignments = None
    
    while attempts < max_attempts:
        receivers = user_ids[:]
        random.shuffle(receivers)
        
        # Verificar esta permutación
        current_assignments = {}
        is_valid = True
        
        for i, giver_id in enumerate(user_ids):
            receiver_id = receivers[i]
            
            # Regla 1: No regalarse a sí mismo
            if giver_id == receiver_id:
                is_valid = False
                break
                
            # Regla 2: Respetar exclusiones
            if (giver_id, receiver_id) in forbidden_pairs:
                is_valid = False
                break
            
            current_assignments[giver_id] = receiver_id
        
        if is_valid:
            valid_assignments = current_assignments
            break
            
        attempts += 1
        
    if not valid_assignments:
        raise ValueError("No se encontró una combinación válida con las restricciones actuales. Intenta eliminar algunos vetos.")

    # 3. Guardar en base de datos
    for member_link in members_links:
        if member_link.user_id in valid_assignments:
            member_link.giftee_id = valid_assignments[member_link.user_id]
            session.add(member_link)
    
    session.commit()
    return True

# --- BLOG & CURATED LISTS LOGIC ---

def get_blog_posts_list():
    """
    Retorna la lista de posts configurados (metadata).
    """
    return BLOG_POSTS

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

    # Pagination already runs over the filtered visible set: search_products
    # applies the editorial predicate before computing totals, so the loop above
    # never collects hidden products. A hero image is only ever derived from a
    # non-empty visible list; when filtering empties the list the post keeps its
    # configured hero (or none) and the template renders the curated empty state.
    if products and not post.get("hero_image"):
        post = {**post, "hero_image": products[0].image_url}

    return post, products


def get_blog_posts_with_covers(session: Session):
    """
    Retorna las entradas de BLOG_POSTS enriquecidas con una imagen de portada,
    resuelta desde el primer producto visible que cumple los criterios del post.
    No muta BLOG_POSTS: devuelve copias.

    Covers are de-duplicated across cards: when a post's first visible product
    reuses an image already shown by an earlier post (overlapping criteria), the
    card advances to the next visible product with an unused image. When every
    candidate image is already used, it falls back to the first product's image.
    """
    posts = []
    used_images: set[str] = set()
    for post in BLOG_POSTS:
        if post.get("hero_image"):
            posts.append({**post})
            used_images.add(post["hero_image"])
            continue
        criteria = post.get("criteria", {})
        category_slug = slugify(criteria["category"]) if "category" in criteria else None
        result = search_products(session, CatalogQuery(
            category_slug=category_slug,
            max_price=criteria.get("max_price"),
            page=1,
            per_page=MAX_PER_PAGE,
        ))
        cover = next(
            (item.image_url for item in result.items
             if item.image_url and item.image_url not in used_images),
            None,
        )
        if cover is None and result.items:
            cover = result.items[0].image_url
        if cover:
            used_images.add(cover)
        posts.append({**post, "hero_image": cover})
    return posts