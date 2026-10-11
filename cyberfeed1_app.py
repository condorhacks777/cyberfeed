
import re
import html
import time
from datetime import timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests
import streamlit as st
from deep_translator import GoogleTranslator


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


# ==================================================
# DISEÑO
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

    div.stButton > button {
        border-radius: 9px;
    }

    hr {
        border-color: #1b3047;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# LIMPIEZA DE TEXTO
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
# CLASIFICACIÓN
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
# TRADUCCIÓN GOOGLE
# ==================================================

@st.cache_data(ttl=86400, show_spinner=False)
def traducir_espanol(texto):
    if not texto or not texto.strip():
        return texto

    try:
        traductor = GoogleTranslator(
            source="auto",
            target="es",
        )

        resultado = traductor.translate(texto[:4500])

        if resultado and resultado.strip():
            return resultado.strip()

    except Exception:
        pass

    return texto


def traducir_noticia(titulo, resumen):
    """
    Combina título y resumen para reducir las solicitudes.
    Devuelve título traducido, resumen traducido y estado.
    """
    separador = "\n\n"

    if resumen:
        texto_combinado = titulo + separador + resumen[:800]
    else:
        texto_combinado = titulo

    resultado = traducir_espanol(texto_combinado)

    if resultado == texto_combinado:
        return titulo, resumen, False

    partes = resultado.split(separador, 1)

    titulo_es = partes[0].strip()

    if len(partes) > 1:
        resumen_es = partes[1].strip()
    else:
        resumen_es = resumen

    return titulo_es or titulo, resumen_es or resumen, True


# ==================================================
# CARGAR FUENTES RSS
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
    enlaces_vistos = set()

    for noticia in noticias:
        if noticia["enlace"] not in enlaces_vistos:
            enlaces_vistos.add(noticia["enlace"])
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

col_titulo, col_actualizar = st.columns([3, 1])

with col_titulo:
    st.caption(
        "Noticias RSS · Traducción al español mediante Google Translate"
    )

with col_actualizar:
    if st.button("🔄 Actualizar noticias", use_container_width=True):
        cargar_noticias.clear()
        st.rerun()


# ==================================================
# FILTROS
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
    "Las traducciones se guardan en caché para reducir solicitudes. "
    "Google puede limitar el acceso automatizado."
)


# ==================================================
# OBTENER NOTICIAS
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
# FILTRAR
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
m3.metric(
    "Fuentes seleccionadas",
    len(fuentes_seleccionadas),
)

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

for indice, noticia in enumerate(noticias_a_mostrar):
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

    # Una sola llamada por noticia, en lugar de dos.
    titulo_es, resumen_es, traduccion_ok = traducir_noticia(
        noticia["titulo_original"],
        noticia["resumen_original"],
    )

    if not traduccion_ok:
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

    # Pausa breve entre noticias para reducir ráfagas.
    if indice < len(noticias_a_mostrar) - 1:
        time.sleep(0.4)


# ==================================================
# ESTADO DE TRADUCCIÓN
# ==================================================

if fallos:
    st.warning(
        f"{fallos} noticias no se pudieron traducir. "
        "Se ha mostrado el contenido original. Si Google ha limitado "
        "las solicitudes, espera antes de volver a intentarlo."
    )
else:
    st.success("Las noticias se han procesado correctamente.")


# ==================================================
# PRUEBA MANUAL
# ==================================================

with st.expander("🧪 Probar Google Translator"):
    texto_prueba = st.text_input(
        "Texto en inglés",
        value="Hackers discovered a new security vulnerability.",
        key="prueba_google",
    )

    if st.button("Probar traducción"):
        try:
            resultado = GoogleTranslator(
                source="auto",
                target="es",
            ).translate(texto_prueba.strip()[:1000])

            st.write("**Resultado:**")
            st.write(resultado)

        except Exception as error:
            st.error("Google Translate no ha aceptado la solicitud.")
            st.code(str(error)[:1000])


# ==================================================
# PIE
# ==================================================

st.caption(
    "CyberFeed · Las noticias pertenecen a sus fuentes originales. "
    "La traducción automática puede contener errores."
)
