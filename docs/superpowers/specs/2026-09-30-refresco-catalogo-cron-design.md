# Diseño: Refresco periódico del catálogo (scraper + ingesta automáticos)

- Fecha: 2026-09-30
- Estado: Aprobado para planificación
- Ámbito: Fase 2 del rediseño del catálogo (la Fase 1 dejó esto explícitamente fuera de alcance)

## 1. Contexto y problema

El catálogo de productos (best sellers, tendencias y más deseados) se alimenta así:

```
amazon_scrapper_all_categories.py  →  amazon_*_total.json  →  import_catalog.py  →  DB
        (manual, local)                  (en la raíz del repo)      (manual)
```

Verificado en el código:

- El scraper es un script suelto: las tres secciones están hardcodeadas
  (`amazon_scrapper_all_categories.py:74-81`) y se ejecuta a mano desde el IDE.
- Los tres JSON tienen entre 650 KB y 720 KB y están **commiteados** en la raíz del
  repositorio. Son datos de producción versionados como si fueran código.
- `catalog.import_from_json()` (`catalog.py:204`) es idempotente: upsert por ASIN y
  reconstrucción de ranks por lista. Deriva `scraped_at` del **mtime del archivo**
  (`catalog.py:223`).
- No existe ningún scheduler. El `Procfile` sólo declara `web`.

Consecuencia: los JSON tienen fecha del 21/01/2026 y nada los refresca. La web muestra
productos, precios y rankings que pueden tener meses. El catálogo es el producto
monetizable (enlaces de afiliado), así que su frescura es directamente ingreso.

## 2. Objetivo

Refrescar el catálogo **sin intervención humana**, de forma periódica, desde la nube, con
degradación segura: si el scraping falla, el catálogo existente no se daña.

## 3. Fuera de alcance

- Recomendaciones personalizadas. Fase 3.
- Proxy residencial o servicio de scraping de terceros. Se documenta como plan B.
- Eliminar los tres JSON del repositorio como paso de este diseño (quedan como fixtures de
  desarrollo; el job no los usa en producción).
- Rediseño visual, cambio de posicionamiento SEO, o cambios en `main.py`.
- Métricas o dashboard de salud del scraping. Los logs de Railway son la observabilidad.

## 4. Decisiones de arquitectura

| Decisión | Elegido | Alternativa descartada | Motivo |
|---|---|---|---|
| Empaquetado | Un comando único: scrape → import en el mismo proceso | Dos servicios unidos por un volumen | Sin estado persistente que mantener; scrape e import comparten el ciclo de vida de la corrida. YAGNI |
| Dónde corre | Servicio cron en Railway, proyecto existente | GitHub Actions scheduled | Reusa la `DATABASE_URL` del proyecto (cero secretos duplicados); el Postgres ya vive ahí; los schedules de Actions se demoran o se dropean |
| Scheduler | `cronSchedule` de Railway sobre un proceso que termina | APScheduler dentro del proceso web | El proceso web no debe cargar un browser 20 minutos; cada restart/redeploy duplicaría el scheduler y generaría corridas concurrentes |
| Dependencias | `requirements-scraper.txt` aparte | `playwright` en `requirements.txt` | La web no usa Playwright; no debe engordar su imagen ni ensuciar el baseline pineado |
| Ubicación del Dockerfile | `scraper/Dockerfile` | `Dockerfile` en la raíz | Railway puede buildear **la web** con un Dockerfile de raíz y voltear el deploy. El web sigue con nixpacks + `Procfile` |
| Frecuencia | Diaria (`0 4 * * *` UTC) | Cada 12 h / semanal | Un catálogo de regalos no gana nada con 12 h de frescura extra, y duplica la exposición al anti-bot |
| Archivos JSON en el job | Directorio temporal efímero | Escribir en la raíz del repo | El contenedor es efímero y no debe escribir en el checkout versionado |

## 5. Arquitectura y flujo

```
Railway cron service  (0 4 * * * UTC)
  └─ python -m jobs.refresh_catalog
       ├─ scraper.scrape_all(tmpdir)   → JSON por sección, o ausente si esa sección falló
       ├─ clasificación de salud       → secciones sanas / sospechosas / ausentes
       ├─ catalog.import_from_json(session, data_files=<secciones sanas>)
       └─ [Slice 3] catalog.deactivate_absent_products(session, list_keys=<sanas>)
     exit 0 si al menos una sección se importó; exit 1 si no se importó nada
```

Componentes nuevos:

| Archivo | Responsabilidad |
|---|---|
| `scraper.py` | Extracción de `amazon_scrapper_all_categories.py`: `SECTIONS`, `scrape_section()`, `scrape_all(out_dir)`. Los selectores y la lógica de extracción se mueven **verbatim**. |
| `jobs/refresh_catalog.py` | Orquestador. Recibe el scraper inyectado (testeable sin browser), clasifica la salud, importa y fija el exit code. |
| `requirements-scraper.txt` | `-r requirements.txt` + `playwright` pineado. |
| `scraper/Dockerfile` | `playwright install --with-deps chromium` sobre el baseline. |

