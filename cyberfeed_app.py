import streamlit as st
import requests
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── CLAVES ───────────────────────────────────────────────────────────────────
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "51214314c9a148fa9cf8ee9d69771431")

# ── TU CSS ORIGINAL (INTACTO) ────────────────────────────────────────────────
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

# ── DOMINIOS Y CATEGORÍAS ────────────────────────────────────────────────────
# Mezclamos dominios para asegurar que siempre haya resultados
CYBER_DOMAINS = "kitploit.com,thehackernews.com,bleepingcomputer.com,portswigger.net,darkreading.com,packetstormsecurity.com"

CATEGORIAS = {
    "◈ TODAS": "cybersecurity hacking",
    "⚠ BRECHAS": '("data breach" OR "ransomware") AND (hack OR victim)',
    "⚙ HERRAMIENTAS": '("github" OR "tool" OR "framework") AND ("offensive" OR "pentest" OR "exploit" OR "scanner" OR "repository")',
    "☣ CVEs": "(CVE OR vulnerability OR zero-day) AND (critical OR exploit)",
    "◉ GRUPOS APT": "(APT OR cyberespionage) AND (campaign OR attack)",
    "₿ CRYPTO": "(crypto OR DeFi OR blockchain) AND (hack OR exploit OR stolen)",
}

CAT_ICONS = {"◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙", "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿"}

# ── TRADUCCIÓN ───────────────────────────────────────────────────────────────
def traducir_articulos(articulos):
    translator = GoogleTranslator(source='en', target='es')
    for art in articulos:
        try:
            if art.get("title"): art["title"] = translator.translate(art["title"])
            if art.get("description"): art["description"] = translator.translate(art["description"][:400])
        except: continue
    return articulos

# ── BÚSQUEDA CORREGIDA ───────────────────────────────────────────────────────
def fetch_news(cat_label, page_size=30):
    try:
        r = requests.get("https://newsapi.org/v2/everything", params={
            "q": CATEGORIAS[cat_label],
            "domains": CYBER_DOMAINS,
            "language": "en",
            "pageSize": page_size,
            "apiKey": NEWSAPI_KEY,
            "sortBy": "publishedAt"
        }, timeout=10)
        
        raw_articles = r.json().get("articles", [])
        
        if cat_label == "⚙ HERRAMIENTAS":
            # Filtro inteligente: quitamos morralla de prensa pero dejamos pasar lo técnico
            ruido = ["newsletter", "boletín", "esta semana", "week in", "opinion", "versículo", "verso", "incident", "disponibilidad"]
            filtered = []
            for a in raw_articles:
                title = a.get("title", "").lower()
                # Si no tiene palabras de "columna de opinión", entra
                if not any(word in title for word in ruido):
                    filtered.append(a)
            return filtered[:10]
            
        return raw_articles[:10]
    except:
        return []

# ── CABECERA ─────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; font-size:0.65rem; color:rgba(0,255,136,0.4); letter-spacing:0.15em'>MONITOR DE INTELIGENCIA &nbsp;·&nbsp; {datetime.now().strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)
st.markdown("---")

# ── NAVEGACIÓN ───────────────────────────────────────────────────────────────
cat_label = st.selectbox("Cat", list(CATEGORIAS.keys()), label_visibility="collapsed")

if "ultima_cat" not in st.session_state or st.session_state.ultima_cat != cat_label:
    with st.spinner(f"⚡ ESCANEANDO SECTOR: {cat_label}..."):
        arts = fetch_news(cat_label)
        if arts:
            st.session_state.articles = traducir_articulos(arts)
            st.session_state.ultima_cat = cat_label
        else:
            st.session_state.articles = []

# ── RENDERIZADO ──────────────────────────────────────────────────────────────
if "articles" in st.session_state and st.session_state.articles:
    for art in st.session_state.articles:
        title = art.get("title") or "Sin título"
        desc = art.get("description") or "Sin descripción."
        source = art.get("source", {}).get("name", "Desconocida")
        url = art.get("url", "#")
        icon = CAT_ICONS.get(cat_label, "◈")

        st.markdown(f"""
        <div class="news-card">
            <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.4rem;">
                <span style="font-size:0.6rem; color:#00cfff;">{icon} {cat_label.split()[-1]}</span>
                <span style="font-size:0.6rem; color:rgba(0,255,136,0.4);">🔗 {source}</span>
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
else:
    st.markdown("<p style='text-align:center; opacity:0.3; margin-top:2rem;'>Buscando nuevas señales...</p>", unsafe_allow_html=True)

st.markdown(f"<p style='text-align:center; font-size:0.55rem; color:rgba(0,255,136,0.15); margin-top:2rem;'>SISTEMA ACTIVO</p>", unsafe_allow_html=True)
