import streamlit as st
import feedparser
import re
from datetime import datetime
from deep_translator import GoogleTranslator

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── DISEÑO HACKER (CSS) ──────────────────────────────────────────────────────
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
h1 { font-family: 'Orbitron', monospace !important; color: #00ff88 !important; letter-spacing: 0.15em !important; text-shadow: 0 0 10px rgba(0,255,136,0.5); }
.stSelectbox > div > div {
    background: #000a03 !important;
    border: 1px solid rgba(0,255,136,0.3) !important;
    color: #00ff88 !important;
    border-radius: 0 !important;
}
.news-card {
    border: 1px solid rgba(0,255,136,0.2);
    border-left: 3px solid #00ff88;
    background: rgba(0,15,5,0.9);
    padding: 1.2rem;
    margin-bottom: 0.8rem;
    transition: 0.3s;
}
.news-card:hover { border-color: #00ff88; background: rgba(0,25,10,0.9); }
hr { border-color: rgba(0,255,136,0.15) !important; }
p, li, span, label { color: rgba(200,255,200,0.85) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem !important; max-width: 750px !important; }
</style>
""", unsafe_allow_html=True)

# ── FUENTES RSS REFORZADAS ──────────────────────────────────────────────────
FEEDS = {
    "◈ TODAS": [
        "https://thehackernews.com/feeds/posts/default",
        "https://www.bleepingcomputer.com/feed/"
    ],
    "⚠ BRECHAS": [
        "https://www.bleepingcomputer.com/feed/",
        "https://krebsonsecurity.com/feed/"
    ],
    "⚙ HERRAMIENTAS": [
        "https://www.kitploit.com/feeds/posts/default",
        "https://packetstormsecurity.com/feeds/public/",
        "https://www.toolswatch.org/feed/"
    ],
    "☣ CVEs": [
        "https://thehackernews.com/search/label/Vulnerability",
        "https://www.darkreading.com/rss.xml"
    ],
    "◉ GRUPOS APT": [
        "https://thehackernews.com/search/label/APT",
        "https://www.scmagazine.com/rss"
    ],
    "₿ CRYPTO": [
        "https://cointelegraph.com/rss/tag/hacking",
        "https://www.rekt.news/rss"
    ]
}

CAT_ICONS = {"◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙", "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿"}

# ── LÓGICA DE TRADUCCIÓN Y LIMPIEZA ──────────────────────────────────────────
@st.cache_data(ttl=1800) # Caché de 30 minutos para no saturar
def procesar_texto(texto, traducir=True):
    if not texto: return "Sin información disponible."
    # Limpiar etiquetas HTML que a veces rompen el RSS
    texto_limpio = re.sub('<[^<]+?>', '', texto)
    if traducir:
        try:
            return GoogleTranslator(source='en', target='es').translate(texto_limpio[:400])
        except:
            return texto_limpio
    return texto_limpio

# ── MOTOR RSS ────────────────────────────────────────────────────────────────
def fetch_news(cat_label):
    articles = []
    urls = FEEDS.get(cat_label, [])
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:7]:
                # Extraer nombre limpio de la fuente
                source_name = url.split("//")[1].split("/")[0].replace("www.", "")
                
                articles.append({
                    "title": entry.title,
                    "description": entry.get("summary", entry.get("description", "")),
                    "link": entry.link,
                    "source": source_name.upper()
                })
        except:
            continue
            
    # Evitar duplicados por título
    seen = set()
    unique_arts = []
    for a in articles:
        if a['title'] not in seen:
            unique_arts.append(a)
            seen.add(a['title'])
            
    return unique_arts[:12]

# ── CABECERA ─────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; font-size:0.65rem; color:rgba(0,255,136,0.4); letter-spacing:0.15em'>RSS PROTOCOL v2.0 · {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>", unsafe_allow_html=True)
st.markdown("---")

# ── NAVEGACIÓN ───────────────────────────────────────────────────────────────
cat_label = st.selectbox("Sector", list(FEEDS.keys()), label_visibility="collapsed")

with st.spinner("Sincronizando con fuentes externas..."):
    arts = fetch_news(cat_label)
    
    if arts:
        for art in arts:
            # Procesar traducción y limpieza
            clean_title = procesar_texto(art["title"])
            clean_desc = procesar_texto(art["description"])
            
            st.markdown(f"""
            <div class="news-card">
                <div style="display:flex; gap:0.6rem; align-items:center; margin-bottom:0.5rem;">
                    <span style="font-size:0.65rem; color:#00cfff; font-weight:bold;">{CAT_ICONS.get(cat_label, "◈")} {cat_label.split()[-1]}</span>
                    <span style="font-size:0.6rem; color:rgba(0,255,136,0.5);">|</span>
                    <span style="font-size:0.6rem; color:rgba(0,255,136,0.5);">SOURCE: {art['source']}</span>
                </div>
                <div style="font-size:0.95rem; color:#e8ffe8; font-weight:bold; line-height:1.4; margin-bottom:0.6rem;">
                    {clean_title}
                </div>
                <div style="font-size:0.8rem; color:rgba(200,255,200,0.7); line-height:1.6; margin-bottom:0.8rem;">
                    {clean_desc}
                </div>
                <a href="{art['link']}" target="_blank" style="color:#00ff88; font-size:0.75rem; text-decoration:none; border: 1px solid #00ff88; padding: 3px 8px; border-radius: 3px;">
                    ACCEDER AL NODO ▶
                </a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("⚠️ Error de enlace: No se detectan señales en este sector. Intenta refrescar en unos segundos.")

st.markdown("<p style='text-align:center; font-size:0.55rem; color:rgba(0,255,136,0.1); margin-top:3rem;'>SISTEMA DE DISTRIBUCIÓN RSS INDEPENDIENTE - SIN FILTROS DE API</p>", unsafe_allow_html=True)
