# Diseño: Catálogo navegable (búsqueda, filtros, orden y paginación)

- Fecha: 2026-09-27
- Estado: Aprobado para planificación
- Ámbito: Fase 1 de 3 del rediseño del catálogo

## 1. Contexto y problema

`regalame_app` es un MVP de Amigo Invisible que monetiza con enlaces de afiliado de Amazon.
El catálogo de productos (best sellers, tendencias y más deseados) vive en tres archivos JSON
en disco y se lee completo en cada petición.

Comportamiento actual, verificado en el código:

- `services._load_json()` abre y parsea el JSON entero en **cada** request.
- El dashboard llama a `get_random_products()` tres veces, es decir, **tres lecturas completas**
  de archivos de ~650 KB por carga de página.
- Las páginas `/trends`, `/bestsellers` y `/most-desired` renderizan **todos** los productos como
  nodos del DOM (hasta ~1450 tarjetas) y filtran con JavaScript en el cliente.
- "Ver más productos" no pagina: solo destapa divs ya presentes en el HTML.
- No existe búsqueda por texto, ni filtro por precio, ni ordenamiento.

Consecuencias: rendimiento degradado, listados que no escalan, imposibilidad de añadir datos
frescos o recomendaciones sobre esta base.

## 2. Objetivo

Convertir el catálogo en un motor consultable sobre la base de datos, con búsqueda por texto,
filtros (categoría, fuente, rango de precio), ordenamiento y paginación resueltos en el servidor,
preservando las URLs y el posicionamiento SEO existentes.

## 3. Fuera de alcance (Fase 1)

- Scraper automático o programado (cron/scheduler). → Fase 2
- Recomendaciones personalizadas (por presupuesto de grupo, wishlist, reservas). → Fase 3
- Búsqueda tolerante a errores tipográficos o relevancia semántica.
- Eliminación de los archivos JSON (permanecen como fuente de datos).
- Rediseño visual de la interfaz.

## 4. Decisiones de arquitectura

| Decisión | Elegido | Alternativa descartada | Motivo |
|---|---|---|---|
| Sustrato de datos | Tabla `Product` en la DB | Cachear JSON en memoria | La base habilita datos frescos y recomendaciones; la caché se descarta en la fase siguiente |
| Búsqueda | SQL con columnas normalizadas | Meilisearch / FTS5 | Sobredimensionado para ~4350 productos; añade infraestructura a operar |
| Relación con las listas | Tabla de enlace `ProductList` | Columna `source` única | Un producto puede pertenecer a varias listas a la vez; la columna única duplicaría filas |
| Tag de afiliado | Inyectado en el render | Guardado en la URL almacenada | Evita reimportar todo el catálogo al cambiar el tag |
| Filtrado | Servidor, con la URL como estado | Filtrado en cliente | Permite compartir resultados e indexarlos de forma controlada |

## 5. Modelo de datos

Dos tablas nuevas en `models.py`. La relación muchos-a-muchos preserva el deduplicado por URL que
hoy hace `get_all_products_unified()`, sin perder la pertenencia a cada lista.

```python
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    asin: str = Field(unique=True, index=True)        # clave de upsert
    title: str
    title_normalized: str = Field(index=True)         # minúsculas y sin tildes, para búsqueda
    image_url: Optional[str] = None
    url: str                                          # URL canónica, sin tag de afiliado
    category: str = Field(index=True)
    category_slug: str = Field(index=True)            # reutiliza slugify()
    price_numeric: Optional[float] = Field(default=None, index=True)  # None si es "N/A"
    price_raw: Optional[str] = None                   # "25,69 €" para mostrar
    scraped_at: datetime                              # fecha de extracción del JSON
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, index=True)

class ProductList(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", index=True)
    list_key: str = Field(index=True)                 # "bestsellers" | "trends" | "desired"
    rank: int                                         # posición original dentro de la lista
    # Restricción UNIQUE(product_id, list_key)
```

Notas de diseño:

- `url` se almacena sin el tag de afiliado. El tag se inyecta al renderizar con
  `generate_amazon_link()`, ya existente. Cambiar el tag no requiere reimportar.
- `title_normalized` y `category_slug` se calculan en el import con `unicodedata` (mismo criterio
  que `slugify`). Se resuelven en Python porque SQLite no dispone de `unaccent` y PostgreSQL sí,
  lo que mantiene paridad entre desarrollo y producción.