`catalog.py`, `models.py`, `database.py`, `main.py` no se tocan en los slices 1, 2 y 3.
`catalog.py` recibe una función nueva en el slice 4.

El scraper se mueve con el modo `headless=True` (ya presente, sin commitear, en el working
tree): es el modo correcto para un contenedor sin display.

`amazon_scrapper_all_categories.py` se conserva en el slice 1 como wrapper delgado
(`python amazon_scrapper_all_categories.py` → `scraper.main()`), para no romper el hábito de
corrida manual desde el IDE. Es la única razón de su supervivencia: no aporta lógica.

## 6. Comportamiento ante fallos

El fallo del scraping es un camino **normal y esperado**, no excepcional. La regla es: un
fallo nunca destruye datos buenos.

| Escenario | Resultado |
|---|---|
| Una sección falla o devuelve vacío | No se escribe su JSON; no se pasa a `import_from_json`; los ranks de esa lista quedan intactos. El resto se actualiza. |
| Sección truncada silenciosamente (Amazon responde 200 con un grid parcial) | Detectada por el guard de sanidad (sección 7) y excluida igual que un fallo. |
| Las tres secciones fallan o quedan sospechosas | `exit 1`, cero escrituras a la DB. |
| Todo OK | Upsert normal + reconstrucción de ranks. |

Base de esta garantía, ya existente: `import_from_json` saltea archivos ausentes
(`catalog.py:216-217`) y listas vacías (`catalog.py:219-220`), y sólo reconstruye ranks de
las listas que efectivamente procesa (`catalog.py:278-283`).

**Idempotencia del exit code:** una corrida con `exit 1` no deja estado a medias, porque
`import_from_json` gestiona una única transacción que commitea al final (`catalog.py:285-288`).

## 7. Guard de sanidad

Modo de falla real: Amazon devuelve el grid truncado sin error. Una sección que trae 5
productos donde había 50 "parece" exitosa, y con la regla de desactivación borraría medio
catálogo.

Definición: una sección es **sana** si produjo al menos un producto **y** su conteo es
≥ `MIN_HEALTHY_RATIO` (constante de módulo, `0.5`) del conteo actual de esa lista en la DB
(`COUNT` sobre `ProductList` por `list_key`, tomado **antes** del import). En caso contrario
es **sospechosa** y se excluye de la importación y de la desactivación.

La línea base sale de la propia DB: no hace falta estado nuevo. El ratio queda como
constante del módulo; una variable de entorno para ajustarlo está fuera de alcance.

## 8. Regla de desactivación de productos obsoletos (Slice 3)

`Product.is_active` ya existe (`models.py:118`) y `search_products` ya filtra por él
(`catalog.py:127`).

Regla aprobada: la desactivación se ejecuta **sólo en una corrida sana** (las tres secciones
sanas), y dentro de ella pasa a `is_active=False` **sólo** el producto que no aparece en
ninguna de las tres listas de esa corrida.

Esa es toda la regla, y son dos condiciones, no tres: si cualquier sección falla o resulta
sospechosa, la desactivación **se omite por completo**. Por eso no hace falta razonar sobre
pertenencias a listas excluidas — con la condición de corrida sana, no existe ninguna lista
excluida. Esa condición es exactamente lo que la vuelve segura: en una corrida parcial no se
toca ni un solo flag. Nunca se borra una fila: sólo se marca inactiva, así que las URLs
existentes siguen resolviendo.

Se implementa como `catalog.deactivate_absent_products(session, list_keys)` en una
transacción posterior al import. No es atómico con él; la consecuencia de una caída en el
medio es un flag de actividad desactualizado que la corrida siguiente corrige. Se prefiere
esa simplicidad a agregar parámetros a `import_from_json`.

## 9. Configuración y despliegue

- **Schedule:** `0 4 * * *` (UTC) en la configuración del servicio cron.
- **Start command:** `python -m jobs.refresh_catalog`.
- **Dockerfile:** `scraper/Dockerfile`, referenciado desde la configuración del servicio.
- **Variables de entorno:** ninguna nueva obligatoria. `DATABASE_URL` ya está en el
  proyecto; `database.py:13-15` normaliza el esquema `postgres://`.
- **CLI del comando** (para corridas manuales y de validación local):
  - `--dry-run`: reporta sin escribir (delegado a `import_from_json(dry_run=True)`).
  - `--data-dir DIR`: usa JSON existentes y **omite el scraping**. Permite validar toda la
    lógica de importación y desactivación contra SQLite sin browser ni red.
- **Logs:** una línea por sección (`list_key`, `products`, `baseline`, `status`) y un
  resumen final (`created`, `updated`, `lists`, `sections_ok`, `deactivated`). El exit code
  es lo que Railway marca como éxito o fallo.

## 10. Plan de pruebas (TDD estricto)

