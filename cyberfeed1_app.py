
import re
import html
import threading
from datetime import timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests
import streamlit as st

import argostranslate.package
import argostranslate.translate


# ==================================================
# CONFIGURACIÓN
# ==================================================

st.set_page_config(
    page_title="CyberFeed | Ciberseguridad",
    page_icon="🛡️",
    layout="wide",
)

FUENTES = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackerNews",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
}

CATEGORIAS = [
    "Todas",
    "Vulnerabilidades",
    "Malware",
    "Hacking",
    "Inteligencia artificial",
    "General",
]

# Evita intentar instalar el modelo varias veces simultáneamente.
argos_lock = threading.Lock()


# ==================================================
# ESTILOS
# ==================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #07111f;
        color: #e8f0fb;
    }

    [data-testid="stHeader"] {
        background: rgba(7,17,31,.95);
    }

    [data-testid="stSidebar"] {
        background-color: #0b1829;
    }

    h1, h2, h3 {
        color: #f2f7ff;
    }

    .cf-subtitle {
        color: #93a9c4;
        font-size: 1rem;
        margin-top: -10px;
        margin-bottom: 24px;
    }

    .cf-tag {
        display: inline-block;
        padding: 4px 9px;
        border-radius: 6px;
        margin-bottom: 8px;
        color: #62e6ce;
        background: #10312f;
        font-size: .78rem;
        font-weight: 600;
    }

    .cf-source {
        color: #91a6bf;
        font-size: .82rem;
        margin-bottom: 8px;
    }

    .cf-title {
        color: #f2f7ff;
        font-size: 1.18rem;
        line-height: 1.5;
        font-weight: 700;
        margin-bottom: 9px;
    }

    .cf-summary {
        color: #c1cde0;
        font-size: .96rem;
        line-height: 1.65;
    }

    .cf-date {
        color: #7f96b2;
        font-size: .8rem;
        margin-top: 10px;
    }

    a {
        color: #57dcca !important;
    }

    div[data-testid="stMetric"] {
        background: #0d1b2d;
        padding: 14px;
        border: 1px solid #1b3047;
        border-radius: 12px;
    }

    hr {
        border-color: #1b3047;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# INSTALAR Y PREPARAR ARGOS
# ==================================================

@st.cache_resource(show_spinner=False)
def preparar_traductor():
    with argos_lock:
        # Comprobar si el modelo inglés-español ya está instalado.
        idiomas = argostranslate.translate.get_installed_languages()

        ingles = next(
            (idioma for idioma in idiomas if idioma.code == "en"),
            None,
        )

        espanol = next(
            (idioma for idioma in idiomas if idioma.code == "es"),
            None,
        )

        if ingles and espanol:
            traduccion = ingles.get_translation(espanol)
            if traduccion:
                return traduccion

        # Descargar el índice oficial de modelos.
        argostranslate.package.update_package_index()

        paquetes = argostranslate.package.get_available_packages()

        paquete = next(
            (
                p for p in paquetes
                if p.from_code == "en" and p.to_code == "es"
            ),
            None,
        )

        if paquete is None:
            raise RuntimeError(
                "No se encontró el modelo de traducción inglés-español."
            )

        archivo_modelo = paquete.download()
        argostranslate.package.install_from_path(archivo_modelo)

        idiomas = argostranslate.translate.get_installed_languages()

        ingles = next(
            (idioma for idioma in idiomas if idioma.code == "en"),
            None,
        )

        espanol = next(
            (idioma for idioma in idiomas if idioma.code == "es"),
            None,
        )

        if not ingles or not espanol:
            raise RuntimeError(
                "El modelo se descargó, pero no se pudo cargar."
            )

        traduccion = ingles.get_translation(espanol)

        if traduccion is None:
            raise RuntimeError(
                "No se pudo preparar la traducción inglés-español."
            )

        return traduccion


# ==================================================
# TRADUCCIÓN LOCAL
# ==================================================

@st.cache_data(ttl=86400, show_spinner=False)
def traducir_espanol(texto):
    if not texto or not texto.strip():
        return texto

    try:
        traductor = preparar_traductor()
        return traductor.translate(texto[:3000])
    except Exception:
        return texto


def traducir_noticia(titulo, resumen):
    separador = "\n\n"

    if resumen:
        combinado = titulo + separador + resumen[:800]
    else:
        combinado = titulo

    resultado = traducir_espanol(combinado)

    if resultado == combinado:
        return titulo, resumen, False

    partes = resultado.split(separador, 1)
    titulo_es = partes[0].strip()

    resumen_es = (
        partes[1].strip()
        if len(partes) > 1
        else resumen
    )

    return titulo_es or titulo, resumen_es or resumen, True


# ==================================================
# LIMPIEZA RSS
# ==================================================

def limpiar_html(texto):
    if not texto:
        return ""

    texto = re.sub(
        r"<script.*?</script>",
        " ",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )

    texto = re.sub(
        r"<style.*?</style>",
        " ",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )

    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = html.unescape(texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def obtener_fecha(entry):
    fecha = entry.get("published") or entry.get("updated")

    if not fecha:
        return ""

    try:
        dt = parsedate_to_datetime(fecha)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.strftime("%d/%m/%Y %H:%M UTC")

    except (TypeError, ValueError, OverflowError):
        return str(fecha)


# ==================================================
# CATEGORÍAS
# ==================================================

def categorizar(texto):
    texto = f" {texto.lower()} "

    grupos = {
        "Vulnerabilidades": [
            "vulnerability", "vulnerabilities",
            "vulnerabilidad", "cve-", "zero-day",
            "zero day", "security flaw", "exploit",
            "security patch",
        ],
        "Malware": [
            "malware", "ransomware", "trojan",
            "stealer", "botnet", "spyware",
            "infostealer", "backdoor", "phishing",
        ],
        "Inteligencia artificial": [
            "artificial intelligence", "machine learning",
            "generative ai", "chatgpt", "openai",
            "large language model", "llm",
        ],
        "Hacking": [
            "hacker", "hacking", "cyberattack",
            "cyber attack", "data breach", "data leak",
            "hacked", "attackers",
        ],
    }

    for categoria, palabras in grupos.items():
        if any(p in texto for p in palabras):
            return categoria

    return "General"


# ==================================================
# CARGAR NOTICIAS
# ==================================================

@st.cache_data(ttl=600, show_spinner=False)
def cargar_noticias(fuentes_seleccionadas):
    noticias = []
    errores = []

    for fuente in fuentes_seleccionadas:
        url = FUENTES.get(fuente)

        if not url:
            continue

        try:
            respuesta = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; CyberFeed/1.0)"
                },
                timeout=12,
            )

            respuesta.raise_for_status()
            feed = feedparser.parse(respuesta.content)

            if not feed.entries:
                errores.append(fuente)
                continue

            for entry in feed.entries:
                titulo = limpiar_html(
                    entry.get("title", "Sin título")
                )

                resumen = limpiar_html(
                    entry.get("summary")
                    or entry.get("description")
                    or ""
                )

                enlace = entry.get("link", "")

                if not titulo or not enlace:
                    continue

                noticias.append({
                    "fuente": fuente,
                    "titulo_original": titulo,
                    "resumen_original": resumen,
                    "enlace": enlace,
                    "categoria": categorizar(titulo + " " + resumen),
                    "fecha": obtener_fecha(entry),
                })

        except (requests.RequestException, ValueError):
            errores.append(fuente)

    unicas = []
    vistos = set()

    for noticia in noticias:
        if noticia["enlace"] not in vistos:
            vistos.add(noticia["enlace"])
            unicas.append(noticia)

    return unicas, errores