- `price_numeric` es anulable: los productos sin precio se muestran pero quedan excluidos de los
  filtros por rango de precio.
- `is_active` permite desactivar productos ausentes en una importación futura sin perder historial.

## 6. Módulos

`services.py` concentra hoy cinco responsabilidades. No se amplía; se extrae el catálogo.

| Módulo | Cambio |
|---|---|
| `models.py` | Añade `Product` y `ProductList` |
| `catalog.py` | **Nuevo.** `CatalogQuery`, `CatalogResult`, `search_products()`, `list_categories()`, `import_from_json()`, `extract_asin()`, `normalize_text()` |
| `services.py` | **Elimina** `_load_json`, `get_random_products`, `get_all_products`, `get_all_products_unified`, `get_products_by_category_slug`, `get_all_categories_info`. **Conserva** `perform_draw`, `generate_amazon_link` y `scrape_metadata`. `get_blog_post_detail` se **reimplementa** sobre `catalog.search_products()` (sus filtros de `max_price` y `category` son exactamente los del catálogo) |
| `main.py` | Las rutas de catálogo y el sitemap consumen `catalog.search_products()` / `catalog.list_categories()` |

`_parse_price()` se traslada de `services.py` a `catalog.py` sin reescribirse.

## 7. Importación JSON → DB

Script `import_catalog.py` en la raíz:

```
python import_catalog.py             # importa los tres JSON
python import_catalog.py --dry-run   # muestra cambios sin escribir
```

Algoritmo idempotente (upsert por `asin`):

1. Extrae el ASIN de la URL (`/dp/{ASIN}` o `/gp/product/{ASIN}`).
2. Sin ASIN: usa un hash del path de la URL como clave.
3. Parsea el precio con `_parse_price()`; `price_numeric` queda en `None` si no es convertible.
4. Normaliza el título (`title_normalized`) y la categoría (`category_slug`).
5. Si el ASIN existe, actualiza los campos modificados; si no, inserta.
6. Reconstruye `ProductList` con el `rank` según el orden del JSON de origen.

Ejecutarlo dos veces no produce duplicados. En Fase 2, el scraper solo deberá volver a ejecutar
este import.

La migración Alembic crea ambas tablas y los índices indicados en la sección 5.

## 8. Semántica de búsqueda

```python
@dataclass
class CatalogQuery:
    q: Optional[str] = None            # texto libre
    category_slug: Optional[str] = None
    source: Optional[str] = None       # bestsellers | trends | desired | None = todas
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    sort: str = "relevance"            # relevance | price_asc | price_desc | newest
    page: int = 1
    per_page: int = 24

@dataclass
class CatalogResult:
    items: list[Product]
    total: int
    page: int
    per_page: int
    total_pages: int
```

Reglas:

- `q`: se normaliza con `normalize_text()` y se aplica `LIKE '%…%'` sobre `title_normalized`.
  Términos de menos de dos caracteres se ignoran. Busca en todas las fuentes.
- `category_slug`: coincidencia exacta contra `category_slug`. `None` significa todas.
- `source`: `EXISTS (ProductList WHERE list_key = source)`. `None` significa todas.
- Precio: si se define `min_price` o `max_price`, se excluyen los productos con `price_numeric` nulo.
- `sort`:
  - `relevance`: con `q`, primero los títulos que **empiezan** por el término (`LIKE 'termino%'`, portable
    entre SQLite y PostgreSQL) y luego el resto, conservando dentro de cada grupo el `rank` original;
    sin `q`, únicamente el `rank` original de la lista.
  - `price_asc` / `price_desc`: por `price_numeric`, con los nulos al final.
  - `newest`: por `scraped_at DESC`.
- Paginación: `per_page` por defecto 24, tope 60. `total` se calcula con un `COUNT` sobre los mismos
  filtros.
- `page` se ajusta al rango válido en las rutas de catálogo (`/catalog`, `/bestsellers`,
  `/trends`, `/most-desired`): fuera de rango se limita a la última página disponible. En
  `/ideas/{slug}` una página fuera de rango responde `404` (enmienda 2026-10-07, sección 17).

## 9. Rutas, URLs y SEO