`jobs/refresh_catalog` recibe el scraper por inyección, de modo que el CI lo testea con un
fake y `playwright` no entra en `requirements-dev.txt` ni en el job de CI.

Tests a escribir **antes** de la implementación (pytest, patrón de `tests/conftest.py`):

1. Tres secciones OK → se importan los tres archivos; `exit 0`; conteos esperados.
2. Una sección falla → se importan dos; los ranks de la lista fallida quedan intactos;
   `exit 0`.
3. Las tres fallan → `exit 1` y la DB queda idéntica (mismos productos, mismos ranks,
   mismos flags).
4. Sección truncada por debajo del ratio → se excluye; las otras dos se importan.
5. Desactivación (slice 4): en corrida sana, el ASIN ausente de las tres listas queda
   inactivo, y ningún otro producto cambia de estado.
6. Desactivación bloqueada: con una sección fallida o sospechosa, **ningún** producto cambia
   de estado.
7. `--data-dir` no invoca el scraper (el fake no se llama).

La extracción DOM de `scraper.py` no es unit-testeable sin browser y queda fuera del CI,
consistente con la exclusión ya existente de `tests/test_e2e.py`.

## 11. Slices y presupuesto de review

Cuatro PRs secuenciales, cada uno por debajo del presupuesto de ~400 líneas. Son cuatro y no
tres porque el slice original de "scraper + orquestador" medido supera el presupuesto con sus
tests: se parte en extracción del scraper (1) y orquestador (2), que además son dos unidades
revisables por separado.

| Slice | Contenido | Tocas |
|---|---|---|
| 1 | `scraper.py` (extracción + aislamiento por sección), wrapper del script viejo, tests sin browser | Código nuevo; DB no |
| 2 | `jobs/refresh_catalog.py` (guard de sanidad, clasificación, exit code, CLI), tests con fake scraper | Código nuevo; DB sólo en tests |
| 3 | `requirements-scraper.txt`, `scraper/Dockerfile`, `.dockerignore`, configuración del cron, sección de deploy en README | Empaquetado |
| 4 | `catalog.deactivate_absent_products()` + cableado en el job | `catalog.py`, `jobs/refresh_catalog.py` |

La separación entre 1 y 2 también habilita un ciclo de verificación más limpio: el slice 1 se
testea sin Playwright ni DB (con un browser falso), y el slice 2 sin browser pero con DB. El
slice 3 es el que recién habilita la corrida real en la nube.

Los reviews nativos de los slices 1 y 2 dejaron dos hallazgos WARNING (persistencia fuera del
containment por sección en `scraper.py`, y `UnicodeDecodeError` escapando al guard de
`_count_items`). Ambos son caminos de aborto total de una corrida desatendida y el arreglo es
barato, así que se insertó un **slice de hardening (2.5)** entre el orquestador y el empaquetado,
con sus propias tareas y tests en el plan de implementación. El orden de merge de la cadena queda:
extracción → orquestador → hardening → empaquetado → desactivación.

En el slice 1, `scraper.py` importa Playwright de forma tolerante (try/except) porque el CI no
lo instala: sin eso, la sola colección del archivo de tests rompe el job.

## 12. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Amazon bloquea la IP de datacenter de Railway (CAPTCHA, 503) | Alta | Corridas fallidas repetidas | Fallo aislado por sección, guard de sanidad, catálogo intacto. Plan B documentado: proxy residencial o volver a scrapeo local con import remoto. |
| Grid truncado sin error | Media | Desactivación masiva | Guard de sanidad por ratio. |
| El `Dockerfile` de raíz voltea el deploy del web | Baja si se respeta `scraper/Dockerfile`; alta si no | Web caída | El Dockerfile vive en `scraper/`. Verificación explícita en el slice 3 de que el web sigue con `Procfile`. |
| Imagen de Railway pesada por chromium (~500 MB) | Alta | Builds más lentos | Servicio separado: no afecta el build del web. |
| Corridas largas (~15-25 min) solapadas | Baja (cron diario) | Pisado de escrituras | El proceso termina; no hay solapamiento a 24 h de separación. |
| Deriva de dependencias (el problema histórico del repo) | Media | Falla silenciosa | `requirements-scraper.txt` pineado; el CI sigue validando el baseline del web. |

## 13. Criterios de aceptación

1. `python -m jobs.refresh_catalog --data-dir <dir>` contra SQLite importa y reporta sin
   scraping ni red.
2. El comando devuelve `exit 1` y no escribe nada cuando todas las secciones fallan.
3. Una sección fallida o sospechosa no altera los ranks ni los flags de actividad de su
   lista.
4. En corrida sana, un ASIN ausente de todas las listas queda con `is_active=False`, y
   ningún producto aparece ni desaparece de la DB.
5. El servicio cron en Railway corre diario sin intervención y el catálogo en producción
   muestra `scraped_at` del día de la corrida.
6. El CI sigue verde sin Playwright instalado, y el web sigue desplegándose con `Procfile`.
