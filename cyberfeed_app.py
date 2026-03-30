import streamlit as st
import requests
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator # Librería de traducción gratuita y estable

# ── CONFIGURACIÓN ────────────────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── CLAVES ───────────────────────────────────────────────────────────────────
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "51214314c9a148fa9cf8ee9d69771431")

# ── CSS (TU ESTÉTICA ORIGINAL INTACTA) ───────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap');
html, body, [class*="stApp"] { background-color: #000a03 !important; color: #00ff88 !important; font-family: 'Share Tech Mono', monospace !important; }
body::after { content: ""; position: fixed; top:0; left:0; right:0; bottom:0; background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,136,0.012) 2px, rgba(0,255,136,0.012) 4px); pointer-events: none; z-index: 9999; }
h1 { font-family: 'Orbitron', monospace !important; color: #00ff88 !important; letter-spacing: 0.15em !important; }
.stButton > button { background: transparent !important; border: 1px solid #00ff88 !important; color: #00ff88 !important; border-radius: 0 !important; width: 100% !important; }
.news-card { border: 1px solid rgba(0,255,136,0.2); border-left: 3px solid #00ff88; background: rgba(0,10,5,0.85); padding: 1rem; margin-bottom: 0.6rem; }
a { color: #00ff88 !important; text-decoration: none; font-size: 0.75rem; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── NUEVA LÓGICA DE TRADUCCIÓN (ESTABLE Y GRATIS) ────────────────────────────
def traducir_articulos(articulos):
    if not articulos: return []
    
    translator = GoogleTranslator(source='en', target='es')
    
    for art in articulos:
        try:
            # Traducimos título y descripción por separado
            if art.get("title"):
                art["title"] = translator.translate(art["title"])
            if art.get("description"):
                # Limitamos caracteres para que no tarde mil años
                desc = art["description"][:400] 
                art["description"] = translator.translate(desc)
        except Exception:
            # Si falla la traducción de uno, seguimos con el siguiente en inglés
            continue
    return articulos

# ── LÓGICA DE NOTICIAS ───────────────────────────────────────────────────────
def get_news(topic):
    q = {
        "◈ TODAS": "cybersecurity", "⚠ BRECHAS": "data breach", 
        "⚙ HERRAMIENTAS": "hacking tools", "☣ CVEs": "vulnerability CVE", 
        "◉ GRUPOS APT": "APT hacking", "₿ CRYPTO": "crypto hack"
    }.get(topic, "cybersecurity")

    url = f"https://newsapi.org/v2/everything?q={q}&language=en&pageSize=8&apiKey={NEWSAPI_KEY}"
    try:
        r = requests.get(url, timeout=10)
        return r.json().get("articles", []) if r.status_code == 200 else []
    except:
        return []

# ── INTERFAZ ─────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    seleccion = st.selectbox("CAT", ["◈ TODAS", "⚠ BRECHAS", "⚙ HERRAMIENTAS", "☣ CVEs", "◉ GRUPOS APT", "₿ CRYPTO"], label_visibility="collapsed")
with col2:
    if st.button("↻ SCAN"):
        with st.spinner("📡 SCANNING & TRANSLATING..."):
            raw_arts = get_news(seleccion)
            if raw_arts:
                # Usamos la nueva traducción estable
                st.session_state.feed = traducir_articulos(raw_arts)
            else:
                st.error("No se encontraron noticias.")

if "feed" in st.session_state:
    for a in st.session_state.feed:
        st.markdown(f"""
        <div class="news-card">
            <div style="font-weight:bold; font-size:0.95rem; margin-bottom:0.4rem;">{a.get('title')}</div>
            <div style="font-size:0.8rem; color:rgba(200,255,200,0.7); margin-bottom:0.6rem;">{a.get('description')}</div>
            <a href="{a.get('url')}" target="_blank">▶ LEER MÁS</a>
        </div>
        """, unsafe_allow_html=True)