| Ruta | Comportamiento | Indexable |
|---|---|---|
| `/catalog` | Catálogo unificado con `?q=&category=&source=&min=&max=&sort=&page=` | No (`noindex, follow`) |
| `/bestsellers` `/trends` `/most-desired` | Se conservan; renderizan `/catalog` con `source` fijo y su título | Sí |
| `/ideas/{slug}` | Landing SEO por categoría, con paginación de servidor | Sí |
| `/blog/{slug}` | Sin cambios | Sí |

Reglas SEO:

1. Las páginas con parámetros `q`, `sort` o `page` se marcan `noindex, follow` para evitar
   contenido duplicado por combinaciones infinitas de filtros.
2. `/ideas/{slug}` se indexa, con `canonical` autorreferente (página 1: `/ideas/{slug}`; página N:
   `/ideas/{slug}?page=N`) y `rel="prev"` / `rel="next"` en la paginación.
3. Sin JavaScript todo funciona: buscador y filtros son un `<form method="GET">`. HTMX es una
   mejora progresiva, no un requisito. Un crawler recibe productos reales en el HTML.
4. El sitemap mantiene las categorías y no incluye `/catalog`.

Mejora con HTMX: el formulario y el paginador usan `hx-get` contra un partial
(`partials/catalog_results.html`) con `hx-push-url="true"`, de modo que la URL refleje el estado
y el botón "atrás" funcione.

## 10. UX

- Buscador global en `base.html` (input + Enter → `/catalog?q=…`), visible en todas las páginas.
- Barra de filtros en `/catalog`: chips de categoría existentes, input de búsqueda, selector de
  orden, campos de precio mínimo/máximo y chips de fuente.
- Grid con el sistema visual actual (`glass-panel`, `rounded-2xl`) y el botón "Añadir a mi lista"
  de un clic ya existente.
- Contador de resultados ("Mostrando 1–24 de 1450") y paginador numérico.
- Estado vacío reutilizando `#no-results`, con mensaje distinto según haya filtros activos.

## 11. Errores y casos borde

| Caso | Comportamiento |
|---|---|
| `q` vacío | Lista normal filtrada por el resto de criterios |
| `min_price > max_price` | Se invierten silenciosamente |
| `page` fuera de rango en rutas de catálogo | Se limita a la última página válida |
| `page` no numérica o menor que 1 en rutas de catálogo | Se limita a 1 |
| `page` fuera de rango, no numérica o menor que 1 en `/ideas/{slug}` | `404` (enmienda 2026-10-07) |
| `category_slug` inexistente en `/catalog` | Estado vacío, sin redirección |
| `category_slug` inexistente o sin productos visibles en `/ideas/{slug}` | `404` (enmienda 2026-10-07) |
| Precio `"N/A"` | Se muestra sin precio; no participa en filtros de precio |
| Cero resultados | Estado vacío con llamada a la acción |

## 12. Testing

- Unitarios: `_parse_price` (`"19,99 €"`, `"EUR 20.50"`, `"1.234,56"`, `"N/A"`, `None`),
  `extract_asin` (`/dp/…`, `/gp/product/…`, URL sin ASIN), `normalize_text` (`"Café"` → `"cafe"`).
- Integración: `search_products` con filtros combinados, paginación (`total`, tope de 60, ajuste de
  página), orden por precio con nulos al final, exclusión de nulos en rango de precio.
- Idempotencia: dos ejecuciones del import producen el mismo `COUNT` y ningún duplicado.
- Rutas: `/catalog` con y sin filtros responde 200; `/bestsellers` responde 200; `/ideas/{slug}`
  pagina correctamente.
- Regresión: los 17 tests existentes deben seguir pasando.

## 13. Migración y despliegue

1. Migración Alembic que crea `product` y `productlist` con índices.
2. Ejecutar `python import_catalog.py` una vez por entorno.
3. Desplegar el código de rutas.
4. Rollback: las tablas nuevas son aditivas; revertir la migración no afecta datos existentes.

## 14. Riesgos

| Riesgo | Mitigación |
|---|---|
| Pérdida de indexado SEO al paginar | `/ideas/{slug}` indexable con canonical y `rel=prev/next`; `noindex` solo en resultados filtrados |
| Datos de precio sucios (`"N/A"`, formato español) | `_parse_price` ya probado; los no convertibles quedan nulos y fuera de filtros |
| Catálogo desactualizado (datos de enero 2026) | Se mitiga en Fase 2 (scraper); el diseño lo contempla con `scraped_at` e `is_active` |
| Duplicados por ASIN ausente | Clave de respaldo por hash del path de la URL |

