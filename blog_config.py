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
        "hero_image": None
    },
    {
        "slug": "como-organizar-amigo-invisible",
        "title": "Cómo organizar un amigo invisible paso a paso",
        "description": "Los pasos concretos para montar el intercambio: fijar presupuesto y fecha, invitar al grupo, hacer el sorteo y consultar las listas de deseos.",
        "organizer_aside": True,
        "guide": [
            {"heading": "Cómo funciona el amigo invisible", "paragraphs": [
                "El amigo invisible (o amigo secreto) es un intercambio en el que cada participante regala a una sola persona asignada al azar, sin que esta sepa quién le regaló. El sorteo se hace una vez y cada quien prepara su regalo para la fecha acordada.",
                "En Regálame el sorteo impide que alguien se asigne a sí mismo y permite configurar vetos, útiles cuando dos personas no deberían regalarse entre sí.",
            ]},
            {"heading": "Antes del sorteo: presupuesto, fecha y grupo", "paragraphs": [
                "Acordad primero el presupuesto máximo: es la regla que evita situaciones incómodas. Después fijad la fecha del intercambio y dejad margen para que cada quien piense su regalo.",
                "Cread el grupo en Regálame, indicad nombre, fecha y presupuesto, y compartid el enlace de invitación por WhatsApp o email. Cada participante se une con su cuenta.",
            ]},
            {"heading": "El día del intercambio", "paragraphs": [
                "Antes de abrir los regalos, cada participante puede repasar la lista de deseos de su asignado: es la referencia más fiable para acertar. Los resultados del sorteo se consultan dentro de la aplicación, nunca se comparten por chat.",
            ]},
        ],
        "hero_image": None,
    },
    {
        "slug": "reglas-del-amigo-invisible",
        "title": "Reglas del amigo invisible: cómo se juega",
        "description": "Las reglas básicas del amigo invisible, las variantes más habituales y cómo evitar los malentendidos típicos del intercambio.",
        "organizer_aside": True,
        "guide": [
            {"heading": "Las reglas básicas", "paragraphs": [
                "Presupuesto pactado por todos y respeto estricto del secreto: nadie revela a quién le toca regalar hasta el día del intercambio. El sorteo debe ser aleatorio y excluir la autoasignación.",
                "Quien no pueda participar debe decirlo antes del sorteo: después suele implicar repetir todo el proceso.",
            ]},
            {"heading": "Variantes habituales", "paragraphs": [
                "Vetos (parejas o enemistades que no deben tocarse), temáticas (productos hechos a mano, libros, locales) o límites de precio por tramos. En grupos grandes, un intervalo de entrega más ancho evita prisas.",
                "La lista de deseos opcional es la variante más útil: el regalo sigue siendo sorpresa, pero acierta. En Regálame cada participante puede publicar la suya.",
            ]},
        ],
        "hero_image": None,
    },
    {
        "slug": "frases-para-el-amigo-invisible",
        "title": "Frases para el amigo invisible: para el grupo, el papelito y el regalo",
        "description": "Frases cortas para invitar al grupo, para el papel del sorteo y para acompañar el regalo, con tono directo y sin cursilerías.",
        "organizer_aside": True,
        "guide": [
            {"heading": "Para invitar al grupo", "paragraphs": [
                "\"Nos falta la mejor parte del plan: el amigo invisible. Entra en el grupo y elige tu lista de deseos.\" · \"Presupuesto ajustado, sorpresas aseguradas: apúntate al intercambio.\"",
                "\"Si el año pasado te tocó el regalo aburrido, este año toca mejorar: apúntate y pon ideas en tu lista.\"",
            ]},
            {"heading": "Para el papelito o la dedicatoria", "paragraphs": [
                "\"De alguien invisible con mucho gusto.\" · \"Elegido al azar, acertado de verdad.\" · \"El secreto me lo llevo, el regalo te lo llevo a ti.\"",
                "\"Que no se nota quién fue, pero que se nota que acerté.\" · \"Regalo con vuestra lista por delante: no fallé.\"",
            ]},
            {"heading": "Con humor (sin pasarse)", "paragraphs": [
                "\"Tu amigo invisible te conoce mejor de lo que crees... o tuvimos suerte.\" · \"He respetado el presupuesto. El gusto no tenía límite.\"",
                "\"Del anonimato más elegante: ni un pista, ni un fallo.\"",
            ]},
        ],
        "hero_image": None,
    },

    # --- PRECIO / PRESUPUESTO ---
    {
        "slug": "regalos-amigo-invisible-10-euros",
        "title": "Top 15 Regalos de Amigo Invisible por menos de 10€",
        "description": "El límite de precio más difícil. Hemos encontrado las joyas ocultas de Amazon para quedar genial sin gastar casi nada.",
        "criteria": {
            "max_price": 10.0
        },
        "organizer_aside": True,
        "hero_image": None 
    },
    {
        "slug": "regalos-baratos-menos-20-euros",
        "title": "20 Regalos por menos de 20€ que parecen de lujo",
        "description": "¿Presupuesto ajustado? Aquí tienes la selección definitiva de detalles económicos que sorprenderán a cualquiera.",
        "criteria": {
            "max_price": 20.0
        },
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
        "hero_image": None
    },
    {
        "slug": "regalos-fitness-deporte",
        "title": "Para los locos del deporte: Equípate al mejor precio",
        "description": "¿Propósito de año nuevo? Ropa técnica, accesorios de gym y gadgets para mantenerte en forma.",
        "criteria": {
            "category": "Deportes y aire libre"
        },
        "hero_image": None
    },
    {
        "slug": "mejores-libros-bestsellers",
        "title": "Los Libros más leídos del momento",
        "description": "Desde novelas adictivas hasta no ficción transformadora. Un libro siempre es el regalo perfecto.",
        "criteria": {
            "category": "Libros"
        },
        "hero_image": None
    },

    # --- ESTILO DE VIDA Y HOGAR ---
    {
        "slug": "top-tendencias-tecnologia-2025",
        "title": "Lo más viral en Electrónica y Gadgets",
        "description": "Desde auriculares hasta domótica. Descubre la tecnología que está marcando tendencia este año.",
        "criteria": {
            "category": "Electrónica" 
        },
        "hero_image": None
    },
    {
        "slug": "imprescindibles-hogar-cocina",
        "title": "Los Reyes de la Cocina: Gadgets que te cambiarán la vida",
        "description": "Si te gusta cocinar (o comer), necesitas ver estos productos top ventas de Hogar y Cocina. Freidoras, robots y más.",
        "criteria": {
            "category": "Hogar y cocina"
        },
        "hero_image": None
    },
    {
        "slug": "belleza-autocuidado-spa",
        "title": "Rutina de Spa en casa: Belleza y Cuidado Personal",
        "description": "Mímate o mima a quien quieras. Cremas, secadores virales y maquillaje top ventas.",
        "criteria": {
            "category": "Belleza"
        },
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
        "hero_image": None
    },
    {
        "slug": "regalos-bebe-padres",
        "title": "El Mundo del Bebé: Lo más útil para padres primerizos",
        "description": "Desde pañales hasta juguetes educativos. Todo lo necesario para los primeros meses.",
        "criteria": {
            "category": "Bebé"
        },
        "hero_image": None
    },
    {
        "slug": "moda-tendencia-ropa",
        "title": "Moda y Accesorios que definen estilo",
        "description": "Renueva el armario con las prendas y complementos más buscados de la temporada.",
        "criteria": {
            "category": "Moda"
        },
        "hero_image": None
    }
]