# ==================================================
# CABECERA
# ==================================================

st.title("🛡️ CyberFeed")

st.markdown(
    '<div class="cf-subtitle">'
    "Tu panel de noticias de ciberseguridad, vulnerabilidades y amenazas."
    "</div>",
    unsafe_allow_html=True,
)

col_info, col_refresh = st.columns([3, 1])

with col_info:
    st.caption(
        "Fuentes RSS · Traducción local inglés-español con Argos Translate"
    )

with col_refresh:
    if st.button("🔄 Actualizar noticias", use_container_width=True):
        cargar_noticias.clear()
        st.rerun()


# ==================================================
# BARRA LATERAL
# ==================================================

st.sidebar.title("⚙️ Configuración")

fuentes_seleccionadas = st.sidebar.multiselect(
    "Fuentes de noticias",
    options=list(FUENTES.keys()),
    default=list(FUENTES.keys()),
)

categoria_seleccionada = st.sidebar.selectbox(
    "Categoría",
    CATEGORIAS,
)

buscar = st.sidebar.text_input(
    "Buscar noticias",
    placeholder="Ransomware, CVE, phishing...",
)

max_noticias = st.sidebar.slider(
    "Noticias por página",
    min_value=5,
    max_value=20,
    value=5,
    step=5,
)

st.sidebar.caption(
    "Argos Translate funciona localmente después de instalar su modelo."
)


