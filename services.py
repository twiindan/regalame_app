import random
import os
import json
import unicodedata
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from models import GroupMember, GroupExclusion

# --- CONFIGURACIÓN DE ARCHIVOS ---
DATA_FILES = {
    "bestsellers": "amazon_bestsellers_total.json",
    "desired": "amazon_mas_deseados_total.json",
    "trends": "amazon_tendencias_total.json"
}

def slugify(value):
    """
    Normaliza texto para URL (ej: "Hogar y cocina" -> "hogar-y-cocina")
    """
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-')

def _load_json(filename):
    """
    Función genérica para leer JSON de forma segura e inyectar el tag de afiliado.
    """
    if not os.path.exists(filename):
        return []

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            items = json.load(f)
            
        tag = os.getenv("AMAZON_TAG", "tu_tag_defecto-21")
        processed = []
        
        for item in items:
            new_item = item.copy()
            # Asegurar que existe la categoría, si no, "Varios"
            if "category" not in new_item or not new_item["category"]:
                new_item["category"] = "Varios"

            # Inyección de tag
            if "url" in new_item:
                separator = "&" if "?" in new_item["url"] else "?"
                if "tag=" not in new_item["url"]:
                    new_item["url"] += f"{separator}tag={tag}"
            processed.append(new_item)
            
        return processed
    except Exception as e:
        print(f"Error loading {filename}: {e}")
        return []

def get_random_products(file_key: str, limit: int = 10):
    """
    Obtiene 'limit' productos aleatorios de un archivo específico.
    Útil para el Dashboard.
    """
    filename = DATA_FILES.get(file_key)
    if not filename:
        return []
    
    all_items = _load_json(filename)
    if not all_items:
        return []
        
    return random.sample(all_items, min(limit, len(all_items)))

def get_all_products(file_key: str):
    """
    Obtiene TODOS los productos y un conjunto de CATEGORÍAS únicas.
    Útil para las páginas 'Ver Más' con filtros.
    Retorna: (items, categories_set)
    """
    filename = DATA_FILES.get(file_key)
    if not filename:
        return [], []
    
    items = _load_json(filename)
    categories = sorted(list(set(item["category"] for item in items)))
    
    return items, categories

# --- UNIFIED SEO LOGIC ---

def get_all_products_unified():
    """
    Carga y unifica productos de TODOS los archivos JSON.
    Elimina duplicados basados en URL.
    """
    all_items = []
    seen_urls = set()
    
    for key in DATA_FILES:
        items = _load_json(DATA_FILES[key])
        for item in items:
            # Usamos URL como identificador único
            if item.get('url') and item['url'] not in seen_urls:
                all_items.append(item)
                seen_urls.add(item['url'])
                
    return all_items

def get_products_by_category_slug(slug):
    """
    Filtra productos unificados por slug de categoría.
    Retorna: (lista_productos, nombre_real_categoria)
    """
    all_items = get_all_products_unified()
    matching_items = []
    real_category_name = ""
    
    for item in all_items:
        cat_name = item.get("category", "Varios")
        if slugify(cat_name) == slug:
            matching_items.append(item)
            # Capturamos el nombre real (formato display) de la primera coincidencia
            if not real_category_name:
                real_category_name = cat_name
                
    return matching_items, real_category_name

def get_all_categories_info():
    """
    Retorna una lista de tuplas (nombre_real, slug) de todas las categorías disponibles.
    Útil para sitemap y enlazado interno.
    """
    all_items = get_all_products_unified()
    categories_map = {} # slug -> real_name
    
    for item in all_items:
        cat_name = item.get("category", "Varios")
        cat_slug = slugify(cat_name)
        if cat_slug not in categories_map:
            categories_map[cat_slug] = cat_name
            
    # Retornar lista ordenada alfabéticamente
    return sorted([(name, slug) for slug, name in categories_map.items()], key=lambda x: x[0])


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
    tag = os.getenv("AMAZON_TAG", "tu_tag_defecto-21")
    
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