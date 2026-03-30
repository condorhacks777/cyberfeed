import streamlit as st
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

NEWSAPI_KEY = "51214314c9a148fa9cf8ee9d69771431"

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
    position: fixed; top:0; left:0; right:0; bottom:0;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,136,0.012) 2px, rgba(0,255,136,0.012) 4px);
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

/* Tarjetas de noticias personalizadas */
.news-card {
    border: 1px solid rgba(0,255,136,0.2);
    border-left: 3px solid #00ff88;
    background: rgba(0,10,5,0.85);
    padding: 0.9rem 1rem;
    margin-bottom: 0.5rem;
    cursor: pointer;
}
.news-card.critical { border-left-color: #ff2d2d; }
.news-card.high     { border-left-color: #ff8c00; }
.news-card.medium   { border-left-color: #ffd700; }
.news-card.low, .news-card.info { border-left-color: #00cfff; }

.badge-critical { color:#ff2d2d; border:1px solid #ff2d2d; background:rgba(255,45,45,0.1); padding:1px 6px; font-size:0.65rem; font-weight:700; }
.badge-high     { color:#ff8c00; border:1px solid #ff8c00; background:rgba(255,140,0,0.1); padding:1px 6px; font-size:0.65rem; font-weight:700; }
.badge-medium   { color:#ffd700; border:1px solid #ffd700; background:rgba(255,215,0,0.08); padding:1px 6px; font-size:0.65rem; font-weight:700; }
.badge-info, .badge-low { color:#00cfff; border:1px solid #00cfff; background:rgba(0,207,255,0.08); padding:1px 6px; font-size:0.65rem; font-weight:700; }

hr { border-color: rgba(0,255,136,0.15) !important; }
p, li, span, label { color: rgba(200,255,200,0.85) !important; font-family: 'Share Tech Mono', monospace !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; max-width: 700px !important; }
</style>
""", unsafe_allow_html=True)

# ── Categorías ────────────────────────────────────────────────────────────────
CATEGORIAS = {
    "TODAS":        "cybersecurity OR hacking OR ransomware OR malware OR CVE OR \"data breach\"",
    "BRECHAS":      "\"data breach\" OR \"data leak\" OR ransomware attack OR hacked company",
    "HERRAMIENTAS": "hacking tool OR pentest tool OR exploit OR \"offensive security\" OR cybersecurity software",
    "CVEs":         "CVE OR vulnerability OR \"zero day\" OR \"zero-day\" OR \"patch tuesday\"",
    "GRUPOS APT":   "APT OR \"nation state\" hacking OR cyberespionage OR \"state sponsored\" attack",
    "CRYPTO":       "crypto hack OR DeFi exploit OR blockchain hack OR \"exchange hack\" OR NFT hack",
}

SEV_BADGE = {
    "critical": ("CRÍTICO", "badge-critical"),
    "high":     ("ALTO",    "badge-high"),
    "medium":   ("MEDIO",   "badge-medium"),
    "low":      ("BAJO",    "badge-info"),
    "info":     ("INFO",    "badge-info"),
}
CAT_ICONS = { "TODAS":"◈", "BRECHAS":"⚠", "HERRAMIENTAS":"⚙", "CVEs":"☣", "GRUPOS APT":"◉", "CRYPTO":"₿" }

# ── Traducción con Claude (solo títulos y descripciones) ──────────────────────
def traducir_articulos(articulos: list) -> list:
    """Traduce títulos y descripciones al español usando la API de Anthropic de forma gratuita con el plan disponible."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        
        textos = []
        for a in articulos:
            titulo = (a.get("title") or "").rsplit(" - ", 1)[0]
            desc = a.get("description") or ""
            textos.append(f"TÍTULO: {titulo}\nDESCRIPCIÓN: {desc}")
        
        bloque = "\n---\n".join(textos)
        prompt = f"""Traduce al español los siguientes títulos y descripciones de noticias de ciberseguridad.
Mantén términos técnicos en inglés (CVE, ransomware, phishing, exploit, etc).
Responde SOLO con el mismo formato separado por ---

{bloque}"""
        
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",  # modelo más barato
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        
        traducciones = resp.content[0].text.strip().split("---")
        
        resultado = []
        for i, art in enumerate(articulos):
            nuevo = dict(art)
            if i < len(traducciones):
                lineas = traducciones[i].strip().split("\n")
                for linea in lineas:
                    if linea.startswith("TÍTULO:"):
                        nuevo["title"] = linea.replace("TÍTULO:", "").strip()
                    elif linea.startswith("DESCRIPCIÓN:"):
                        nuevo["description"] = linea.replace("DESCRIPCIÓN:", "").strip()
            resultado.append(nuevo)
        return resultado
    except Exception:
        # Si falla la traducción, devolver sin traducir
        return articulos


# ── NewsAPI ───────────────────────────────────────────────────────────────────
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
        raise ValueError("API key de NewsAPI inválida.")
    if r.status_code == 429:
        raise ValueError("Límite de llamadas alcanzado. Inténtalo más tarde.")
    r.raise_for_status()
    arts = r.json().get("articles", [])
    # Limpiar sufijo " - Fuente" del título
    for a in arts:
        if a.get("title") and " - " in a["title"]:
            a["title"] = a["title"].rsplit(" - ", 1)[0]
    return arts


def format_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return iso[:10] if iso else "—"


def render_card(article: dict, idx: int, cat_label: str):
    title  = article.get("title") or "Sin título"
    desc   = article.get("description") or "Sin descripción disponible."
    source = article.get("source", {}).get("name", "Desconocida")
    url    = article.get("url", "#")
    fecha  = format_date(article.get("publishedAt", ""))
    icon   = CAT_ICONS.get(cat_label, "◈")

    st.markdown(f"""
    <div class="news-card">
        <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; margin-bottom:0.4rem;">
            <span style="font-size:0.6rem; color:#00cfff; letter-spacing:0.05em;">{icon} {cat_label}</span>
            <span style="font-size:0.6rem; color:rgba(0,255,136,0.4);">📅 {fecha}</span>
            <span style="font-size:0.6rem; color:rgba(0,207,255,0.5);">🔗 {source}</span>
        </div>
        <div style="font-size:0.88rem; color:#e8ffe8; font-family:'Share Tech Mono',monospace; line-height:1.4; margin-bottom:0.5rem; font-weight:bold;">
            {title}
        </div>
        <div style="font-size:0.76rem; color:rgba(200,255,200,0.75); line-height:1.7; margin-bottom:0.5rem;">
            {desc}
        </div>
        <a href="{url}" target="_blank" style="color:#00ff88; font-size:0.72rem; text-decoration:none;">
            ▶ Leer artículo completo
        </a>
    </div>
    """, unsafe_allow_html=True)


# ── Cabecera ──────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; font-size:0.65rem; color:rgba(0,255,136,0.4); letter-spacing:0.15em'>"
    f"TERMINAL DE INTELIGENCIA DE AMENAZAS &nbsp;·&nbsp; {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    f"</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Controles ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    cat_label = st.selectbox("cat", list(CATEGORIAS.keys()), label_visibility="collapsed")
with col2:
    buscar = st.button("↻ BUSCAR")

num_noticias = st.slider("Número de noticias", 5, 20, 10, 5)
traducir = st.checkbox("Traducir títulos al español (usa Claude Haiku)", value=True)

# ── Sesión ────────────────────────────────────────────────────────────────────
for k, v in [("articles", []), ("ultima_cat", None), ("ultima_sync", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

cargar = buscar or st.session_state.ultima_cat != cat_label

if cargar:
    with st.spinner("⚡ Buscando noticias..."):
        try:
            arts = fetch_news(CATEGORIAS[cat_label], page_size=num_noticias)
            if traducir and arts:
                arts = traducir_articulos(arts)
            st.session_state.articles   = arts
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
        f"<p style='font-size:0.62rem; color:rgba(0,255,136,0.35)'>"
        f"RESULTADOS: <span style='color:#00ff88'>{len(articles)}</span> &nbsp;·&nbsp; "
        f"ÚLTIMA SYNC: <span style='color:#00cfff'>{st.session_state.ultima_sync}</span> &nbsp;·&nbsp; ÚLTIMOS 7 DÍAS"
        f"</p>",
        unsafe_allow_html=True,
    )
    for i, art in enumerate(articles):
        render_card(art, i, cat_label)

    st.markdown(
        "<p style='text-align:center; font-size:0.58rem; color:rgba(0,255,136,0.2); margin-top:1.5rem;'>"
        "◈ CYBERFEED · NOTICIAS VÍA NEWSAPI · SIN COSTE ◈<br>"
        "Verifica siempre la fuente original antes de compartir."
        "</p>",
        unsafe_allow_html=True,
    )
elif not cargar:
    st.info("Selecciona una categoría y pulsa ↻ BUSCAR.")