# ==================================================
# PREPARAR TRADUCTOR
# ==================================================

try:
    with st.spinner(
        "Preparando el traductor local. La primera carga puede tardar..."
    ):
        preparar_traductor()

    traductor_disponible = True

except Exception as error:
    traductor_disponible = False

    st.error(
        "No se pudo instalar o iniciar el traductor local. "
        "Comprueba los registros de Streamlit Cloud."
    )

    with st.expander("Detalles del error"):
        st.code(str(error)[:2000])


# ==================================================
# CONSULTAR FUENTES
# ==================================================

if not fuentes_seleccionadas:
    st.info("Selecciona al menos una fuente.")
    st.stop()

with st.spinner("Consultando fuentes RSS..."):
    noticias, errores = cargar_noticias(tuple(fuentes_seleccionadas))

if errores:
    st.warning(
        "No se pudieron consultar estas fuentes: "
        + ", ".join(errores)
    )

if not noticias:
    st.error("No se han podido cargar noticias. Inténtalo más tarde.")
    st.stop()


# ==================================================
# FILTROS
# ==================================================

noticias_filtradas = []

for noticia in noticias:
    if (
        categoria_seleccionada != "Todas"
        and noticia["categoria"] != categoria_seleccionada
    ):
        continue

    texto = (
        noticia["titulo_original"]
        + " "
        + noticia["resumen_original"]
    ).lower()

    if buscar and buscar.strip().lower() not in texto:
        continue

    noticias_filtradas.append(noticia)


# ==================================================
# MÉTRICAS
# ==================================================

m1, m2, m3 = st.columns(3)

m1.metric("Noticias recopiladas", len(noticias))
m2.metric("Resultados filtrados", len(noticias_filtradas))
m3.metric("Fuentes seleccionadas", len(fuentes_seleccionadas))

st.divider()


# ==================================================
# MOSTRAR NOTICIAS
# ==================================================

if not noticias_filtradas:
    st.info("No hay noticias que coincidan con los filtros.")
    st.stop()

noticias_a_mostrar = noticias_filtradas[:max_noticias]

st.subheader("📰 Últimas noticias")

st.caption(
    f"Mostrando {len(noticias_a_mostrar)} de "
    f"{len(noticias_filtradas)} resultados."
)

fallos = 0

for noticia in noticias_a_mostrar:
    st.markdown(
        f'<span class="cf-tag">'
        f'{html.escape(noticia["categoria"])}</span>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="cf-source">'
        f'{html.escape(noticia["fuente"])}</div>',
        unsafe_allow_html=True,
    )

    if traductor_disponible:
        titulo_es, resumen_es, traduccion_ok = traducir_noticia(
            noticia["titulo_original"],
            noticia["resumen_original"],
        )

        if not traduccion_ok:
            fallos += 1
    else:
        titulo_es = noticia["titulo_original"]
        resumen_es = noticia["resumen_original"]
        fallos += 1

    st.markdown(
        f'<div class="cf-title">'
        f'{html.escape(titulo_es)}</div>',
        unsafe_allow_html=True,
    )

    if resumen_es:
        st.markdown(
            f'<div class="cf-summary">'
            f'{html.escape(resumen_es)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("La fuente no proporciona un resumen.")

    if noticia["fecha"]:
        st.markdown(
            f'<div class="cf-date">'
            f'🕒 {html.escape(noticia["fecha"])}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'[Leer noticia original ↗]({noticia["enlace"]})'
    )

    st.divider()


# ==================================================
# ESTADO
# ==================================================

if not traductor_disponible:
    st.warning(
        "Se muestran los textos originales porque el traductor "
        "no está disponible."
    )
elif fallos:
    st.warning(
        f"{fallos} noticias no pudieron traducirse correctamente."
    )
else:
    st.success("Traducción local disponible.")
    

# ==================================================
# PRUEBA DEL TRADUCTOR
# ==================================================

with st.expander("🧪 Probar traducción local"):
    frase = st.text_input(
        "Frase de prueba en inglés",
        value="Hackers discovered a new security vulnerability.",
        key="argos_test",
    )

    if st.button("Traducir frase"):
        if not traductor_disponible:
            st.error("El traductor local no está disponible.")
        elif not frase.strip():
            st.warning("Escribe una frase.")
        else:
            resultado = traducir_espanol(frase)
            st.write("**Resultado:**")
            st.write(resultado)


# ==================================================
# PIE
# ==================================================

st.caption(
    "CyberFeed · Las noticias pertenecen a sus fuentes originales. "
    "La traducción automática puede contener errores."
)
