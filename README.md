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
2. En la configuración del servicio:
   - **Root directory:** la raíz del repositorio.
   - **Dockerfile path:** `scraper/Dockerfile`.
   - **Cron schedule:** `0 4 * * *`.
   - **Start command:** `python -m jobs.refresh_catalog`.
3. Variables de entorno: sólo `DATABASE_URL`, referenciando el Postgres del proyecto
   (`${{Postgres.DATABASE_URL}}`). No hacen falta `SECRET_KEY` ni las de email.
4. Verifica la primera corrida en los logs: una línea `section=... status=...` por sección y
   un resumen `import: created=... updated=... lists=... sections_ok=...`.

Un `sections_ok` menor a 3 significa que alguna sección falló o salió sospechosa. El catálogo
existente queda intacto: la corrida siguiente lo reintenta.

**Prueba local, sin browser y sin red:**

```bash
python -m jobs.refresh_catalog --data-dir . --dry-run
```

## 📝 Licencia

Este proyecto es un MVP para fines educativos y personales.
