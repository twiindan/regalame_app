import random
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from models import GroupMember, GroupExclusion

RECOMMENDED_GIFTS = [
    {
        "title": "Amazon Fire TV Stick 4K Select (última generación): comienza a reproducir contenido 4K en streaming, ve cientos de miles de películas y episodios de series, y accede a la TV gratuita y en directo",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61NG161RTaL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/fire-tv-stick-4k-select/dp/B0CN41GMDK/ref=zg_bs_g_electronics_d_sccl_1/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Amazon Basics - Paquete de 20 pilas alcalinas AA de alto rendimiento, 1,5 voltios, vida útil de 10 años",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81L6ZkEa2lL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Amazon-Basics-High-Performance-Alkaline-Batteries/dp/B00NTCH52W/ref=zg_bs_g_electronics_d_sccl_2/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "XIAOMI Redmi Watch 5 Active, Llamadas Bluetooth, Pantalla LCD de 2 Pulgadas, Monitor de frecuencia cardíaca, 140 Modos Deportivos, hasta 18 días de autonomía",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/51756XmmP7L._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Xiaomi-Bluetooth-frecuencia-Deportivos-autonom%C3%ADa/dp/B0DFZPR9Z4/ref=zg_bs_g_electronics_d_sccl_3/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Amazon Echo Spot (última generación) | Despertador inteligente con sonido de calidad y Alexa | Negro",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61jdAKkrAUL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/amazon-echo-spot-modelo-de-2024-despertador-inteligente-con-sonido-de-calidad-y-alexa-negro/dp/B0C2S2J7JP/ref=zg_bs_g_electronics_d_sccl_4/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Amazon Basics - Paquete de 40 pilas industriales alcalinas AA, 1,5 voltios, vida útil de 5 años",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81J5P4txVmL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Amazon-Basics-AA-Industrial-Batteries/dp/B07MLFBJG3/ref=zg_bs_g_electronics_d_sccl_5/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Amazon Fire TV Stick 4K Plus, compatible con Wi-Fi 6, Dolby Vision, Dolby Atmos y HDR10+",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71ZASIk7sTL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/fire-tv-stick-4k-plus/dp/B0F7ZFWVTC/ref=zg_bs_g_electronics_d_sccl_6/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Amazon Fire TV Stick HD (Última generación), con TV en directo gratuita, mando por voz Alexa, controles de Hogar digital y reproducción en streaming HD",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/51P-NqQI9EL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/fire-tv-stick-hd/dp/B0CQMWQDH4/ref=zg_bs_g_electronics_d_sccl_7/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Duracell CR2032 pilas de botón de litio 3 V (paquete de 8) - Hasta un 70 % extra duración - Tecnología Baby Secure - Para Apple AirTag, llaves remotas, dispositivos domésticos, deportivos y médicos",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81ii5FNe2qL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Duracell-Specialty-bot%C3%B3n-Litio-Paquete/dp/B06VW5BH2K/ref=zg_bs_g_electronics_d_sccl_8/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "GREENKINDER Camara Fotos Infantil Instantanea, 3,0 Pulgadas 14 MP Camara Fotos Infantil con Tarjeta de 32 GB y Papel de Impresión, HD 1080P Cámara Instantánea para Niños y Niñas 3 a 12 Años",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71AJ1CRZ0YL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/GREENKINDER-Infantil-Instantanea-Impresi%C3%B3n-Instant%C3%A1nea/dp/B0CYSZW34N/ref=zg_bs_g_electronics_d_sccl_9/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "XIAOMI TV F 32, 32 Pulgadas (81 cm), HD, Smart TV, Fire OS7, Control por Voz Alexa, Dolby Audio, DTS Virtual:X, DTS-HD, Compatible con Apple AirPlay, 2025",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/51rExJmgkIL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/XIAOMI-Pulgadas-Smart-Control-Virtual/dp/B0F4548TCQ/ref=zg_bs_g_electronics_d_sccl_10/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "XIAOMI Redmi Note 14 - Smartphone de 8+256GB, Pantalla de 6.67\" AMOLED FHD+ 120Hz, MediaTek Helio G99-Ultra, cámara de 108MP, TurboCharge 33W, 5500 mAh, Cargador no Incluido, Negro (Versión ES)",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81L4MbrSEBL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Xiaomi-Redmi-Note-14-TurboCharge/dp/B0DRCX34LQ/ref=zg_bs_g_electronics_d_sccl_11/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Instax Mini 12 Cámara instantánea, con autoexposición y Lente selfi incluida, Pastel Blue",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/51NfShWOj-L._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Instax-C%C3%A1mara-instant%C3%A1nea-autoexposici%C3%B3n-incluida/dp/B0BV37WZJL/ref=zg_bs_g_electronics_d_sccl_12/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Echo Pop (Última generación) | Altavoz inteligente Bluetooth con Alexa de sonido potente y compacto | Antracita",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/619NyX2WEPL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/echo-pop/dp/B09WX9XBKD/ref=zg_bs_g_electronics_d_sccl_13/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "XIAOMI Redmi Watch 5 Lite, Llamadas Bluetooth, Pantalla AMOLED de 1.96 Pulgadas, Monitor de frecuencia cardíaca, 150 Modos Deportivos, hasta 18 días de autonomía, Dorado",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/510jZSLgfPL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Llamadas-Bluetooth-frecuencia-Deportivos-autonom%C3%ADa/dp/B0DFHG6YZ7/ref=zg_bs_g_electronics_d_sccl_14/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Energizer Alkaline Power - Pilas AA (Paquete de 24) - 1,5V Baterías Alcalinas - para Aparatos Domésticos y Electrónicos - Embalaje 100% reciclable - 7 años de Vida útil [Exclusivo en Amazon]",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81C1DtWaFpL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Energizer-Alkaline-Power-Unidades-bater%C3%ADas/dp/B07L49RDJH/ref=zg_bs_g_electronics_d_sccl_15/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "AMAZFIT Active 2 Smart Watch 44mm, AI, Control por Voz, GPS & Mapas sin Coste, Batería de 10 Días, 160+ Modos Deportivos, Resistente al Agua 5 ATM, Compatible con Android & iPhone, Negro",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/610n84NfVaL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/AMAZFIT-Control-Deportivos-Resistente-Compatible/dp/B0DSPWKJW4/ref=zg_bs_g_electronics_d_sccl_16/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "[App Integrada] 2025 Upgraded Proyector Portátil 1920x1080P 4K Supote Videoproyector Dual Control TV WiFi 6 BT5.2 180° Rotation Compatible con HDMI/TV Stick/USB/Laptop, Blanco",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71j0fa86DnL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Integrada-Upgraded-Proyector-1920x1080P-Videoproyector/dp/B0DHG8XRVV/ref=zg_bs_g_electronics_d_sccl_17/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Reloj Inteligente Hombre Mujer con Llamadas Bluetooth, 1.95\" Smartwatch Hombre con Pulsómetro/Monitor de Sueño/Podómetro, 110+ Modos Deportivos Smart Watch, IP68 Pulsera Actividad para Android iOS",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/711Dr5O642L._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Inteligente-Bluetooth-Smartwatch-Puls%C3%B3metro-Deportivos/dp/B0FWRFKRY9/ref=zg_bs_g_electronics_d_sccl_18/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "[Apps integradas & 2025 Upgraded] Mini Proyector con WiFi 6 Bluetooth 5.4 Support 4K 1080P Auto Keystone 180° Rotable Proyector Portátil Compatibile con HDMI/TV Stick/Memory Stick/Laptop, Blanco",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71fuWbhH5pL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/integradas-Upgraded-Proyector-Bluetooth-Compatibile/dp/B0F4QWS84P/ref=zg_bs_g_electronics_d_sccl_19/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Mini Proyector 4K WiFi 6 BT5.2 Upgraded Proyector portátil Full HD Compatible con Teléfono/PC/TV/HDMI/PS5 Corrección Automática de Keystone Teatro en Casa Rotación de 180°[Aplicación Integrada]",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71U0ezDt70L._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Proyector-Compatible-Correcci%C3%B3n-Autom%C3%A1tica-Aplicaci%C3%B3n/dp/B0DG5LSJ3X/ref=zg_bs_g_electronics_d_sccl_20/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Echo Show 5 (Última generación) | Pantalla táctil inteligente con Alexa diseñada para controlar tus dispositivos de Hogar digital y más | Gris azulado",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/51fSgqA-IlL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/echo-show-5-3a-generacion/dp/B09B2R276Z/ref=zg_bs_g_electronics_d_sccl_21/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Amazon Basics paquete de 12 pilas AAA NiMH recargables, 800 mAh, 1,2 V, se recargan hasta 1000 veces, precargadas",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/8108hV04pVL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Amazon-Basics-Estanter%C3%ADa-ajustable-profundidad/dp/B007B9NXAC/ref=zg_bs_g_electronics_d_sccl_22/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "DURACELL Plus Pilas AA (Paquete de 24) – Pilas alcalinas 1,5 V – Hasta un 150 % de duración extra con activos POWER BOOST–Fiabilidad para dispositivos cotidianos–Envase con 0 % de plástico–MN1500",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81qqg-Z5nLL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/DURACELL-Plus-Pilas-Paquete-cotidianos-Envase/dp/B093C9B1HK/ref=zg_bs_g_electronics_d_sccl_23/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Reloj Inteligente Niño, Smartwatch Niños con 26 Juegos HD Cámara Alarma Reproductor de Música Podómetro Caloría Pantalla Táctil, Reloj Niño Juguetes Regalos para Niños Niñas 4-12",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61TDdKm243L._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/YEDASAH-Inteligente-Smartwatch-Reproductor-Pod%C3%B3metro/dp/B0BV24HVTM/ref=zg_bs_g_electronics_d_sccl_24/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Tapo C200P2 - Cámara IP WiFi 360° Cámara de Vigilancia FHD 1080p,Visión Nocturna, Notificaciones en Tiempo Real, Admite Tarjeta SD,Detección de Movimiento,Control Remoto,Compatible con Alexa",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71zqd4y1HRL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Tapo-C200P2-Vigilancia-Notificaciones-Movimiento/dp/B0CDCL38KZ/ref=zg_bs_g_electronics_d_sccl_25/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "CEGASA CR2032 Pack 2 Pilas Botón de Litio",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61zfPvIdFxL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/CEGASA-CR2032-Pilas-bot%C3%B3n-Litio/dp/B0748PZPRK/ref=zg_bs_g_electronics_d_sccl_26/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Amazon Basics - Paquete de 6 pilas de litio de botón CR2025 de larga duración, 3 voltios, sin mercurio",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71Mc-+9gkYL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Amazon-Basics-Paquete-duraci%C3%B3n-mercurio/dp/B08J4SX2QV/ref=zg_bs_g_electronics_d_sccl_27/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "HiMont Cámara de Fotos Instantáneas para Niños con Papel de Impresión y Tarjeta SD de 32G,20MP, Cámara de Fotos para Niños con Bolígrafos de Colores, Regalo para Niños de 3 a 14 años (Rosa)",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71t2KN+BG8L._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/Instant%C3%A1neas-Impresi%C3%B3n-Tarjeta-Bol%C3%ADgrafos-Colores/dp/B0B2SFNV57/ref=zg_bs_g_electronics_d_sccl_28/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "XIAOMI Redmi Watch 5, Reloj Inteligente: AMOLED 2.07\", 24 días batería, Llamadas Bluetooth, 150+ Modos Deportivos, Monitor cardíaco, sueño, 5ATM, GPS, Android/iOS, Negro",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61SzOmxnVDL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/XIAOMI-Redmi-Watch-Reloj-Inteligente/dp/B0DPX91VHZ/ref=zg_bs_g_electronics_d_sccl_29/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Nuevo Amazon Echo Dot Max: altavoz Alexa con sonido envolvente y controlador de Hogar digital integrado, Grafito",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71imtTuTXFL._AC_UL600_SR600,400_.jpg",
        "url": "https://www.amazon.es/echo-dot-max/dp/B0DKLFHZDH/ref=zg_bs_g_electronics_d_sccl_30/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Tapo Cámara de vigilancia WiFi interior 360° 1080p C200C, visión nocturna, notificaciones en tiempo real, detección de personas, seguimiento de movimiento, control remoto, compatible con Alexa",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/51+CVesFleL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Tapo-vigilancia-C200C-notificaciones-seguimiento/dp/B0D9MDV5L5/ref=zg_bs_g_electronics_d_sccl_31/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Ring Intercom Audio | Haz que tu interfono sea más inteligente | Transmisión de audio, llaves virtuales y acceso a distancia | Instalación por cuenta propia",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/51NZrF7+rnL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/ring-intercom-de-amazon-actualizacion-para-interfonos-apertura-en-remoto-compatible-con-alexa-comunicacion-bidireccional-se-requiere-un-interfono-compatible/dp/B0CKGQ5913/ref=zg_bs_g_electronics_d_sccl_32/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "[App Integrada] Mini Proyector Soporte 4K 1080P con 5G WiFi 6 y Bluetooth 5.4 2026 Upgraded Proyector Portátil con Corrección Trapezoidal Automática 270° Giratorio TV Stick/USB/PS5/Con Ratón,Blanco",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71YsMbPERfL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Proyector-Inal%C3%A1mbrico-Correcci%C3%B3n-Trapezoidal-Autom%C3%A1tica/dp/B0F29PX662/ref=zg_bs_g_electronics_d_sccl_33/524-6428720-3457932?psc=1",
        "price": "56,99 €"
    },
    {
        "title": "Tapo C210 - Cámara IP WiFi 360° Cámara de Vigilancia 2K (3MP),Visión Nocturna Admite Tarjeta SD hasta 512 GB, Detección y Seguimiento de Movimiento, Control Remoto, Compatible con Alexa",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81bWts7WhUL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Tapo-C210-Vigilancia-Seguimiento-Movimiento/dp/B095CLQ1PT/ref=zg_bs_g_electronics_d_sccl_34/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "XIAOMI Redmi Note 14 - Smartphone de 8+256GB, Pantalla de 6.67\" AMOLED FHD+ 120Hz, MediaTek Helio G99-Ultra, cámara de 108MP, TurboCharge 33W, 5500 mAh, Cargador no Incluido, Azul (Versión ES)",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81T7bJ+AFoL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Xiaomi-Redmi-Note-14-TurboCharge/dp/B0DRCWH9KH/ref=zg_bs_g_electronics_d_sccl_35/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "CREATE/Record Player Retro/Tocadiscos Retro Blanco Roto/Diseño Vintage, Bluetooth, USB, SD, MicroSD,Mp3, Sonido estéreo, 3 velocidades de reproducción, para Todo Tipo de vinilos",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61-0-j0P90L._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/CREATE-Record-Player-Compact-Reproductor/dp/B095X2PDF9/ref=zg_bs_g_electronics_d_sccl_36/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "AMAZFIT Bip 6 Smartwatch 46mm, Batería 14 días, AMOLED 1,97\", GPS con Mapas, IA, Llamadas Bluetooth, Seguimiento Salud y Sueño, 140+ Modos Deportivos, Resistencia al Agua 5ATM, Negro",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61wJFwhRaYL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Smartwatch-Bluetooth-Seguimiento-Deportivos-Resistencia/dp/B0DYP9R6YT/ref=zg_bs_g_electronics_d_sccl_37/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Reloj Inteligente Mujer con Alexa, 1,83\" Smartwatch con Llamadas, Notificaciones, 110+ Modos Deport, Esfera DIY, Pulsómetro/Podómetro/Monitor de Sueño, Impermeable IP68 Pulsera para Android iOS Rosa",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61bwUmKA2TL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Inteligente-Smartwatch-Notificaciones-Puls%C3%B3metro-Impermeable/dp/B0FVM5ZL77/ref=zg_bs_g_electronics_d_sccl_38/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Xiaomi Watch S4",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/615nODIvK2L._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Xiaomi-Bluetooth-Deportivo-Profesional-Frecuencia/dp/B0DSGLPKCC/ref=zg_bs_g_electronics_d_sccl_39/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "XIAOMI Redmi 15C - Smartphone de 4+256GB, Cámara Dual con IA de 50 MP, Pantalla inmersiva de 6,9\" 120 Hz, Potente procesador octacore, Carga rápida de 33W, Cargador no Incluido, Azul (Versión ES)",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61AlRQbmaZL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/XIAOMI-Redmi-15C-Smartphone-procesador/dp/B0FHBT612T/ref=zg_bs_g_electronics_d_sccl_40/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "CNAPXAIA Camara Fotos Infantil Instantanea, HD 1080P Video Cámara Instantánea con Tarjeta de 32GB y Papel de Impresión, 2,4 Pulgada Camara Fotos Infantil de Regalos Juguete de 3 a 12 Años (Azul)",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71l5bFTPN-L._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/CNAPXAIA-Infantil-Instantanea-Instant%C3%A1nea-Impresi%C3%B3n/dp/B0F4F84XCP/ref=zg_bs_g_electronics_d_sccl_41/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "SPC Titan - Teléfono Móvil de Tapa para Mayores, Botones y Teclas Grandes, Fácil de Usar, Timbre 100dB, Configuración Remota, Timbre y Notificaciones Inteligentes, 2 Memorias Directas, Color Negro",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/618ydwlXvHL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/SPC-Titan-notificaciones-Inteligentes-configuraci%C3%B3n/dp/B09P1RJ1P7/ref=zg_bs_g_electronics_d_sccl_42/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Warriors 10X Pilas CR2032 Pila 2032 3V Litio Botón, Embalaje a Prueba de niños, para Dispositivos Electrónicos, Llaves de Coche",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71wYVHBbbPL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Warriors-2032-CR2032-resistencia-seguridad/dp/B0BNVG3QHX/ref=zg_bs_g_electronics_d_sccl_43/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "TD Systems - Smart TV 32 Pulgadas HD, Television TDT HD, Android 14 GTV, Modelo 2025, Televisor con 3 años de garantía - PRIME32C21GLE",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71WE8VRgwfL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/TD-Systems-Television-Televisor-PRIME32C21GLE/dp/B0FNWT2HKL/ref=zg_bs_g_electronics_d_sccl_44/524-6428720-3457932?psc=1",
        "price": "119,89 €"
    },
    {
        "title": "Torre Regletas Enchufes, Regleta USB 8 Tomas de AC y 4 USB Enchufe Multiple, 2500W/10A,Regleta Enchufes Proteccion Sobretension, 2M Regreltas Vertical con Interruptor para Mesa, Oficia, Casa, Negro",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71a8yOLPauL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Regletas-Proteccion-Sobretension-Regreltas-Interruptor/dp/B0BXWTFNKD/ref=zg_bs_g_electronics_d_sccl_45/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Apple Watch SE 3 GPS con Caja de Aluminio en Blanco Estrella de 40 mm y Correa Deportiva Blanco Estrella-Talla S/M.Monitores de entreno y sueño,Monitor de frecuencia Cardiaca, Pantalla Siempre Activa",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61sNr8bUALL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Apple-Deportiva-Estrella-Talla-M-Monitores-frecuencia/dp/B0FQG1VG1C/ref=zg_bs_g_electronics_d_sccl_46/524-6428720-3457932?psc=1",
        "price": "239,00 €"
    },
    {
        "title": "XIAOMI Redmi Note 14 Pro - Smartphone de 8+256GB, Pantalla de 6.67\" AMOLED FHD+ 120Hz, MediaTek Helio G100-Ultra, cámara de 200MP, TurboCharge 45W, 5500 mAh, Cargador no Incluido, Negro (Versión ES)",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/81hL-1AnbVL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Xiaomi-Redmi-Note-14-Pro/dp/B0DPHMWDZN/ref=zg_bs_g_electronics_d_sccl_47/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Philips TAR1509 Radio Portátil FM/MW",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/61XIRvlaosL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Philips-TAR1509-Radio-Port%C3%A1til-FM/dp/B0D9HCGMMJ/ref=zg_bs_g_electronics_d_sccl_48/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "Tapo 2K(3MP) Cámara de vigilancia WiFi Interior 360° C21A, visión Nocturna, notificaciones en Tiempo Real, detección de Persona, Seguimiento de Movimiento, Control Remoto, Compatible con Alexa",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71b5HsExYtL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Tapo-vigilancia-C21A-notificaciones-Seguimiento/dp/B0DV59DL41/ref=zg_bs_g_electronics_d_sccl_49/524-6428720-3457932?psc=1",
        "price": "Consultar"
    },
    {
        "title": "4G Reloj Inteligente Niña, IP68 Impermeable Smartwatch Niñas con GPS y Llamadas, Doble Cámara, Videollamada, Chat de Voz, SOS, Modo Escuela, Linterna, Podómetro Reloj Inteligente Niñas y Niños Púrpura",
        "image": "https://images-eu.ssl-images-amazon.com/images/I/71VAr3ZhuyL._AC_UL300_SR300,200_.jpg",
        "url": "https://www.amazon.es/Inteligente-Impermeable-Smartwatch-Videollamada-Pod%C3%B3metro/dp/B0FQJJVSKP/ref=zg_bs_g_electronics_d_sccl_50/524-6428720-3457932?psc=1",
        "price": "Consultar"
    }
]

def get_recommended_gifts(limit=3):
    """
    Devuelve una lista aleatoria de regalos recomendados, inyectando el tag de afiliado.
    """
    selected = random.sample(RECOMMENDED_GIFTS, min(limit, len(RECOMMENDED_GIFTS)))
    tag = os.getenv("AMAZON_TAG", "tu_tag_defecto-21")
    
    # Procesar para añadir tag (creando copias para no mutar el global)
    processed = []
    for item in selected:
        new_item = item.copy()
        separator = "&" if "?" in new_item["url"] else "?"
        new_item["url"] += f"{separator}tag={tag}"
        processed.append(new_item)
        
    return processed

def get_all_recommendations():
    """
    Devuelve todas las recomendaciones con tag de afiliado inyectado.
    """
    tag = os.getenv("AMAZON_TAG", "tu_tag_defecto-21")
    processed = []
    for item in RECOMMENDED_GIFTS:
        new_item = item.copy()
        separator = "&" if "?" in new_item["url"] else "?"
        new_item["url"] += f"{separator}tag={tag}"
        processed.append(new_item)
    return processed

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