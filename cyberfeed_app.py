import streamlit as st
import requests
from datetime import datetime, timedelta

# ── Configuración de página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="CyberFeed",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── API Key NewsAPI ───────────────────────────────────────────────────────────
NEWSAPI_KEY = "51214314c9a148fa9cf8ee9d69771431"

# ── CSS personalizado ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap');

html, body, [class*="stApp"] {
    background-color: #000a03 !important;
    color: #00ff88 !important;
    font-family: 'Share Tech Mono', monospace !important;
}
body::after {
    content: "";
    position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,136,0.015) 2px, rgba(0,255,136,0.015) 4px);
    pointer-events: none; z-index: 9999;
}
h1 { font-family: 'Orbitron', monospace !important; color: #00ff88 !important; letter-spacing: 0.15em !important; }
.stButton > button {
    background: transparent !important;
    border: 1px solid #00ff88 !important;
    color: #00ff88 !important;
    font-family: 'Share Tech Mono', monospace !important;
    letter-spacing: 0.1em !important;
    border-radius: 0 !important;
    width: 100% !important;
}
.stButton > button:hover { background: rgba(0,255,136,0.1) !important; }
.stSelectbox > div > div {
    background: #000a03 !important;
    border: 1px solid rgba(0,255,136,0.3) !important;
    color: #00ff88 !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
}
.stExpander {
    border: 1px solid rgba(0,255,136,0.2) !important;
    border-radius: 0 !important;
    background: rgba(0,10,5,0.85) !important;
    margin-bottom: 0.5rem !important;
}
.stExpander:hover { border-color: rgba(0,255,136,0.5) !important; }
hr { border-color: rgba(0,255,136,0.15) !important; }
p, li, span, label { color: rgba(200,255,200,0.85) !important; font-family: 'Share Tech Mono', monospace !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 700px !important; }
</style>
""", unsafe_allow_html=True)

# ── Categorías ────────────────────────────────────────────────────────────────
CATEGORIAS = {
    "◈ TODAS":         "cybersecurity OR hacking OR \"data breach\" OR ransomware OR malware OR CVE",
    "⚠ BRECHAS":       "\"data breach\" OR \"data leak\" OR hacked OR ransomware attack",
    "⚙ HERRAMIENTAS":  "hacking tool OR pentest OR exploit OR \"offensive security\" OR cybersecurity tool",
    "☣ CVEs":          "CVE OR vulnerability OR \"zero day\" OR \"zero-day\" OR patch tuesday",
    "◉ GRUPOS APT":    "APT OR \"nation state\" hacking OR cyberespionage OR \"state sponsored\"",
    "₿ CRYPTO":        "crypto hack OR DeFi exploit OR blockchain hack OR \"exchange hack\"",
}

# ── Funciones ─────────────────────────────────────────────────────────────────
def fetch_news(query: str, page_size: int = 10) -> list:
    desde = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    r = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": query,
            "from": desde,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": page_size,
            "apiKey": NEWSAPI_KEY,
        },
        timeout=10,
    )
    if r.status_code == 401:
        raise ValueError("API key inválida.")
    if r.status_code == 429:
        raise ValueError("Límite de llamadas alcanzado. Inténtalo más tarde.")
    r.raise_for_status()
    return r.json().get("articles", [])


def format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return iso[:10] if iso else "—"


def render_card(article: dict):
    title  = article.get("title") or "Sin título"
    desc   = article.get("description") or "Sin descripción disponible."
    source = article.get("source", {}).get("name", "Desconocida")
    url    = article.get("url", "#")
    fecha  = format_date(article.get("publishedAt", ""))
    author = article.get("author") or ""

    # Quitar sufijo " - Fuente" que añade NewsAPI
    if " - " in title:
        title = title.rsplit(" - ", 1)[0]

    with st.expander(f"📰 {title}", expanded=False):
        st.markdown(
            f"<small style='color:rgba(0,207,255,0.7)'>📅 {fecha} &nbsp;·&nbsp; 🔗 {source}"
            + (f" &nbsp;·&nbsp; ✍ {author}" if author else "") + "</small>",
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.markdown(desc)
        st.markdown(
            f"<a href='{url}' target='_blank' style='color:#00ff88; font-size:0.8rem;'>"
            f"▶ Leer artículo completo</a>",
            unsafe_allow_html=True,
        )


# ── Cabecera ──────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; font-size:0.7rem; color:rgba(0,255,136,0.4); letter-spacing:0.15em'>"
    f"TERMINAL DE INTELIGENCIA DE AMENAZAS &nbsp;·&nbsp; {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    f"</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Controles ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    cat_label = st.selectbox("Categoría", list(CATEGORIAS.keys()), label_visibility="collapsed")
with col2:
    buscar = st.button("↻ BUSCAR")

num_noticias = st.slider("Número de noticias", min_value=5, max_value=20, value=10, step=5)

# ── Estado de sesión ──────────────────────────────────────────────────────────
if "articles"    not in st.session_state: st.session_state.articles    = []
if "ultima_cat"  not in st.session_state: st.session_state.ultima_cat  = None
if "ultima_sync" not in st.session_state: st.session_state.ultima_sync = None

cargar = buscar or st.session_state.ultima_cat != cat_label

if cargar:
    with st.spinner(f"⚡ Buscando noticias de {cat_label.strip()}..."):
        try:
            arts = fetch_news(CATEGORIAS[cat_label], page_size=num_noticias)
            st.session_state.articles    = arts
            st.session_state.ultima_cat  = cat_label
            st.session_state.ultima_sync = datetime.now().strftime("%H:%M:%S")
        except ValueError as e:
            st.error(f"⚠ {e}")
            st.session_state.articles = []
        except Exception as e:
            st.error(f"⚠ Error de conexión: {e}")
            st.session_state.articles = []

# ── Resultados ────────────────────────────────────────────────────────────────
articles = st.session_state.articles

if articles:
    st.markdown(
        f"<p style='font-size:0.65rem; color:rgba(0,255,136,0.35)'>"
        f"RESULTADOS: <span style='color:#00ff88'>{len(articles)}</span> &nbsp;·&nbsp; "
        f"ÚLTIMA SYNC: <span style='color:#00cfff'>{st.session_state.ultima_sync}</span> &nbsp;·&nbsp; "
        f"ÚLTIMOS 7 DÍAS"
        f"</p>",
        unsafe_allow_html=True,
    )
    for art in articles:
        render_card(art)

    st.markdown("---")
    st.markdown(
        "<p style='text-align:center; font-size:0.6rem; color:rgba(0,255,136,0.2)'>"
        "◈ CYBERFEED · NOTICIAS VÍA NEWSAPI · SIN COSTE ◈<br>"
        "Verifica siempre la fuente original antes de compartir."
        "</p>",
        unsafe_allow_html=True,
    )
elif not cargar:
    st.info("Selecciona una categoría y pulsa **↻ BUSCAR**.")
