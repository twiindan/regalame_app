# 🎁 Regálame - Amigo Invisible MVP

Una aplicación moderna y rápida para organizar el "Amigo Invisible" (Secret Santa) con un toque de monetización mediante afiliados de Amazon y chat anónimo integrado.

## 🚀 Características

- **Grupos Personalizados**: Crea grupos con presupuesto, fecha de evento y descripción.
- **Invitaciones**: Sistema de invitaciones por email y enlace directo (WhatsApp/Compartir).
- **Lista de Deseos**: Los usuarios añaden deseos. Si es un enlace de Amazon, se limpia; si es texto, se genera un enlace de búsqueda de afiliado.
- **Sorteo Inteligente**: Algoritmo que evita que te toque a ti mismo y permite configurar **vetos** (exclusiones).
- **Chat Anónimo 🎅**: Habla con tu "Santa" o con tu "Giftee" sin revelar tu identidad hasta el final.
- **Diseño Moderno**: Interfaz limpia usando TailwindCSS y carga dinámica con HTMX.

## 🛠️ Stack Tecnológico

- **Backend**: Python + [FastAPI](https://fastapi.tiangolo.com/)
- **Base de Datos**: [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic)
- **Frontend**: Jinja2 Templates + [HTMX](https://htmx.org/) (Zero JS approach)
- **Estilos**: TailwindCSS (via CDN)
- **Migraciones**: Alembic
- **Despliegue**: Preparado para Railway / Render / Heroku

## 💻 Instalación Local

1. **Clonar el repositorio**:
   ```bash
   git clone <tu-repo>
   cd regalame_gemini3
   ```

2. **Crear entorno virtual e instalar dependencias**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**:
   Crea un archivo `.env` en la raíz:
   ```env
   SECRET_KEY=tu_clave_secreta_aqui
   DATABASE_URL=sqlite:///database.db
   DOMAIN_URL=http://localhost:8000
   # Configuración de Email (opcional para invitaciones)
   MAIL_USERNAME=tu_usuario
   MAIL_PASSWORD=tu_password
   MAIL_FROM=info@regalame.app
   MAIL_PORT=587
   MAIL_SERVER=smtp.gmail.com
   # Curación editorial del catálogo (opcional; por defecto off = shadow)
   # EDITORIAL_FILTER_MODE=off
   # EDITORIAL_PROVIDER_API_KEY=tu_api_key   # o el compartido NAN_API_KEY
   # EDITORIAL_PROVIDER_BASE_URL=https://api.nan.builders/v1
   # EDITORIAL_PROVIDER_MODEL=qwen3.6
   # EDITORIAL_PROVIDER_REASONING_EFFORT=    # vacío = se omite (recomendado)
   # EDITORIAL_JOB_CONCURRENCY=4             # 1 = secuencial
   ```

4. **Ejecutar migraciones**:
   ```bash
   alembic upgrade head
   ```

5. **Iniciar el servidor de desarrollo**:
   ```bash
   uvicorn main:app --reload
   ```

## 🧪 Tests

Para ejecutar la suite de pruebas:
```bash
pytest
```

## 🚢 Despliegue (Railway)

Este proyecto está listo para Railway:
1. Conecta tu repo de GitHub a Railway.
2. Añade un servicio de PostgreSQL.
3. Configura las Variables de Entorno en el panel de Railway (especialmente `DATABASE_URL` y `SECRET_KEY`).
4. Railway usará automáticamente el `Procfile` para arrancar la aplicación.

### Refresco periódico del catálogo (servicio cron)

El catálogo se refresca solo, una vez por día, desde un segundo servicio del mismo proyecto
de Railway. Ese servicio **no** es el web: la web sigue usando el `Procfile`.

1. En Railway, crea un servicio nuevo en el mismo proyecto, apuntando al mismo repositorio.
2. Configurá en **Settings** del servicio, **antes de que corra**:
   - **Cron Schedule:** `0 4 * * *`. Es lo que lo convierte en un servicio programado.
   - **Restart policy:** `Never`.
   - **Build → Dockerfile path:** `scraper/Dockerfile`.
   - **Start command:** `python -m jobs.refresh_catalog`.
   - **Root directory:** la raíz del repositorio. (El Dockerfile vive en `scraper/` a propósito:
     un `Dockerfile` en la raíz haría que Railway buildee **la web** con él y rompería el deploy.)
3. Variables de entorno: sólo `DATABASE_URL`, referenciando el Postgres del proyecto
   (`${{Postgres.DATABASE_URL}}`). No hacen falta `SECRET_KEY` ni las de email.
4. Verificá la primera corrida en los logs: una línea `section=... status=...` por sección y
   un resumen `import: created=... updated=... lists=... sections_ok=...`.

**Por qué el schedule y el `Restart policy: Never` van primero.** El job sale con **exit 1**
cuando ninguna sección quedó sana, a propósito, para que el fallo sea visible en los logs. El
default de Railway es `On Failure` con hasta **10 reintentos**, así que un servicio desplegado
**sin** su cron schedule reiniciaría la corrida hasta diez veces, y cada reinicio vuelve a
scrapear Amazon entero — justo el patrón de tráfico que puede marcar la IP como bot.

**Tres cosas del cron de Railway que importan acá:**
- El horario es **UTC**: `0 4 * * *` son las 4 de la mañana UTC.
- Mínimo **5 minutos** entre corridas.
- El proceso **debe terminar**. Si la corrida anterior sigue activa cuando toca la siguiente,
  Railway **saltea** la nueva. Una corrida completa tarda varios minutos.

**Esto se configura en el dashboard, no en el repo.** `railway.json` está deprecado (deja de
leerse el 2026-12-01) y **los servicios nuevos ya no pueden usarlo**, así que no hay camino por
código para estas dos settings: el Cron Schedule y el Dockerfile path son de Settings.

Un `sections_ok` menor a 3 significa que alguna sección falló o salió sospechosa. El catálogo
existente queda intacto: la corrida siguiente lo reintenta. Y si ves
`deactivation skipped: at least one section came back shorter than its baseline`, es el guard
haciendo su trabajo: una sección vino incompleta y por eso no se retiró ningún producto.

**Prueba local, sin browser y sin red:**

```bash
python -m jobs.refresh_catalog --data-dir . --dry-run
```

### Curación editorial del catálogo (servicios cron)

La curación clasifica los productos del catálogo con IA (`eligible`, `contextual`,
`excluded`, `unknown`) y filtra las superficies públicas. Corre en **modo shadow**
por defecto (`EDITORIAL_FILTER_MODE=off`): los jobs pueden clasificar y persistir
decisiones, pero la web no cambia en nada. El filtrado se activa recién cuando el
gate de evaluación pasa y el backfill está completo al 100%.

Se configura con **dos servicios cron** separados (mismo proyecto de Railway, mismo
patrón que el refresco del catálogo: `Restart policy: Never` y el Cron Schedule
**antes** de la primera corrida):

1. **Clasificación** — Start command: `python -m jobs.classify_catalog`.
   Variables: `DATABASE_URL`, `EDITORIAL_PROVIDER_API_KEY` (o el compartido
   `NAN_API_KEY`) y, si hace falta, `EDITORIAL_PROVIDER_BASE_URL`,
   `EDITORIAL_PROVIDER_MODEL` y los límites `EDITORIAL_JOB_*`. Probá primero con
   `--dry-run` (cero llamadas y cero escrituras) y después sin él para persistir
   decisiones.
2. **Gate de evaluación** — Start command: `python -m jobs.evaluate_curation`.
   Es offline (no llama al proveedor): `--sample-out sample.json` emite la muestra
   estratificada para etiquetar a mano, y `--labels sample.json` evalúa y registra
   el veredicto. **No** necesita cron propio.

| Variable | Default | Para qué |
|----------|---------|----------|
| `EDITORIAL_FILTER_MODE` | `off` | `off` = shadow; `enforce` = filtra (sólo si el gate pasa). Se lee una vez al importar: cambiarla requiere restart/redeploy. |
| `EDITORIAL_PROVIDER_API_KEY` (o `NAN_API_KEY`) | — (secreto) | Bearer token del proveedor. Se toma de `EDITORIAL_PROVIDER_API_KEY` (preferido) o, como fallback, del compartido `NAN_API_KEY`. Sin ninguno, ninguna corrida real clasifica. |
| `EDITORIAL_PROVIDER_BASE_URL` | `https://api.nan.builders/v1` | Base URL OpenAI-compatible. |
| `EDITORIAL_PROVIDER_MODEL` | `qwen3.6` | Modelo; también entra en el fingerprint de reclasificación. |
| `EDITORIAL_PROVIDER_REASONING_EFFORT` | *(vacío = se omite)* | Esfuerzo de razonamiento OpenAI-compatible. Por defecto se omite: el sondeo real mostró que `minimal` es ~8x más rápido pero devuelve ~2x más decisiones inválidas (el modelo inventa un `context` que no es el `category_slug` del producto), y una decisión inválida no se cachea, así que la cobertura nunca llega a 1.0. `minimal`/`low` quedan como opt-in. |
| `EDITORIAL_JOB_COMMIT_EVERY` | `25` | Commit de decisiones cada N productos. |
| `EDITORIAL_JOB_RPM` | `60` | Máximo de requests por minuto; espacia los **inicios** también cuando hay llamadas concurrentes. `0` desactiva el espaciado. |
| `EDITORIAL_JOB_CONCURRENCY` | `1` | Llamadas al proveedor en vuelo a la vez. `1` = secuencial (comportamiento previo). Producción: `4`, dejando libre 1 de los 5 slots concurrentes de NaN. Las llamadas corren en hilos, pero **todas** las lecturas/escrituras/commits de DB siguen en el hilo principal (`Session` de SQLModel no es thread-safe). |
| `EDITORIAL_JOB_MAX_SECONDS` | `3300` | Tope de tiempo por corrida (55 min). |
| `EDITORIAL_JOB_MAX_PRODUCTS` | `500` | Tope de productos por corrida. |

`EDITORIAL_POLICY_VERSION` y `EDITORIAL_CONTEXTS` **no** son variables de entorno:
son constantes de código en `curation.py`. La secuencia completa de despliegue
(migración → backfill shadow → gate → `enforce`), el gate exacto y el rollback
están en
[`docs/deploy/2026-10-04-curacion-regalos-ia-rollout-runbook.md`](docs/deploy/2026-10-04-curacion-regalos-ia-rollout-runbook.md).

## 📝 Licencia

Este proyecto es un MVP para fines educativos y personales.
