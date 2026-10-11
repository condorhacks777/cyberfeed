
import re
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests
import streamlit as st


# --------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------

st.set_page_config(
    page_title="CyberFeed | Ciberseguridad",
    page_icon="🛡️",
    layout="wide",
)

FUENTES = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
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

TRADUCTORES = [
    "https://translate.argosopentech.com/translate",
    "https://translate.fedilab.app/translate",
    "https://translate.cutie.dating/translate",
]


# --------------------------------------------------
# ESTILOS
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background: #07111f;
        color: #e8f0fb;
    }

    [data-testid="stHeader"] {
        background: rgba(7, 17, 31, 0.95);
    }

    h1, h2, h3 {
        color: #f2f7ff;
    }

    .cf-subtitle {
        color: #93a9c4;
        font-size: 1rem;
        margin-top: -12px;
        margin-bottom: 25px;
    }

    .cf-tag {
        display: inline-block;
        padding: 4px 9px;
        margin-bottom: 8px;
        border-radius: 6px;
        color: #62e6ce;
        background: #10312f;
        font-size: 0.78rem;
        font-weight: 600;
    }

    .cf-source {
        color: #91a6bf;
        font-size: 0.82rem;
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
        font-size: 0.96rem;
        line-height: 1.65;
    }

    .cf-date {
        color: #7f96b2;
        font-size: 0.8rem;
        margin-top: 10px;
    }

    a {
        color: #57dcca !important;
    }

    [data-testid="stSidebar"] {
        background: #0b1829;
    }

    div[data-testid="stMetric"] {
        background: #0d1b2d;
        padding: 15px;
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


# --------------------------------------------------
# LIMPIEZA DE CONTENIDO RSS
# --------------------------------------------------

def limpiar_html(texto):
    if not texto:
        return ""

    texto = re.sub(r"<script.*?</script>", " ", texto,
                   flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r"<style.*?</style>", " ", texto,
                   flags=re.IGNORECASE | re.DOTALL)
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


# --------------------------------------------------
# CATEGORIZACIÓN
# --------------------------------------------------

def categorizar(texto):
    texto = texto.lower()

    palabras_vulnerabilidades = [
        "vulnerability", "vulnerabilidad", "cve-",
        "zero-day", "zero day", "patch", "exploit",
        "security flaw", "critical flaw", "bug",
    ]

    palabras_malware = [
        "malware", "ransomware", "trojan", "stealer",
        "botnet", "spyware", "infostealer", "backdoor",
        "malicious", "phishing", "infostealing",
    ]

    palabras_hacking = [
        "hacker", "hacking", "breach", "cyberattack",
        "cyber attack", "data leak", "data breach",
        "attackers", "exploited", "hacked",
    ]

    palabras_ia = [
        "artificial intelligence", " ai ", "llm",
        "chatgpt", "machine learning", "openai",
        "generative ai", "language model",
    ]

    if any(p in texto for p in palabras_vulnerabilidades):
        return "Vulnerabilidades"

    if any(p in texto for p in palabras_malware):
        return "Malware"

    if any(p in texto for p in palabras_ia):
        return "Inteligencia artificial"

    if any(p in texto for p in palabras_hacking):
        return "Hacking"

    return "General"


# --------------------------------------------------
# TRADUCCIÓN GRATUITA CON VARIOS SERVIDORES
# --------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def traducir_espanol(texto):
    if not texto or not texto.strip():
        return texto

    texto = texto.strip()

    # Evita enviar textos excesivamente largos al traductor.
    texto_a_traducir = texto[:1800]

    for endpoint in TRADUCTORES:
        try:
            respuesta = requests.post(
                endpoint,
                json={
                    "q": texto_a_traducir,
                    "source": "auto",
                    "target": "es",
                    "format": "text",
                },
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "CyberFeed/1.0",
                },
                timeout=10,
            )

            if not respuesta.ok:
                continue

            resultado = respuesta.json().get("translatedText", "")

            if isinstance(resultado, str) and resultado.strip():
                resultado = resultado.strip()

                # Si se recortó el texto, no descarta el resto.
                if len(texto) > len(texto_a_traducir):
                    return resultado + "…"

                return resultado

        except (
            requests.RequestException,
            ValueError,
            TypeError,
            AttributeError,
        ):
            continue

    # La app sigue funcionando aunque fallen los traductores.
    return texto


# --------------------------------------------------
# CARGA DE NOTICIAS
# --------------------------------------------------

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
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; CyberFeed/1.0)"
                    )
                },
                timeout=15,
            )
            respuesta.raise_for_status()

            feed = feedparser.parse(respuesta.content)

            if not feed.entries:
                errores.append(fuente)
                continue

            for entry in feed.entries:
                titulo_original = limpiar_html(
                    entry.get("title", "Sin título")
                )

                resumen_original = limpiar_html(
                    entry.get("summary")
                    or entry.get("description")
                    or ""
                )

                enlace = entry.get("link", "")

                if not titulo_original or not enlace:
                    continue

                texto_clasificacion = (
                    titulo_original + " " + resumen_original
                )

                noticias.append({
                    "fuente": fuente,
                    "titulo_original": titulo_original,
                    "resumen_original": resumen_original,
                    "enlace": enlace,
                    "categoria": categorizar(texto_clasificacion),
                    "fecha": obtener_fecha(entry),
                })

        except (requests.RequestException, ValueError):
            errores.append(fuente)

    # Elimina duplicados por enlace.
    noticias_unicas = []
    enlaces_vistos = set()

    for noticia in noticias:
        enlace = noticia["enlace"]

        if enlace not in enlaces_vistos:
            enlaces_vistos.add(enlace)
            noticias_unicas.append(noticia)

    # Ordena por fecha cuando el RSS proporciona una fecha válida.
    # Los elementos sin fecha se mantienen al final.
    return noticias_unicas, errores


