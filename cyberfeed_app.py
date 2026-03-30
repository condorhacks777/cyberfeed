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
.news-card {
    border: 1px solid rgba(0,255,136,0.2);
    border-left: 3px solid #00ff88;
    background: rgba(0,10,5,0.85);
    padding: 0.9rem 1rem;
    margin-bottom: 0.5rem;
}
hr { border-color: rgba(0,255,136,0.15) !important; }
p, li, span, label { color: rgba(200,255,200,0.85) !important; font-family: 'Share Tech Mono', monospace !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; max-width: 700px !important; }
</style>
""", unsafe_allow_html=True)

# ── Fuentes especializadas en ciberseguridad ──────────────────────────────────
CYBER_DOMAINS = (
    "thehackernews.com,bleepingcomputer.com,krebsonsecurity.com,"
    "threatpost.com,darkreading.com,securityweek.com,"
    "cyberscoop.com,wired.com,arstechnica.com,techcrunch.com,"
    "portswigger.net,helpnetsecurity.com,infosecurity-magazine.com,"
    "github.blog,offensive-security.com,kitploit.com"
)

CATEGORIAS = {
    "◈ TODAS":        "cybersecurity hacking (breach OR ransomware OR malware OR CVE OR exploit OR vulnerability)",
    "⚠ BRECHAS":      "(\"data breach\" OR \"data leak\" OR ransomware) (company OR hospital OR government OR million records)",
    "⚙ HERRAMIENTAS": "(\"new tool\" OR \"open source\" OR \"released\" OR \"github\" OR \"framework\") (pentest OR \"red team\" OR \"offensive security\" OR \"security tool\" OR \"hacking tool\" OR nmap OR metasploit OR burpsuite OR wireshark)",
    "☣ CVEs":         "(CVE OR vulnerability OR \"zero-day\" OR \"patch tuesday\") (critical OR high severity OR CVSS)",
    "◉ GRUPOS APT":   "(APT OR \"nation state\" OR \"state sponsored\") (hacking OR cyberespionage OR campaign OR attack)",
    "₿ CRYPTO":       "(crypto OR DeFi OR blockchain OR NFT OR exchange) (hack OR exploit OR stolen OR breach OR million)",
}

CAT_ICONS = {
    "◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙",
    "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿",
}

# ── Traducción en lote: UNA sola petición para todos los artículos ────────────
SEP = " <<|>> "
SPLIT = " [[D]] "

def traducir_lote(articulos: list) -> list:
    """
    Concatena todos los títulos y descripciones en un único texto
    y hace UNA sola llamada a MyMemory. Así no se agota el límite diario.
    """
    # Construir bloque único
    fragmentos = []
    for a in articulos:
        t = (a.get("title") or "").strip()[:120]
        d = (a.get("description") or "").strip()[:180]
        fragmentos.append(f"{t}{SPLIT}{d}")

    bloque = SEP.join(fragmentos)

    # MyMemory permite hasta 500 chars por petición en el plan gratuito sin key
    # Si el bloque es muy largo, dividimos en dos llamadas
    mitad = len(fragmentos) // 2
    bloques = []
    if len(bloque) <= 490:
        bloques = [fragmentos]
    else:
        bloques = [fragmentos[:mitad], fragmentos[mitad:]]

    traducidos = []
    for grupo in bloques:
        texto = SEP.join(grupo)[:490]
        try:
            r = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": texto, "langpair": "en|es"},
                timeout=8,
            )
            if r.status_code == 200:
                t_texto = r.json().get("responseData", {}).get("translatedText", "")
                partes = t_texto.split(SEP)
                traducidos.extend(partes)
            else:
                traducidos.extend(grupo)  # fallback: texto original
        except Exception:
            traducidos.extend(grupo)

    # Reconstruir artículos con textos traducidos
    resultado = []
    for i, art in enumerate(articulos):
        nuevo = dict(art)
        if i < len(traducidos):
            segs = traducidos[i].split(SPLIT)
            if len(segs) >= 2:
                nuevo["title"]       = segs[0].strip()
                nuevo["description"] = segs[1].strip()
            elif len(segs) == 1:
                nuevo["title"] = segs[0].strip()
        resultado.append(nuevo)
    return resultado


# ── NewsAPI ───────────────────────────────────────────────────────────────────
def fetch_news(cat_label: str, page_size: int = 10) -> list:
    query = CATEGORIAS[cat_label]
    desde = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    r = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": query,
            "domains": CYBER_DOMAINS,
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


def render_card(article: dict, cat_label: str):
    title  = article.get("title") or "Sin título"
    desc   = article.get("description") or "Sin descripción disponible."
    source = article.get("source", {}).get("name", "Desconocida")
    url    = article.get("url", "#")
    fecha  = format_date(article.get("publishedAt", ""))
    icon   = CAT_ICONS.get(cat_label, "◈")

    st.markdown(f"""
    <div class="news-card">
        <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; margin-bottom:0.4rem;">
            <span style="font-size:0.6rem; color:#00cfff;">{icon} {cat_label.split()[-1]}</span>
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
traducir_activo = st.toggle("🌐 Traducir al español", value=True)

# ── Sesión ────────────────────────────────────────────────────────────────────
for k, v in [("articles", []), ("ultima_cat", None), ("ultima_sync", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

cargar = buscar or st.session_state.ultima_cat != cat_label

if cargar:
    with st.spinner("⚡ Buscando noticias de ciberseguridad..."):
        try:
            arts = fetch_news(cat_label, page_size=num_noticias)
            if traducir_activo and arts:
                arts = traducir_lote(arts)
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
        f"<p style='font-size:0.62rem; color:rgba(0,255,136,0.35)'>"
        f"RESULTADOS: <span style='color:#00ff88'>{len(articles)}</span> &nbsp;·&nbsp; "
        f"ÚLTIMA SYNC: <span style='color:#00cfff'>{st.session_state.ultima_sync}</span>"
        f"</p>",
        unsafe_allow_html=True,
    )
    for art in articles:
        render_card(art, cat_label)

    st.markdown(
        "<p style='text-align:center; font-size:0.58rem; color:rgba(0,255,136,0.2); margin-top:1rem;'>"
        "◈ CYBERFEED · THEHACKERNEWS · BLEEPINGCOMPUTER · KREBSONSECURITY · Y MÁS ◈"
        "</p>",
        unsafe_allow_html=True,
    )
elif not cargar:
    st.info("Selecciona una categoría y pulsa ↻ BUSCAR.")
