"""Category-aware pSEO content for the ``/ideas/{slug}`` landings, plus the
FAQ content for the ``/amigo-invisible`` organizer landing.

Everything here is factual: the generic guidance derives from the category
name and the per-category guidance in ``CATEGORY_CONTENT`` is topic-specific
but still neutral. No invented numbers, prices, ratings or superlative claims
anywhere — the strict editorial policy applies to every string in this module
and is enforced by tests. The blog cross-links reuse the curated posts already
declared in ``blog_config`` instead of duplicating titles.
"""

from blog_config import BLOG_POSTS
from catalog import slugify

# Price-focused posts used when a category has no dedicated curated post.
_PRICE_GUIDE_SLUGS = (
    "regalos-amigo-invisible-10-euros",
    "regalos-baratos-menos-20-euros",
)


def _generic_guide(name):
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


def _generic_faq(name):
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


# Topic-specific guide and FAQ content for the highest-traffic category
# landings. Keyed by category slug (``catalog.slugify`` of the display name,
# which is also the ``/ideas/{slug}`` URL segment). Each entry holds the
# display name plus a unique intro, tips and FAQ for the topic. Every string
# stays neutral factual guidance: no prices, ratings, figures, discounts or
# superlative claims — enforced by tests/test_category_content.py.
CATEGORY_CONTENT = {
    "electronica": {
        "name": "Electrónica",
        "meta": {
            "title": "Ideas de regalo en electrónica: cómo acertar | Regálame",
            "description": (
                "Ideas de regalo en electrónica para cumpleaños y amigo invisible: "
                "compara modelos y accesorios según los dispositivos que ya usa "
                "quien lo recibe."
            ),
        },
        "intro": (
            "Un regalo de electrónica acierta cuando encaja con los dispositivos "
            "que la otra persona ya utiliza. Antes de decidirte, comprueba la "
            "compatibilidad de conectores y sistemas, y distingue bien el modelo "
            "exacto: en esta categoría conviven versiones, generaciones y "
            "ediciones muy parecidas a simple vista."
        ),
        "tips": [
            "Comprueba la compatibilidad: conectores, sistema operativo y accesorios que ya tenga.",
            "Identifica el modelo exacto; conviven versiones, generaciones y ediciones muy similares.",
            "Revisa la garantía y los canales de soporte del fabricante antes de elegir marca.",
            "Valora los accesorios oficiales o certificados frente a los genéricos.",
            "Piensa en el uso previsto: autonomía, consumo y tamaño pesan según su día a día.",
        ],
        "faq": [
            {
                "q": "¿Qué conviene revisar antes de regalar un dispositivo electrónico?",
                "a": (
                    "Sobre todo la compatibilidad con lo que la otra persona ya "
                    "usa: conectores, sistema y accesorios. También el modelo "
                    "exacto, porque las versiones y ediciones se parecen mucho."
                ),
            },
            {
                "q": "¿Qué pasa si el modelo elegido no es compatible?",
                "a": (
                    "Es el fallo más habitual en este tipo de regalo. Consulta la "
                    "lista de deseos de quien lo recibe o pregúntale a alguien "
                    "cercano antes de comprar, y conserva la opción de cambio "
                    "como respaldo."
                ),
            },
            {
                "q": "¿Merece la pena incluir un accesorio junto al dispositivo?",
                "a": (
                    "Un accesorio compatible (funda, cable o soporte) puede "
                    "completar bien el regalo, siempre que corresponda al modelo "
                    "exacto y al uso que se le va a dar."
                ),
            },
        ],
    },
    "belleza": {
        "name": "Belleza",
        "meta": {
            "title": "Ideas de regalo en belleza y cuidado personal | Regálame",
            "description": (
                "Regalos de belleza y cuidado personal para cumpleaños o amigo "
                "invisible: sets, cosmética y detalles elegidos según el tipo de "
                "piel y su rutina."
            ),
        },
        "intro": (
            "En belleza, el acierto depende de la piel, el cabello y la rutina "
            "de quien lo recibe. Un mismo producto puede ser perfecto para una "
            "persona y no servir para otra, así que conviene pensar en el tipo "
            "de piel, en los tonos que ya usa y en si prefiere descubrir "
            "novedades o repetir con sus básicos."
        ),
        "tips": [
            "Piensa en el tipo de piel o de cabello: grasa, seca, mixta o sensible cambia por completo la elección.",
            "Revisa el periodo de validez tras la apertura y la fecha de caducidad del producto.",
            "Distingue entre paletas completas y productos individuales según el gusto de quien lo recibe.",
            "Ante la duda, elige tonos neutros o sets de muestras para probar sin comprometerse.",
            "Comprueba que el producto responda a su rutina actual en lugar de obligarla a cambiarla.",
        ],
        "faq": [
            {
                "q": "¿Cómo acertar con cosmética si no conozco su rutina?",
                "a": (
                    "Opta por productos versátiles y tonos neutros, o por sets "
                    "de muestras que permiten probar texturas y aromas sin "
                    "comprometerse a un formato completo."
                ),
            },
            {
                "q": "¿Qué significan los símbolos de caducidad en cosmética?",
                "a": (
                    "Los envases cosméticos indican el periodo de validez tras "
                    "la apertura mediante un símbolo de bote abierto; también "
                    "conviene mirar la fecha de caducidad cuando el producto "
                    "incluye filtros solares."
                ),
            },
            {
                "q": "¿Paleta completa o productos individuales?",
                "a": (
                    "La paleta funciona cuando la persona le gusta experimentar "
                    "con combinaciones; los productos individuales encajan "
                    "mejor cuando ya tiene una rutina definida y repite con sus "
                    "básicos."
                ),
            },
        ],
    },
    "hogar-y-cocina": {
        "name": "Hogar y cocina",
        "meta": {
            "title": "Qué regalar en hogar y cocina: selección 2026 | Regálame",
            "description": (
                "Qué regalar en hogar y cocina: objetos útiles para el día a día, "
                "regalos originales para estrenar casa o detalles prácticos para "
                "cumpleaños."
            ),
        },
        "intro": (
            "En hogar y cocina, el regalo útil es el que se integra en la casa "
            "y en la rutina de quien lo recibe. Antes de decidirte, piensa en "
            "el espacio disponible, en el estilo de la decoración y en la "
            "frecuencia de uso: los objetos de uso diario suelen dar más juego "
            "que los puramente decorativos."
        ),
        "tips": [
            "Ten en cuenta el espacio real disponible y, en muebles, las medidas del hueco.",
            "Revisa los materiales y el cuidado: apto para lavavajillas, horno o tipos de fogones.",
            "Distingue entre utilidad diaria y decoración según el estilo de su casa.",
            "Valora la calidad de los materiales cuando el objeto vaya a usarse a diario.",
            "Completa con un juego o set solo si sabes que encaja con lo que ya tiene.",
        ],
        "faq": [
            {
                "q": "¿Qué regalar en cocina si no sé qué utensilios tiene?",
                "a": (
                    "Los objetos de uso diario y versátiles son los que menos "
                    "riesgo tienen: textiles de cocina, moldes, organizadores "
                    "de despensa o accesorios que no dependen de otros "
                    "utensilios concretos."
                ),
            },
            {
                "q": "¿Cómo acertar con decoración sin conocer su estilo?",
                "a": (
                    "Elige piezas pequeñas, de materiales atemporales y colores "
                    "neutros, que se integran en casi cualquier decoración y "
                    "no condicionan el conjunto de la estancia."
                ),
            },
            {
                "q": "¿Qué revisar en un electrodoméstico pequeño de cocina?",
                "a": (
                    "Sus funciones concretas frente a las que se van a usar, el "
                    "espacio que ocupa, la limpieza de sus piezas y el ruido, "
                    "que suelen ser los criterios que deciden el uso diario."
                ),
            },
        ],
    },
    "moda": {
        "name": "Moda",
        "meta": {
            "title": "Regalar ropa y accesorios sin fallar en la talla | Regálame",
            "description": (
                "Ideas para regalar ropa y accesorios acertando con la talla: "
                "básicos atemporales para cumpleaños y regalos originales para "
                "quien cuida su estilo."
            ),
        },
        "intro": (
            "Regalar ropa o accesorios exige acertar con tallas, estilos y "
            "forma de vestir. Lo que funciona en una persona no encaja en otra: "
            "antes de decidirte, observa qué prenda o estilo usa a diario y "
            "recuerda que los básicos atemporales fallan mucho menos que las "
            "piezas de temporada."
        ),
        "tips": [
            "Averigua la talla con antelación; si es posible, usa como referencia una prenda que ya tenga.",
            "Piensa en su estilo habitual: los básicos atemporales fallan menos que las piezas de temporada.",
            "Revisa la composición y el cuidado del tejido antes de elegir.",
            "Comprueba la posibilidad de cambio de talla por si el ajuste no es el esperado.",
            "Ante la duda, elige colores neutros que combinen con lo que ya usa.",
        ],
        "faq": [
            {
                "q": "¿Cómo acertar con la talla al regalar ropa?",
                "a": (
                    "Lo más fiable es apoyarse en una prenda que la persona ya "
                    "tenga, revisar la guía de tallas del fabricante y contar "
                    "con la posibilidad de cambio de talla por si el ajuste no "
                    "es el esperado."
                ),
            },
            {
                "q": "¿Qué prendas son un regalo seguro?",
                "a": (
                    "Los básicos atemporales, como bufandas, gorros, camisetas "
                    "de buena confección o accesorios de cuero, funcionan mejor "
                    "que las piezas de temporada, que dependen más del gusto "
                    "personal."
                ),
            },
            {
                "q": "¿Cómo se cuida una prenda para que dure?",
                "a": (
                    "Revisa la etiqueta de composición y las instrucciones de "
                    "lavado; respetarlas es la referencia principal para que la "
                    "prenda se mantenga en buen estado."
                ),
            },
        ],
    },
    "juguetes-y-juegos": {
        "name": "Juguetes y juegos",
        "meta": {
            "title": "Regalos de juguetes y juegos por edad e interés | Regálame",
            "description": (
                "Regalos de juguetes y juegos elegidos por edad e intereses: "
                "juegos de mesa para el amigo invisible y ideas de cumpleaños que "
                "se usan de verdad."
            ),
        },
        "intro": (
            "En juguetes, la clave está en la edad y los intereses de quien va "
            "a jugar. La edad recomendada por el fabricante no es un detalle "
            "menor: indica seguridad y complejidad. Un juguete que se ajusta a "
            "su etapa y a lo que le divierte se usa mucho más que uno llamativo "
            "pero ajeno a sus gustos."
        ),
        "tips": [
            "Respeta la edad recomendada por el fabricante: marca seguridad y complejidad.",
            "Con niños pequeños, comprueba que no incluya piezas pequeñas susceptibles de tragarse.",
            "Aprovecha sus intereses actuales: construcción, ciencias, dibujo, vehículos o dramatización.",
            "En juegos de mesa, revisa el número de jugadores y la duración de la partida.",
            "Ten en cuenta el espacio de guardado y recogida que exige el juguete.",
        ],
        "faq": [
            {
                "q": "¿Cómo se elige un juguete según la edad?",
                "a": (
                    "La edad recomendada impresa por el fabricante es la "
                    "referencia: recoge criterios de seguridad y de complejidad. "
                    "A partir de ahí, los intereses del niño o la niña deciden "
                    "entre construcción, manualidades, ciencias o juego "
                    "simbólico."
                ),
            },
            {
                "q": "¿Qué revisar antes de regalar un juego de mesa?",
                "a": (
                    "El número de jugadores, la duración de la partida y la "
                    "edad recomendada; conviene que encaje con el grupo con el "
                    "que se va a jugar y con su experiencia previa en juegos de "
                    "mesa."
                ),
            },
            {
                "q": "¿Es buena idea un juguete educativo?",
                "a": (
                    "Sí, siempre que responda a los intereses de quien lo "
                    "recibe; un juguete que conecta con lo que ya le divierte "
                    "consigue que el aprendizaje llegue como consecuencia del "
                    "juego."
                ),
            },
        ],
    },
    "deportes-y-aire-libre": {
        "name": "Deportes y aire libre",
        "meta": {
            "title": "Regalos para deportistas según su disciplina | Regálame",
            "description": (
                "Regalos para deportistas según su disciplina y nivel: material de "
                "running, gimnasio o montaña como regalo de cumpleaños o un detalle "
                "original."
            ),
        },
        "intro": (
            "En deporte, el regalo útil depende de la disciplina concreta y del "
            "nivel de quien lo practica: no es lo mismo equipar a alguien que "
            "empieza que a alguien que entrena a diario. Identificar la "
            "actividad, la frecuencia y las condiciones de uso evita regalar "
            "material que queda guardado en un cajón."
        ),
        "tips": [
            "Identifica el deporte concreto; el material de una disciplina rara vez sirve para otra.",
            "Distingue entre quien empieza y quien entrena a diario: cambian las prioridades.",
            "En ropa técnica, la talla y el ajuste importan tanto como en el día a día.",
            "Piensa en las condiciones de uso: interior o exterior, clima y transporte del equipo.",
            "Valora los consumibles y repuestos de lo que ya usa: casi siempre encajan.",
        ],
        "faq": [
            {
                "q": "¿Qué regalar a alguien que empieza un deporte?",
                "a": (
                    "Lo básico de su disciplina: ropa adecuada, protección y "
                    "algún accesorio de entrada. Sin sobre-equipar, porque sus "
                    "preferencias concretas se definen con la práctica."
                ),
            },
            {
                "q": "¿Cómo se elige la talla de ropa técnica?",
                "a": (
                    "Igual que en el resto de ropa, con la referencia de una "
                    "prenda que ya tenga y la guía del fabricante; en prendas "
                    "de compresión o capas interiores, el ajuste es parte de la "
                    "función."
                ),
            },
            {
                "q": "¿Los accesorios de recambio son buena opción?",
                "a": (
                    "Suelen acertar: consumibles y repuestos de lo que ya usa "
                    "(grips, fundas, botellas, pilas) no dependen del gusto y "
                    "siempre se aprovechan."
                ),
            },
        ],
    },
    "libros": {
        "name": "Libros",
        "meta": {
            "title": "Regalar libros: cómo elegir el título adecuado | Regálame",
            "description": (
                "Ideas para regalar libros acertando con géneros y formatos: "
                "novedades, ediciones cuidadas y clásicos para cumpleaños, amigo "
                "invisible o Navidad."
            ),
        },
        "intro": (
            "Un libro es un regalo muy personal: acierta cuando conecta con los "
            "géneros y autores que ya se leen. Si conoces sus gustos, una "
            "novedad de su autor favorito rara vez falla; si no los conoces, "
            "las ediciones cuidadas y los clásicos con buen criterio de género "
            "son el camino con menos riesgo."
        ),
        "tips": [
            "Apóyate en los géneros y autores que ya lee, o en su lista de deseos.",
            "Decide el formato: tapa dura, bolsillo, edición ilustrada, digital o audiolibro.",
            "Comprueba qué títulos tiene ya, para no duplicar dentro de una saga.",
            "Las ediciones cuidadas o ilustradas funcionan incluso con lecturas ya conocidas.",
            "Si lee poco, una obra breve o muy recomendada de su temática de interés es mejor puerta de entrada.",
        ],
        "faq": [
            {
                "q": "¿Cómo elegir un libro si no conozco sus gustos?",
                "a": (
                    "Pregunta a personas cercanas, revisa su lista de deseos o "
                    "apóyate en su película o serie favorita: hay adaptaciones "
                    "y géneros que suelen corresponder. Una edición cuidada de "
                    "un clásico acorde a sus intereses es la opción con menos "
                    "riesgo."
                ),
            },
            {
                "q": "¿Qué formato conviene más?",
                "a": (
                    "Depende del hábito: tapa dura o edición ilustrada para "
                    "coleccionar, bolsillo para leer con comodidad, y digital o "
                    "audiolibro para quien viaja o prefiere leer en el móvil o "
                    "con auriculares."
                ),
            },
            {
                "q": "¿Es mejor un libro nuevo o una edición especial?",
                "a": (
                    "Si la persona ya tiene el título, una edición especial "
                    "(ilustrada, anotada o de coleccionista) le da una segunda "
                    "vida al regalo sin duplicar la lectura."
                ),
            },
        ],
    },
    "alimentacion-y-bebidas": {
        "name": "Alimentación y bebidas",
        "meta": {
            "title": "Regalos de comida y bebida con identidad | Regálame",
            "description": (
                "Regalos de comida y bebida con identidad: cestas, especialidades "
                "regionales y detalles originales para cumpleaños, cenas de "
                "empresa o amigo invisible."
            ),
        },
        "intro": (
            "La comida y la bebida son regalos de consumo inmediato, así que el "
            "acierto depende de los gustos y, sobre todo, de las alergias, "
            "intolerancias y dietas de quien lo recibe. Bien elegido, es de lo "
            "poco que nunca sobra; mal elegido, es lo primero que se queda en "
            "la despensa."
        ),
        "tips": [
            "Averigua alergias, intolerancias y dietas antes de elegir cualquier producto.",
            "Revisa la fecha de caducidad o consumo preferente y el plazo en que se va a consumir.",
            "Las especialidades de una zona o denominación funcionan bien como regalo con identidad.",
            "Distingue entre cestas surtidas y un producto concreto: la segunda suele sentirse más personal.",
            "Ten en cuenta la conservación y el transporte si el producto es perecedero.",
        ],
        "faq": [
            {
                "q": "¿Qué revisar antes de regalar comida o bebida?",
                "a": (
                    "Alergias, intolerancias y dieta de quien lo recibe; "
                    "después, la fecha de caducidad o consumo preferente y las "
                    "condiciones de conservación, sobre todo en productos "
                    "perecederos."
                ),
            },
            {
                "q": "¿Cesta surtida o producto concreto?",
                "a": (
                    "Una cesta reparte el riesgo entre productos variados; un "
                    "producto concreto de calidad, elegido según sus gustos, se "
                    "siente más personal. La elección depende de cuánto sepas "
                    "de lo que le gusta."
                ),
            },
            {
                "q": "¿Cómo elegir un producto con identidad?",
                "a": (
                    "Las especialidades regionales y las denominaciones de "
                    "origen son una buena referencia: cuentan una historia y "
                    "suelen ser productos que la persona no compra a diario "
                    "para sí misma."
                ),
            },
        ],
    },
    "videojuegos": {
        "name": "Videojuegos",
        "meta": {
            "title": "Regalos gamer según su consola o su PC | Regálame",
            "description": (
                "Regalos de videojuegos sin fallos: elige según su consola u "
                "ordenador, con juegos, tarjetas digitales y accesorios para "
                "cumpleaños o amigo invisible."
            ),
        },
        "intro": (
            "En videojuegos, el regalo depende sobre todo de la plataforma y "
            "del tipo de juego que disfruta la otra persona. Un juego de la "
            "consola equivocada no sirve de nada, y la clasificación por edad "
            "es una referencia que conviene respetar tanto como la compatibilidad."
        ),
        "tips": [
            "Identifica la plataforma exacta: consola y generación, ordenador o dispositivo móvil.",
            "Respecta la clasificación por edades del juego, igual que en el cine.",
            "Piensa en su tipo favorito: aventura, deportes, estrategia, cooperativo o competitivo.",
            "Los periféricos y accesorios deben corresponder a su plataforma y modelo concretos.",
            "Las tarjetas digitales y suscripciones son opción flexible si no conoces su biblioteca.",
        ],
        "faq": [
            {
                "q": "¿Cómo saber qué plataforma tiene la otra persona?",
                "a": (
                    "Pregunta a gente de su entorno o revisa su lista de "
                    "deseos; la plataforma y su generación son la primera "
                    "cuestión, porque un juego o accesorio de otra plataforma "
                    "no es compatible."
                ),
            },
            {
                "q": "¿Qué significa la clasificación por edades?",
                "a": (
                    "Es el sistema que indica la idoneidad del contenido según "
                    "la edad, similar al del cine. Conviene comprobarla "
                    "siempre, en especial cuando el regalo es para menores."
                ),
            },
            {
                "q": "¿Tarjeta digital o juego físico?",
                "a": (
                    "La tarjeta digital o la suscripción evitan fallar con un "
                    "título concreto y dejan elegir a quien lo recibe; el juego "
                    "físico funciona bien cuando sabes exactamente qué título "
                    "busca."
                ),
            },
        ],
    },
    "productos-para-mascotas": {
        "name": "Productos para mascotas",
        "meta": {
            "title": "Regalos para perros, gatos y sus dueños | Regálame",
            "description": (
                "Regalos para mascotas según especie y tamaño: juguetes, camas y "
                "accesorios para perros y gatos, un detalle original o un regalo "
                "de cumpleaños."
            ),
        },
        "intro": (
            "Regalar a una mascota es, en la práctica, regalar a su dueño: el "
            "acierto depende de la especie, el tamaño y la etapa de vida del "
            "animal. Un accesorio bien elegido se nota en el día a día; uno "
            "mal dimensionado o inadecuado para la especie termina sin usarse."
        ),
        "tips": [
            "Confirma especie, raza y tamaño: los accesorios se dimensionan a la medida del animal.",
            "Ten en cuenta la etapa de vida: cachorro o gatito, adulto o senior cambian las necesidades.",
            "En juguetes, elige materiales resistentes al uso que le da esa mascota en concreto.",
            "Para salud e higiene, prefieres productos de uso veterinario reconocido.",
            "Arnés, cama o transportín exigen medidas correctas: compáralas antes de decidir.",
        ],
        "faq": [
            {
                "q": "¿Cómo elegir un juguete para perro o gato?",
                "a": (
                    "Según la especie, el tamaño y la forma de jugar del "
                    "animal: la resistencia del material y la seguridad (sin "
                    "piezas desprendibles) pesan más que el color o el ruido "
                    "del juguete."
                ),
            },
            {
                "q": "¿Qué accesorios dependen de la talla de la mascota?",
                "a": (
                    "Casi todos los de contacto directo: arneses, collares, "
                    "camas, transportines o ropa. Conviene medir o guiarse por "
                    "el peso del animal antes de elegir la talla."
                ),
            },
            {
                "q": "¿Es buena idea regalar comida o golosinas?",
                "a": (
                    "Solo con la conformidad del dueño: la alimentación "
                    "responde a indicaciones veterinarias, edad y posibles "
                    "alergias, y no todos los cambios de dieta le sientan bien "
                    "al animal."
                ),
            },
        ],
    },
    "bebe": {
        "name": "Bebé",
        "meta": {
            "title": "Qué regalar a un bebé según su etapa | Regálame",
            "description": (
                "Qué regalar a un bebé según su etapa de desarrollo: textil, "
                "higiene y productos seguros para recién nacidos, o un detalle "
                "práctico para los padres."
            ),
        },
        "intro": (
            "En regalos de bebé, la seguridad manda: materiales certificados, "
            "productos adaptados a la edad y diseño pensado para los más "
            "pequeños. Quien mejor sabe lo que falta suele ser la familia, así "
            "que la lista de deseos es aquí más útil que en casi cualquier otra "
            "categoría."
        ),
        "tips": [
            "Prioriza la seguridad: certificados, materiales sin piezas pequeñas y edad recomendada.",
            "Ajusta el regalo a la etapa de desarrollo, no solo a la edad en meses.",
            "Valora los productos que crecen con el bebé y se adaptan a varias etapas.",
            "Piensa también en los padres: confort y praticidad del día a día se agradecen.",
            "En ropa, guiúate por la talla por meses y la estación en que la va a usar.",
        ],
        "faq": [
            {
                "q": "¿Qué hace un regalo de bebé seguro?",
                "a": (
                    "Los materiales certificados, las piezas de tamaño seguro, "
                    "los bordes redondeados y el respeto de la edad recomendada "
                    "del fabricante; la normativa específica de productos "
                    "infantiles es la referencia."
                ),
            },
            {
                "q": "¿Cómo acertar con la talla de la ropa?",
                "a": (
                    "La ropa de bebé se talla por meses, pero el crecimiento es "
                    "individual: elegir una talla algo por encima y pensar en "
                    "la estación en que la usará suele funcionar."
                ),
            },
            {
                "q": "¿Qué regalar si los padres no han pedido nada?",
                "a": (
                    "Básicos de uso diario (textil, higiene, alimentación) o "
                    "algo para los propios padres, que es una parte del regalo "
                    "que se suele olvidar y siempre se agradece."
                ),
            },
        ],
    },
    "informatica": {
        "name": "Informática",
        "meta": {
            "title": "Regalos de informática: accesorios útiles | Regálame",
            "description": (
                "Regalos de informática útiles para el trabajo y el estudio: "
                "teclados, ratones y accesorios compatibles, ideas para "
                "cumpleaños o amigo invisible."
            ),
        },
        "intro": (
            "En informática, el regalo útil sale de entender para qué sirve el "
            "equipo: trabajo, estudio, creación o juego. La compatibilidad con "
            "el sistema y los puertos existentes decide si el accesorio se usa "
            "o se olvida, y las versiones de software tienen licencias que "
            "conviene distinguir."
        ),
        "tips": [
            "Define el uso principal: ofimática, estudio, diseño, programación o juego.",
            "Comprueba la compatibilidad con el sistema operativo y los puertos del equipo.",
            "Los periféricos ergonómicos son un acierto para quien pasa muchas horas frente a la pantalla.",
            "Distingue las versiones y licencias del software antes de elegir.",
            "En equipos, revisa el estado del almacenamiento y la batería si no son nuevos.",
        ],
        "faq": [
            {
                "q": "¿Qué conviene revisar antes de regalar un accesorio informático?",
                "a": (
                    "La compatibilidad con el equipo receptor: sistema "
                    "operativo, puertos y conectores. Es el criterio que decide "
                    "si el accesorio se usa desde el primer día o se queda en "
                    "un cajón."
                ),
            },
            {
                "q": "¿Qué periférico es un regalo acertado para quien trabaja con el ordenador?",
                "a": (
                    "Los ergonómicos: teclado, ratón o soporte de pantalla "
                    "mejoran la comodidad de las largas jornadas y no dependen "
                    "de la tarea concreta."
                ),
            },
            {
                "q": "¿Qué revisar en el software antes de regalarlo?",
                "a": (
                    "La versión y el tipo de licencia, porque cada una cubre "
                    "usos distintos; conviene confirmar que encaja con el "
                    "equipo y con la actividad de quien lo va a usar."
                ),
            },
        ],
    },
}


