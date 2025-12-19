Actúa como un Desarrollador Senior Full-Stack experto en Python. Vamos a construir un MVP de una aplicación de "Amigo Invisible" (Secret Santa) con monetización por afiliados de Amazon.

CONTEXTO DEL PROYECTO:
El objetivo es una aplicación web rápida donde los usuarios crean grupos de amigo invisible, se unen mediante un código y añaden su lista de deseos.
- La característica clave es que los deseos se convierten automáticamente en enlaces de búsqueda de afiliados de Amazon.
- La arquitectura debe ser un "Monolito Moderno" para evitar complejidad en el frontend.

STACK TECNOLÓGICO OBLIGATORIO:
1. Backend: Python + FastAPI.
2. Base de Datos: SQLModel (sobre SQLite para desarrollo).
3. Templating: Jinja2 (Server Side Rendering).
4. Frontend Interactivo: HTMX (para AJAX sin escribir JavaScript).
5. Estilos: TailwindCSS (vía CDN, sin compilación Node.js).
6. Testing: Pytest.

ESTRUCTURA DE ARCHIVOS DESEADA:
root/
├── main.py            # Entry point y rutas principales
├── models.py          # Definición de tablas SQLModel (User, Group, Wish, Member)
├── database.py        # Configuración de engine y sesión
├── services.py        # Lógica de negocio (Sorteo, Generador de Links Amazon)
├── templates/         # Carpetas de HTML
│   ├── base.html      # Layout principal (incluye script de HTMX y Tailwind CDN)
│   ├── index.html     # Landing page
│   └── partials/      # Fragmentos HTML para respuestas de HTMX
└── requirements.txt   # Dependencias

REGLAS DE DESARROLLO:
1. NO uses Node.js, Webpack ni React. Todo el frontend debe ser HTML + HTMX.
2. Usa inyección de dependencias de FastAPI para la sesión de base de datos.
3. Cuando generes código, dame el contenido completo del archivo para copiar y pegar.
4. Mantén la lógica de negocio (como el algoritmo del sorteo) separada en `services.py`.
5. Tienes que hacer tests de todas las funcionalidades que desarrolles. 

TAREA INICIAL:
Genera el código base ("scaffolding") funcional para:
1. `requirements.txt`
2. `database.py`
3. `models.py` (con las tablas Group y Wish básicas)
4. `templates/base.html` (configurado con Tailwind y HTMX)
5. `main.py` (con una ruta GET raíz que renderice un Hola Mundo y una ruta POST para crear grupo usando HTMX).

Empieza ahora.
