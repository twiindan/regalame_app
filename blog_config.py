# Configuración de Posts para el Blog (Listas Curadas)

BLOG_POSTS = [
    # --- NAVIDAD ---
    {
        "slug": "regalos-navidad-mas-deseados",
        "title": "Los regalos más deseados para Navidad",
        "description": "Una selección curada a mano con los regalos que más gustan para estas Navidades: ideas para todos los gustos y presupuestos, con enlace directo a Amazon.",
        "criteria": {
            "items": [
                "B0B77CMJXZ", "B0FLQG3BL5", "B0DHSDHHPG", "B0CN41GMDK", "B0DRCZ7YL2",
                "B0D9LNMRB6", "B0FXB1RNCM", "B0FQNWG1YX", "B07Q7463M7", "B0CHFHK76L",
                "B08CGQZ7ND", "B09FK88YSH", "B09XHTR4RP", "B0CJVTDTB1", "B0B8ZMMV2H",
                "B09C1ZT1TQ", "B0FPQRM6MS", "B0D2D4M1VG", "B0FZB7CGCK", "B07MCD3WVG",
                "B07BB2MBNC", "B0DT4RPCK9", "B08L9HVWT3", "B0DHNYMK86", "8434439689",
                "B0F5HPS9HW", "B0CB4JY5DV"
            ]
        },
        "faq": [
            {"q": "¿Cómo elegir un regalo de Navidad acertado?", "a": "Piensa primero en los gustos y la edad de quien lo recibe, no solo en la categoría. Si tiene una lista de deseos, revísala antes de comprar y compara varias opciones antes de decidirte."},
            {"q": "¿Cuándo conviene hacer las compras de Navidad?", "a": "Cuanto antes, mejor: con las fechas cercanas suben los plazos de envío y algunos productos pueden agotarse. Revisa los tiempos de entrega de cada vendedor antes de pedir."},
            {"q": "¿Sirve esta selección para un amigo invisible?", "a": "Sí, siempre que respetes el límite de precio acordado en el grupo. Revisa el importe pactado antes de elegir cada opción."},
        ],
        "hero_image": None
    },

    # --- PRECIO / PRESUPUESTO ---
    {
        "slug": "regalos-amigo-invisible-10-euros",
        "title": "Top 15 Regalos de Amigo Invisible por menos de 10€",
        "description": "El límite de precio más difícil. Hemos encontrado las joyas ocultas de Amazon para quedar genial sin gastar casi nada.",
        "criteria": {
            "max_price": 10.0
        },
        "faq": [
            {"q": "¿Qué regalo funciona bien para un amigo invisible con poco presupuesto?", "a": "Los detalles útiles o con un guiño personal suelen funcionar mejor que los objetos grandes. Fija el límite pactado en tu grupo y compara varias opciones dentro de ese rango antes de decidir."},
            {"q": "¿Cómo saber si un regalo barato es de buena calidad?", "a": "Lee la descripción del producto y las condiciones del vendedor: materiales, dimensiones y qué incluye el paquete. Los precios y la disponibilidad pueden cambiar, así que comprueba la ficha actual antes de comprar."},
            {"q": "¿Cuánto debería gastar en un amigo invisible?", "a": "No hay una cifra única: depende de lo que acuerde el grupo. Lo importante es respetar el presupuesto pactado para que el intercambio sea justo para todos."},
        ],
        "hero_image": None 
    },
    {
        "slug": "regalos-baratos-menos-20-euros",
        "title": "20 Regalos por menos de 20€ que parecen de lujo",
        "description": "¿Presupuesto ajustado? Aquí tienes la selección definitiva de detalles económicos que sorprenderán a cualquiera.",
        "criteria": {
            "max_price": 20.0
        },
        "faq": [
            {"q": "¿Cómo acertar con un regalo de presupuesto ajustado?", "a": "Prioriza objetos de uso diario o ligados a una afición concreta de quien lo recibe. Si existe una lista de deseos, es la referencia más fiable para no fallar."},
            {"q": "¿Qué hace que un regalo económico parezca de más calidad?", "a": "La presentación y la utilidad pesan más que el precio. Compara materiales y descripciones entre varias opciones de la misma categoría antes de elegir."},
            {"q": "¿Los precios de esta guía pueden cambiar?", "a": "Sí. Los precios de las tiendas online se actualizan con frecuencia, así que comprueba el precio actual en la ficha de cada producto antes de comprar."},
        ],
        "hero_image": None 
    },

    # --- NICHOS Y AFICIONES ---
    {
        "slug": "ideas-regalo-gamers-videojuegos",
        "title": "Zona Gamer: Accesorios y Juegos imprescindibles",
        "description": "Sube de nivel con esta selección de periféricos, consolas y merchandising para los amantes de los videojuegos.",
        "criteria": {
            "category": "Videojuegos"
        },
        "faq": [
            {"q": "¿Qué regalar a alguien al que le gustan los videojuegos?", "a": "Depende de la plataforma que use y de los juegos que ya tenga. Los accesorios y periféricos suelen encajar mejor que un título concreto, porque no dependen de haber jugado o no a un juego determinado."},
            {"q": "¿Cómo acertar si no sé qué consola tiene?", "a": "Comprueba la compatibilidad en la descripción del producto antes de comprar, o pregunta a alguien cercano. Si tiene una lista de deseos, es la referencia más fiable."},
            {"q": "¿Sirven los accesorios para quien juega en PC y en consola?", "a": "Algunos son multiplataforma y otros no. Revisa en la ficha del producto con qué dispositivos es compatible antes de decidirte."},
        ],
        "hero_image": None
    },
    {
        "slug": "regalos-fitness-deporte",
        "title": "Para los locos del deporte: Equípate al mejor precio",
        "description": "¿Propósito de año nuevo? Ropa técnica, accesorios de gym y gadgets para mantenerte en forma.",
        "criteria": {
            "category": "Deportes y aire libre"
        },
        "faq": [
            {"q": "¿Qué regalar a alguien que empieza a hacer deporte?", "a": "Los básicos de ropa técnica y los accesorios de entrenamiento suelen ser más útiles al principio que los equipos grandes. Valora el tipo de actividad que practica antes de elegir."},
            {"q": "¿Cómo elegir la talla al regalar ropa deportiva?", "a": "Sin conocer las medidas es fácil fallar. Si no puedes consultarlas, los accesorios sin talla, como botellas, guantes o bandas de resistencia, son una alternativa más segura."},
            {"q": "¿Es buena idea regalar un gadget de deporte?", "a": "Depende del interés real de la persona. Si la actividad ya forma parte de su rutina, revisa la descripción y la compatibilidad con sus dispositivos antes de comprar."},
        ],
        "hero_image": None
    },
    {
        "slug": "mejores-libros-bestsellers",
        "title": "Los Libros más leídos del momento",
        "description": "Desde novelas adictivas hasta no ficción transformadora. Un libro siempre es el regalo perfecto.",
        "criteria": {
            "category": "Libros"
        },
        "faq": [
            {"q": "¿Es un libro un buen regalo si no conozco los gustos de la persona?", "a": "Un superventas reciente suele encajar bien con lectores variados. Si conoces los géneros o autores que ya sigue, priorízalos sobre cualquier lista de novedades."},
            {"q": "¿Cómo elegir entre novela y no ficción?", "a": "Piensa en cómo lee esa persona: la novela suele gustar a quien busca una lectura de entretenimiento, y la no ficción a quien prefiere temas concretos. Si dudas, revisa su lista de deseos."},
            {"q": "¿Puedo regalar un libro que ya tenga?", "a": "Puede pasar, y no hay forma garantizada de evitarlo. Consultar a gente cercana o revisar su lista de deseos reduce el riesgo de repetir un título."},
        ],
        "hero_image": None
    },

    # --- ESTILO DE VIDA Y HOGAR ---
    {
        "slug": "mejores-gadgets-tecnologia",
        "title": "Lo más viral en Electrónica y Gadgets",
        "description": "Desde auriculares hasta domótica. Descubre la tecnología que está marcando tendencia este año.",
        "criteria": {
            "category": "Electrónica" 
        },
        "faq": [
            {"q": "¿Qué conviene tener en cuenta al regalar tecnología?", "a": "La compatibilidad con los dispositivos que la persona ya usa es lo primero. Revisa la descripción del producto y compara varias opciones de la misma categoría antes de decidir."},
            {"q": "¿Es buena idea elegir un producto solo porque es viral?", "a": "Las tendencias cambian rápido y lo viral no siempre encaja con todo el mundo. Antes de decidir, valora si el producto resuelve una necesidad real para quien lo va a recibir."},
            {"q": "¿Cómo saber si un gadget es de calidad?", "a": "Lee la ficha del producto: materiales, especificaciones y condiciones del vendedor. Comparar varias opciones dentro de la misma categoría es la mejor forma de decidir con criterio."},
        ],
        "hero_image": None
    },
    {
        "slug": "imprescindibles-hogar-cocina",
        "title": "Los Reyes de la Cocina: Gadgets que te cambiarán la vida",
        "description": "Si te gusta cocinar (o comer), necesitas ver estos productos top ventas de Hogar y Cocina. Freidoras, robots y más.",
        "criteria": {
            "category": "Hogar y cocina"
        },
        "faq": [
            {"q": "¿Qué gadget de cocina regalar a alguien que le gusta cocinar?", "a": "Depende de lo que ya tenga y del espacio disponible en su cocina. Antes de comprar, pregunta o revisa su lista de deseos para no duplicar un aparato que ya posee."},
            {"q": "¿Cómo elegir entre los aparatos de cocina más populares?", "a": "Compara funciones, tamaño y descripción entre varias opciones. El más vendido no tiene por qué ser el más adecuado para la cocina y los hábitos de quien lo va a usar."},
            {"q": "¿Tienen sentido estos regalos para alguien que apenas cocina?", "a": "Sí, si eliges productos sencillos de uso ocasional en lugar de aparatos grandes. Valora con qué frecuencia crees que lo usará antes de decidirte."},
        ],
        "hero_image": None
    },
    {
        "slug": "belleza-autocuidado-spa",
        "title": "Rutina de Spa en casa: Belleza y Cuidado Personal",
        "description": "Mímate o mima a quien quieras. Cremas, secadores virales y maquillaje top ventas.",
        "criteria": {
            "category": "Belleza"
        },
        "faq": [
            {"q": "¿Qué regalar a alguien que cuida su piel?", "a": "Depende de su tipo de piel y de su rutina habitual. Si no los conoces, los accesorios y los productos de uso general suelen encajar mejor que la cosmética muy específica."},
            {"q": "¿Cómo acertar con cosmética si no sé sus gustos?", "a": "Evita los productos muy concretos y opta por artículos de autocuidado o accesorios neutros. Revisar su lista de deseos o preguntar a gente cercana reduce el riesgo de fallar."},
            {"q": "¿Un regalo de belleza sirve para cualquier edad?", "a": "No necesariamente: cada persona tiene necesidades y rutinas distintas. Valora los gustos y la etapa vital de quien lo recibe antes de elegir."},
        ],
        "hero_image": None
    },

    # --- FAMILIA ---
    {
        "slug": "juguetes-mas-vendidos",
        "title": "Los Juguetes que arrasan esta temporada",
        "description": "No esperes al último día. Estos son los favoritos de los niños (y no tan niños) de todas las edades.",
        "criteria": {
            "category": "Juguetes y juegos"
        },
        "faq": [
            {"q": "¿Cómo elegir un juguete según la edad?", "a": "Revisa la edad recomendada por el fabricante en la ficha del producto: es la referencia más fiable y suele aparecer bien indicada en cada juguete."},
            {"q": "¿Qué hago si no sé qué juguetes tiene ya el niño?", "a": "Consulta con sus padres o revisa una lista de deseos si existe. Es la forma más sencilla de evitar regalos repetidos y elegir algo que encaje con lo que ya le gusta."},
            {"q": "¿Los juguetes más vendidos valen para todas las edades?", "a": "No: cada juguete tiene un rango de edad recomendado. Compruébalo en la descripción antes de comprar, especialmente para los más pequeños."},
        ],
        "hero_image": None
    },
    {
        "slug": "regalos-bebe-padres",
        "title": "El Mundo del Bebé: Lo más útil para padres primerizos",
        "description": "Desde pañales hasta juguetes educativos. Todo lo necesario para los primeros meses.",
        "criteria": {
            "category": "Bebé"
        },
        "faq": [
            {"q": "¿Qué es lo más útil para regalar a padres primerizos?", "a": "Los artículos de cuidado diario suelen ser los que más uso dan en los primeros meses. Preguntar antes de comprar ayuda a evitar duplicados, porque muchos artículos se repiten en cada hogar con bebé."},
            {"q": "¿Cómo elegir un regalo de bebé seguro?", "a": "Revisa la edad recomendada y las indicaciones del fabricante en la ficha del producto, y sigue las instrucciones de uso y montaje que acompañan a cada artículo."},
            {"q": "¿Es mejor regalar algo para el bebé o para los padres?", "a": "Ambas opciones valen: lo que alivia el día a día de los padres acaba beneficiando también al bebé. Piensa en lo que la familia aún no tenga antes de decidir."},
        ],
        "hero_image": None
    },
    {
        "slug": "moda-tendencia-ropa",
        "title": "Moda y Accesorios que definen estilo",
        "description": "Renueva el armario con las prendas y complementos más buscados de la temporada.",
        "criteria": {
            "category": "Moda"
        },
        "faq": [
            {"q": "¿Cómo acertar con la talla al regalar ropa?", "a": "Sin conocer las medidas es fácil fallar. Si no puedes consultarlas con discreción, los complementos y accesorios, que no dependen de la talla, son una alternativa más segura."},
            {"q": "¿Qué regalar a alguien interesado en moda si no conozco sus gustos?", "a": "Opta por complementos neutros que combinen con casi cualquier estilo, o mira su lista de deseos si tiene. Evita las prendas muy personales si no estás seguro de su gusto."},
            {"q": "¿Las prendas de tendencia son buena opción de regalo?", "a": "Las tendencias cambian cada temporada. Antes de elegir, valora si la prenda encaja con el estilo habitual de quien la va a llevar, no solo con lo que está de moda ahora."},
        ],
        "hero_image": None
    }
]