## 15. Criterios de aceptación

1. `/catalog` busca por texto sin distinguir mayúsculas ni tildes.
2. Los filtros de categoría, fuente y rango de precio se combinan entre sí.
3. El ordenamiento por precio funciona y coloca los nulos al final.
4. La paginación respeta el tope de 60 y ajusta páginas fuera de rango.
5. `/bestsellers`, `/trends`, `/most-desired` e `/ideas/{slug}` responden 200 y mantienen sus URLs.
6. El import es idempotente: dos ejecuciones, mismo conteo.
7. Los 17 tests existentes siguen verdes.
8. Sin JavaScript, la página 1 muestra productos reales en el HTML.
9. Las páginas con filtros llevan `noindex, follow`; `/ideas/{slug}` es indexable.

## 16. Fases siguientes (contexto, no alcance)

- **Fase 2 — Datos vivos:** scraper programado que alimenta la tabla `Product` mediante el mismo
  import, con desactivación de productos ausentes.
- **Fase 3 — Recomendaciones:** sugerencias según presupuesto del grupo, wishlist del destinatario
  y reservas existentes, apoyadas en la base ya normalizada.

## 17. Enmienda 2026-10-07: política estricta de `/ideas/{slug}`

Decisión del usuario (2026-10-07): endurecer la landing SEO por categoría. Sustituye, solo para
esta ruta, las reglas generales de las secciones 8, 9 y 11.

| Caso | Comportamiento |
|---|---|
| `slug` ausente de `list_categories(session)` (conjunto visible) | `404` real |
| `?page` no entero, `< 1` o `> total_pages` | `404` real |
| `?page=N` con `N > 1` en rango | `200`; `canonical` autorreferente `/ideas/{slug}?page=N` |
| `/ideas/{slug}` página 1 | `200`; `canonical` `/ideas/{slug}` |

- «`?page` no entero» significa **solo dígitos ASCII** (`[0-9]+`): espacios, signos (`+`/`-`), separadores `_` y dígitos no-ASCII se rechazan con `404`.
- En las páginas `200` se conservan `rel="prev"` y `rel="next"` de la paginación.
- La respuesta `404` usa `templates/404.html`, con `meta robots="noindex"`, y no emite `canonical`.
- Las peticiones HTMX a una URL inválida también reciben `404`.
- Consecuencia aceptada: bajo modo editorial `enforce`, una categoría sin productos visibles
  responde `404` en lugar de renderizar una página vacía.
- El resto de rutas (`/catalog`, `/bestsellers`, `/trends`, `/most-desired`) conservan el recorte
  de página y el estado vacío descritos en las secciones 8 y 11.

## 18. Enmienda 2026-10-07: política de indexación de rutas legacy con query string

Decisión del usuario (2026-10-07): las rutas legacy (`/bestsellers`, `/trends`, `/most-desired`)
siguen respondiendo `200` y son **indexables solo en su URL limpia**, sin query string. Cualquier
query string en esas rutas pasa a renderizar `noindex, follow`, porque hoy no emiten `canonical` y
sus variantes con parámetros son duplicados indexables.

| Caso | Comportamiento |
|---|---|
| `/bestsellers`, `/trends`, `/most-desired` sin query string | `200`; indexable (sin `meta robots`) |
| Cualquier query string en esas rutas (`?source=…`, `?q=&sort=relevance&source=…`, etc.) | `200`; `noindex, follow` |

- `source` **no** es un parámetro de query enlazado en estas rutas: su valor es fijo por ruta
  (`trends`, `desired`, `bestsellers`). Un `?source=` aportado por el visitante no alimenta las
  condiciones de filtro; solo genera un duplicado y por eso se clasifica como `noindex` en lugar
  de incorporarse a los filtros.
- `/catalog` conserva su `noindex, follow` incondicional (cualquier parámetro, incluido
  `?source=`), sin cambios.
- `/ideas/{slug}` no se ve afectada: la página 1 sigue indexable y `?page=N` sigue indexable según
  la sección 17.
- La regla vive en `_catalog_context(...)` mediante el nuevo parámetro `has_query_params`, que solo
  pasan las tres rutas legacy. `/catalog` (`force_noindex=True`) y `/ideas/{slug}`
  (`always_indexable=True`) mantienen su política intacta.

