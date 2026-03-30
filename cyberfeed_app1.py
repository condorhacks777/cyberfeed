import streamlit as st
import feedparser
import re
import urllib.request
from datetime import datetime
from deep_translator import GoogleTranslator

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── DISEÑO TERMINAL HACKER (CSS) ─────────────────────────────────────────────
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
h1 { font-family: 'Orbitron', monospace !important; color: #00ff88 !important; letter-spacing: 0.15em !important; text-shadow: 0 0 8px rgba(0,255,136,0.6); }
.stSelectbox > div > div {
    background: #000a03 !important;
    border: 1px solid rgba(0,255,136,0.3) !important;
    color: #00ff88 !important;
    border-radius: 0 !important;
}
.news-card {
    border: 1px solid rgba(0,255,136,0.2);
    border-left: 4px solid #00ff88;
    background: rgba(0,20,10,0.85);
    padding: 1.2rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.news-card:hover { border-color: #ffffff; background: rgba(0,40,20,0.9); transform: translateX(5px); }
hr { border-color: rgba(0,255,136,0.2) !important; }
p, li, span, label { color: rgba(200,255,200,0.9) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem !important; max-width: 800px !important; }
</style>
""", unsafe_allow_html=True)

# ── FUENTES DE INTELIGENCIA (FILTRADAS Y ESTABLES) ──────────────────────────
FEEDS = {
    "◈ TODAS": ["https://thehackernews.com/feeds/posts/default", "https://www.bleepingcomputer.com/feed/"],
    "⚠ BRECHAS": ["https://www.bleepingcomputer.com/feed/", "https://krebsonsecurity.com/feed/"],
    "☣ CVEs": [
        "https://seclists.org/rss/fulldisclosure.rss",
        "https://packetstormsecurity.com/feeds/advisories/",
        "https://www.vulnerability-lab.com/rss/rss.php"
    ],
    "◉ GRUPOS APT": ["https://thehackernews.com/search/label/APT", "https://www.mandiant.com/resources/blog/rss.xml"],
    "₿ CRYPTO": ["https://www.rekt.news/rss"]
}

CAT_ICONS = {"◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿"}

# ── PROCESAMIENTO ───────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def limpiar_y_traducir(texto):
    if not texto: return "Sin descripción técnica."
    clean = re.sub('<[^<]+?>', '', texto).strip()
    try:
        return GoogleTranslator(source='en', target='es').translate(clean[:400])
    except:
        return clean

def fetch_intel(cat_label):
    articles = []
    urls = FEEDS.get(cat_label, [])
    current_year = str(datetime.now().year)
    prev_year = str(datetime.now().year - 1)
    allowed_years = [current_year, prev_year]

    for url in urls:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read()
                feed = feedparser.parse(content)
            
            for entry in feed.entries[:12]:
                title = entry.title
                desc = entry.get("summary", entry.get("description", ""))
                content_lower = (title + desc).lower()
                
                if cat_label == "☣ CVEs":
                    cve_match = re.search(r'cve-\d{4}', content_lower)
                    if cve_match and cve_match.group().split('-')[1] not in allowed_years:
                        continue
                    if not any(k in content_lower for k in ["vulnerability", "exploit", "cve-", "apple-sa-"]):
                        continue

                source = url.split("//")[1].split("/")[0].replace("www.", "").upper()
                articles.append({"title": title, "description": desc, "link": entry.link, "source": source})
        except: continue
            
    unique = []
    seen = set()
    for a in articles:
        if a['title'].lower() not in seen:
            unique.append(a)
            seen.add(a['title'].lower())
    return unique[:12]

# ── CABECERA BY CONDORHACKS ──────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(f"""
<div style='text-align:center; margin-top:-0.5rem; margin-bottom:1.5rem;'>
    <p style='font-size:0.65rem; color:rgba(0,255,136,0.6); letter-spacing:0.15em; margin:0;'>
        INTEL ACTUALIZADA · {datetime.now().strftime('%H:%M')}
    </p>
    <p style='font-size:0.55rem; color:rgba(0,255,136,0.25); letter-spacing:0.25em; font-style:italic; margin-top:0.3rem; text-transform:uppercase;'>
        by condorhacks
    </p>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

cat_label = st.selectbox("Sector", list(FEEDS.keys()), label_visibility="collapsed")

with st.spinner("Estableciendo conexión segura..."):
    results = fetch_intel(cat_label)
    if results:
        for art in results:
            t_title = limpiar_y_traducir(art["title"])
            t_desc = limpiar_y_traducir(art["description"])
            st.markdown(f"""
            <div class="news-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.6rem;">
                    <span style="font-size:0.65rem; color:#00cfff; font-weight:bold;">{CAT_ICONS.get(cat_label, "◈")} {cat_label.split()[-1]}</span>
                    <span style="font-size:0.55rem; color:rgba(0,255,136,0.4);">{art['source']}</span>
                </div>
                <div style="font-size:1rem; color:#ffffff; font-weight:bold; line-height:1.3; margin-bottom:0.7rem;">{t_title}</div>
                <div style="font-size:0.82rem; color:rgba(200,255,200,0.8); line-height:1.6; margin-bottom:1rem;">{t_desc}</div>
                <div style="text-align:right;">
                    <a href="{art['link']}" target="_blank" style="color:#00ff88; font-size:0.7rem; text-decoration:none; border: 1px solid rgba(0,255,136,0.4); padding: 4px 10px; border-radius: 2px;">
                        ANALIZAR NODO ▶
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("⚠️ El sector seleccionado no responde. Intenta refrescar el nodo.")

st.markdown("<p style='text-align:center; font-size:0.55rem; color:rgba(0,255,136,0.1); margin-top:4rem;'>ENCRIPTACIÓN RSA-4096 ACTIVA | RSS FEED DIRECTO | NODO ALCALÁ</p>", unsafe_allow_html=True)
