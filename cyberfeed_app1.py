import streamlit as st
import feedparser
from datetime import datetime
from deep_translator import GoogleTranslator

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── TU DISEÑO HACKER (CSS) ───────────────────────────────────────────────────
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

# ── FUENTES RSS (GRATIS Y SIN KEYS) ──────────────────────────────────────────
FEEDS = {
    "◈ TODAS": ["https://www.bleepingcomputer.com/feed/", "https://thehackernews.com/feeds/posts/default"],
    "⚠ BRECHAS": ["https://www.bleepingcomputer.com/feed/", "https://krebsonsecurity.com/feed/"],
    "⚙ HERRAMIENTAS": ["https://www.kitploit.com/feeds/posts/default", "https://packetstormsecurity.com/feeds/public/"],
    "☣ CVEs": ["https://thehackernews.com/search/label/Vulnerability"],
    "◉ GRUPOS APT": ["https://thehackernews.com/search/label/APT"],
    "₿ CRYPTO": ["https://cointelegraph.com/rss/tag/hacking"]
}

CAT_ICONS = {"◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙", "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿"}

# ── LÓGICA DE TRADUCCIÓN (MEJORADA) ──────────────────────────────────────────
@st.cache_data(ttl=3600)
def traducir(texto):
    if not texto: return "Sin descripción."
    try:
        return GoogleTranslator(source='en', target='es').translate(texto[:400])
    except:
        return texto

# ── MOTOR RSS ────────────────────────────────────────────────────────────────
def fetch_news(cat_label):
    articles = []
    urls = FEEDS.get(cat_label, [])
    for url in urls:
        feed = feedparser.parse(url)
        for entry in feed.entries[:6]:
            articles.append({
                "title": entry.title,
                "description": entry.get("summary", entry.get("description", "")),
                "link": entry.link,
                "source": url.split(".")[1].capitalize()
            })
    return articles[:12]

# ── INTERFAZ ─────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; font-size:0.65rem; color:rgba(0,255,136,0.4); letter-spacing:0.15em'>SISTEMA RSS ACTIVO · {datetime.now().strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)
st.markdown("---")

cat_label = st.selectbox("Cat", list(FEEDS.keys()), label_visibility="collapsed")

with st.spinner("Sincronizando feeds..."):
    arts = fetch_news(cat_label)
    if arts:
        for art in arts:
            # Traducir título y descripción al vuelo
            t_title = traducir(art["title"])
            t_desc = traducir(art["description"])
            
            st.markdown(f"""
            <div class="news-card">
                <div style="display:flex; gap:0.5rem; align-items:center; margin-bottom:0.4rem;">
                    <span style="font-size:0.6rem; color:#00cfff;">{CAT_ICONS.get(cat_label, "◈")} {cat_label.split()[-1]}</span>
                    <span style="font-size:0.6rem; color:rgba(0,255,136,0.4);">🔗 {art['source']}</span>
                </div>
                <div style="font-size:0.88rem; color:#e8ffe8; font-family:'Share Tech Mono',monospace; line-height:1.4; margin-bottom:0.5rem; font-weight:bold;">{t_title}</div>
                <div style="font-size:0.76rem; color:rgba(200,255,200,0.75); line-height:1.7; margin-bottom:0.5rem;">{t_desc}</div>
                <a href="{art['link']}" target="_blank" style="color:#00ff88; font-size:0.72rem; text-decoration:none;">▶ Leer artículo completo</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No se detectan señales en este sector.")