# --------------------------------------------------
# CABECERA
# --------------------------------------------------

st.title("🛡️ CyberFeed")
st.markdown(
    '<div class="cf-subtitle">'
    "Tu panel de noticias de ciberseguridad, vulnerabilidades y amenazas."
    "</div>",
    unsafe_allow_html=True,
)

col_a, col_b = st.columns([3, 1])

with col_a:
    st.caption(
        "Noticias de fuentes especializadas · Traducción automática al español"
    )

with col_b:
    if st.button("🔄 Actualizar noticias", use_container_width=True):
        cargar_noticias.clear()
        traducir_espanol.clear()
        st.rerun()


# --------------------------------------------------
# BARRA LATERAL Y FILTROS
# --------------------------------------------------

st.sidebar.title("⚙️ Configuración")

fuentes_seleccionadas = st.sidebar.multiselect(
    "Fuentes de noticias",
    options=list(FUENTES.keys()),
    default=list(FUENTES.keys()),
)

categoria_seleccionada = st.sidebar.selectbox(
    "Categoría",
    options=CATEGORIAS,
)

buscar = st.sidebar.text_input(
    "Buscar noticias",
    placeholder="Ej. ransomware, CVE, phishing...",
)

max_noticias = st.sidebar.slider(
    "Noticias por página",
    min_value=5,
    max_value=50,
    value=20,
    step=5,
)

st.sidebar.divider()
st.sidebar.caption(
    "CyberFeed utiliza fuentes RSS públicas y servicios de traducción "
    "comunitarios. La disponibilidad de estos últimos puede variar."
)


# --------------------------------------------------
# OBTENER Y FILTRAR NOTICIAS
# --------------------------------------------------

if not fuentes_seleccionadas:
    st.info("Selecciona al menos una fuente en el menú lateral.")
    st.stop()

with st.spinner("Consultando fuentes de ciberseguridad…"):
    noticias, errores = cargar_noticias(
        tuple(fuentes_seleccionadas)
    )

if errores:
    st.warning(
        "No se pudo consultar alguna fuente: "
        + ", ".join(errores)
        + ". Puedes intentarlo de nuevo con «Actualizar noticias»."
    )

if not noticias:
    st.error(
        "No se han podido cargar noticias. Comprueba la conexión "
        "o inténtalo de nuevo más tarde."
    )
    st.stop()

noticias_filtradas = []

for noticia in noticias:
    if (
        categoria_seleccionada != "Todas"
        and noticia["categoria"] != categoria_seleccionada
    ):
        continue

    texto_busqueda = (
        noticia["titulo_original"] + " " + noticia["resumen_original"]
    ).lower()

    if buscar and buscar.lower().strip() not in texto_busqueda:
        continue

    noticias_filtradas.append(noticia)


# --------------------------------------------------
# MÉTRICAS
# --------------------------------------------------

total = len(noticias)
total_filtrado = len(noticias_filtradas)
total_fuentes = len(set(n["fuente"] for n in noticias))

m1, m2, m3 = st.columns(3)

m1.metric("Noticias recopiladas", total)
m2.metric("Resultados filtrados", total_filtrado)
m3.metric("Fuentes activas", total_fuentes)

st.divider()


# --------------------------------------------------
# MOSTRAR NOTICIAS EN ESPAÑOL
# --------------------------------------------------

if not noticias_filtradas:
    st.info("No hay noticias que coincidan con los filtros.")
    st.stop()

noticias_a_mostrar = noticias_filtradas[:max_noticias]

st.subheader("📰 Últimas noticias")
st.caption(
    f"Mostrando {len(noticias_a_mostrar)} de "
    f"{total_filtrado} resultados."
)

for indice, noticia in enumerate(noticias_a_mostrar, start=1):
    with st.container():
        st.markdown(
            f'<span class="cf-tag">'
            f'{html.escape(noticia["categoria"])}</span>',
            unsafe_allow_html=True,
        )

        st.markdown(
            f'<div class="cf-source">'
            f'{html.escape(noticia["fuente"])}'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.spinner("Traduciendo noticia…" if indice == 1 else ""):
            titulo_es = traducir_espanol(
                noticia["titulo_original"]
            )

            resumen_es = traducir_espanol(
                noticia["resumen_original"]
            )

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
            st.caption("Esta noticia no incluye un resumen en el RSS.")

        if noticia["fecha"]:
            st.markdown(
                f'<div class="cf-date">'
                f'🕒 {html.escape(noticia["fecha"])}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"[Leer noticia original ↗]({noticia['enlace']})")
        st.divider()


# --------------------------------------------------
# PIE
# --------------------------------------------------

st.caption(
    "CyberFeed · Las noticias pertenecen a sus respectivas fuentes. "
    "La traducción automática puede contener errores."
)