def _content_for(name):
    """Return the ``CATEGORY_CONTENT`` entry matching ``name`` (or slug)."""
    if not name:
        return None
    key = slugify(name)
    return CATEGORY_CONTENT.get(key)


def category_guide(name):
    """Return a short "how to choose" block for ``name``.

    The result is ``{"title", "intro", "tips"}``. Categories with an entry in
    ``CATEGORY_CONTENT`` get topic-specific text; the rest fall back to the
    generic, factual guidance. No prices, ratings or "best" claims anywhere.
    """
    entry = _content_for(name)
    if entry is None:
        return _generic_guide(name)
    return {
        "title": f"Cómo elegir un regalo de {entry['name']}",
        "intro": entry["intro"],
        "tips": list(entry["tips"]),
    }


def category_meta(name):
    """Return ``{"title", "description"}`` SEO meta for ``name``.

    Only categories whose ``CATEGORY_CONTENT`` entry declares a ``meta``
    field return specific copy; everything else (unknown category, entry
    without ``meta``) returns ``None`` so the template keeps the generic
    title/description pattern. Titles stay within 70 chars and descriptions
    within 160 (enforced by tests/test_category_meta.py).
    """
    entry = _content_for(name)
    if entry is None:
        return None
    meta = entry.get("meta")
    if not meta:
        return None
    return {"title": meta["title"], "description": meta["description"]}


def category_faq(name):
    """Return 2-3 neutral ``{"q", "a"}`` pairs for the ``name`` category.

    Categories with a ``CATEGORY_CONTENT`` entry get topic-specific questions;
    the rest fall back to the generic neutral answers.
    """
    entry = _content_for(name)
    if entry is None:
        return _generic_faq(name)
    return [dict(item) for item in entry["faq"]]


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
