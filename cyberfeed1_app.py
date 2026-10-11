
import re
import html
from email.utils import parsedate_to_datetime
from datetime import timezone

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
        background: rgba(7, 17, 31, 0.95);
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
        margin-bottom: 25px;
    }

    .cf-tag {
        display: inline-block;
        padding: 4px 9px;
        border-radius: 6px;
        margin-bottom: 8px;
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


# ==================================================
# LIMPIAR TEXTO RSS
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
# CLASIFICAR NOTICIAS
# ==================================================

def categorizar(texto):
    texto = f" {texto.lower()} "

    vulnerabilidades = [
        "vulnerability",
        "vulnerabilities",
        "vulnerabilidad",
        "cve-",
        "zero-day",
        "zero day",
        "security flaw",
        "security patch",
        "exploit",
    ]

    malware = [
        "malware",
        "ransomware",
        "trojan",
        "stealer",
        "botnet",
        "spyware",
        "infostealer",
        "backdoor",
        "phishing",
    ]

    inteligencia_artificial = [
        "artificial intelligence",
        "machine learning",
        "generative ai",
        "chatgpt",
        "openai",
        "large language model",
        "llm",
    ]

    hacking = [
        "hacker",
        "hacking",
        "cyberattack",
        "cyber attack",
        "data breach",
        "data leak",
        "hacked",
        "attackers",
    ]

    if any(p in texto for p in vulnerabilidades):
        return "Vulnerabilidades"

    if any(p in texto for p in malware):
        return "Malware"

    if any(p in texto for p in inteligencia_artificial):
        return "Inteligencia artificial"

    if any(p in texto for p in hacking):
        return "Hacking"

    return "General"


# ==================================================
# GOOGLE TRANSLATOR
# ==================================================

@st.cache_data(ttl=86400, show_spinner=False)
def traducir_espanol(texto):
    if not texto or not texto.strip():
        return texto

    texto = texto.strip()

    try:
        traductor = GoogleTranslator(
            source="auto",
            target="es",
        )

        resultado = traductor.translate(texto[:4500])

        if resultado and resultado.strip():
            return resultado.strip()

        return texto

    except Exception:
        return texto


# ==================================================
# CARGAR RSS
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
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; CyberFeed/1.0)"
                    )
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

                noticias.append(
                    {
                        "fuente": fuente,
                        "titulo_original": titulo,
                        "resumen_original": resumen,
                        "enlace": enlace,
                        "categoria": categorizar(
                            titulo + " " + resumen
                        ),
                        "fecha": obtener_fecha(entry),
                    }
                )

        except (requests.RequestException, ValueError):
            errores.append(fuente)

    # Eliminar noticias duplicadas.
    unicas = []
    enlaces_vistos = set()

    for noticia in noticias:
        enlace = noticia["enlace"]

        if enlace not in enlaces_vistos:
            enlaces_vistos.add(enlace)
            unicas.append(noticia)

    return unicas, errores


# ==================================================
# CABECERA
# ==================================================

st.title("🛡️ CyberFeed")

st.markdown(
    '<div class="cf-subtitle">'
    "Tu panel de noticias de ciberseguridad, "
    "vulnerabilidades y amenazas."
    "</div>",
    unsafe_allow_html=True,
)

col_cabecera, col_actualizar = st.columns([3, 1])

with col_cabecera:
    st.caption(
        "Fuentes RSS especializadas · Traducción al español con Google Translate"
    )

with col_actualizar:
    if st.button(
        "🔄 Actualizar noticias",
        use_container_width=True,
    ):
        cargar_noticias.clear()
        traducir_espanol.clear()
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
    options=CATEGORIAS,
)

buscar = st.sidebar.text_input(
    "Buscar noticias",
    placeholder="Ransomware, CVE, phishing...",
)

max_noticias = st.sidebar.slider(
    "Noticias por página",
    min_value=5,
    max_value=30,
    value=5,
    step=5,
)

st.sidebar.divider()

st.sidebar.caption(
    "La traducción depende de la disponibilidad del servicio web "
    "de Google Translate. Si falla, se mostrará el texto original."
)


# ==================================================
# CARGAR NOTICIAS
# ==================================================

if not fuentes_seleccionadas:
    st.info("Selecciona al menos una fuente en el menú lateral.")
    st.stop()

with st.spinner("Consultando fuentes RSS..."):
    noticias, errores = cargar_noticias(
        tuple(fuentes_seleccionadas)
    )

if errores:
    st.warning(
        "No se pudieron consultar estas fuentes: "
        + ", ".join(errores)
    )

if not noticias:
    st.error(
        "No se han podido cargar noticias. "
        "Inténtalo de nuevo más tarde."
    )
    st.stop()


# ==================================================
# FILTRAR NOTICIAS
# ==================================================

noticias_filtradas = []

for noticia in noticias:
    if (
        categoria_seleccionada != "Todas"
        and noticia["categoria"] != categoria_seleccionada
    ):
        continue

    texto_busqueda = (
        noticia["titulo_original"]
        + " "
        + noticia["resumen_original"]
    ).lower()

    if buscar and buscar.strip().lower() not in texto_busqueda:
        continue

    noticias_filtradas.append(noticia)


# ==================================================
# MÉTRICAS
# ==================================================

total = len(noticias)
total_filtrado = len(noticias_filtradas)
total_fuentes = len(set(n["fuente"] for n in noticias))

m1, m2, m3 = st.columns(3)

m1.metric("Noticias recopiladas", total)
m2.metric("Resultados filtrados", total_filtrado)
m3.metric("Fuentes consultadas", total_fuentes)

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
    f"{total_filtrado} resultados."
)

fallos_traduccion = 0

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

    # Traducir titular y resumen con Google Translator.
    # Se limita el resumen para reducir el número de caracteres.
    titulo_es = traducir_espanol(
        noticia["titulo_original"]
    )

    resumen_original = noticia["resumen_original"][:1200]

    resumen_es = traducir_espanol(resumen_original)

    if titulo_es == noticia["titulo_original"]:
        fallos_traduccion += 1

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
# ESTADO DE TRADUCCIÓN
# ==================================================

if fallos_traduccion:
    st.warning(
        f"No se pudieron traducir {fallos_traduccion} titulares. "
        "Se ha mostrado el texto original. Prueba a actualizar "
        "más tarde si Google Translate no responde."
    )
else:
    st.success("Los titulares se han procesado correctamente.")


# ==================================================
# PRUEBA MANUAL DEL TRADUCTOR
# ==================================================

with st.expander("🧪 Probar Google Translator"):
    texto_prueba = st.text_input(
        "Escribe una frase en inglés",
        value="Hackers discovered a new security vulnerability.",
        key="texto_prueba_google",
    )

    if st.button("Traducir frase de prueba"):
        if not texto_prueba.strip():
            st.warning("Escribe una frase para traducir.")
        else:
            try:
                resultado_prueba = GoogleTranslator(
                    source="auto",
                    target="es",
                ).translate(texto_prueba.strip()[:4500])

                if resultado_prueba:
                    st.write("**Traducción:**")
                    st.write(resultado_prueba)
                else:
                    st.error("Google Translate no devolvió una traducción.")

            except Exception as error:
                st.error(
                    "Google Translate no está respondiendo desde "
                    "la aplicación."
                )
                st.code(str(error)[:1000])


# ==================================================
# PIE DE PÁGINA
# ==================================================

st.caption(
    "CyberFeed · Noticias de sus respectivas fuentes. "
    "Las traducciones automáticas pueden contener errores."
)
