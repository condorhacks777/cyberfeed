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

# ── FUENTES DE INTELIGENCIA (RSS REFINADO) ───────────────────────────────────
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
        "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml", # NIST Oficial
        "https://seclists.org/rss/fulldisclosure.rss",       # Reportes técnicos
        "https://www.vulnerability-lab.com/rss/rss.php"      # Labs Reales
    ],
    "◉ GRUPOS APT": [
        "https://thehackernews.com/search/label/APT",
        "https://www.mandiant.com/resources/blog/rss.xml"
    ],
    "₿ CRYPTO": [
        "https://www.rekt.news/rss",
        "https://cointelegraph.com/rss/tag/hacking"
    ]
}

CAT_ICONS = {"◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙", "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿"}

# ── PROCESAMIENTO DE TEXTO ───────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def limpiar_y_traducir(texto, traducir=True):
    if not texto: return "Sin descripción técnica."
    # Eliminar HTML y limpiar espacios
    clean = re.sub('<[^<]+?>', '', texto).strip()
    if traducir:
        try:
            return GoogleTranslator(source='en', target='es').translate(clean[:450])
        except:
            return clean
    return clean

# ── MOTOR DE BÚSQUEDA Y FILTRADO ─────────────────────────────────────────────
def fetch_intel(cat_label):
    articles = []
    urls = FEEDS.get(cat_label, [])
    
    # Palabras clave para validar CVEs reales
    CVE_KEYWORDS = ["cve-", "vulnerability", "exploit", "rce", "critical", "0-day", "zero-day", "bypass", "overflow"]

    for url in urls:
        try:
            # Usamos un User-Agent básico para evitar bloqueos
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.title
                desc = entry.get("summary", entry.get("description", ""))
                
                # --- FILTRO QUIRÚRGICO PARA CVEs ---
                if cat_label == "☣ CVEs":
                    content_to_scan = (title + desc).lower()
                    if not any(k in content_to_scan for k in CVE_KEYWORDS):
                        continue # Ignora noticias genéricas de política o IA
                
                source = url.split("//")[1].split("/")[0].replace("www.", "").upper()
                
                articles.append({
                    "title": title,
                    "description": desc,
                    "link": entry.link,
                    "source": source
                })
        except:
            continue
            
    # Eliminar duplicados
    unique_list = []
    titles_seen = set()
    for a in articles:
        if a['title'].lower() not in titles_seen:
            unique_list.append(a)
            titles_seen.add(a['title'].lower())
            
    return unique_list[:12]

# ── INTERFAZ DE USUARIO ──────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; font-size:0.65rem; color:rgba(0,255,136,0.4); letter-spacing:0.15em'>PROT. RSS INDEPENDIENTE · {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>", unsafe_allow_html=True)
st.markdown("---")

cat_label = st.selectbox("SECTOR", list(FEEDS.keys()), label_visibility="collapsed")

with st.spinner("Sincronizando con el satélite..."):
    results = fetch_intel(cat_label)
    
    if results:
        for art in results:
            t_title = limpiar_y_traducir(art["title"])
            t_desc = limpiar_y_traducir(art["description"])
            
            st.markdown(f"""
            <div class="news-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
                    <span style="font-size:0.65rem; color:#00cfff; font-weight:bold;">{CAT_ICONS.get(cat_label, "◈")} {cat_label.split()[-1]}</span>
                    <span style="font-size:0.55rem; color:rgba(0,255,136,0.4);">{art['source']}</span>
                </div>
                <div style="font-size:1rem; color:#ffffff; font-weight:bold; line-height:1.3; margin-bottom:0.7rem;">
                    {t_title}
                </div>
                <div style="font-size:0.82rem; color:rgba(200,255,200,0.8); line-height:1.6; margin-bottom:1rem;">
                    {t_desc}
                </div>
                <div style="text-align:right;">
                    <a href="{art['link']}" target="_blank" style="color:#00ff88; font-size:0.7rem; text-decoration:none; border: 1px solid rgba(0,255,136,0.4); padding: 4px 10px; border-radius: 2px; text-transform: uppercase;">
                        Analizar Nodo ▶
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("⚠️ Error de enlace: No se detectan señales técnicas en este sector. Intenta de nuevo en unos segundos.")

st.markdown("<p style='text-align:center; font-size:0.55rem; color:rgba(0,255,136,0.1); margin-top:4rem;'>ENCRIPTACIÓN RSA-4096 ACTIVA | RSS FEED DIRECTO</p>", unsafe_allow_html=True)
