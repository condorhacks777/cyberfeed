import streamlit as st
import feedparser
import re
from datetime import datetime
from deep_translator import GoogleTranslator

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── DISEÑO TERMINAL HACKER ───────────────────────────────────────────────────
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
.news-card {
    border: 1px solid rgba(0,255,136,0.2);
    border-left: 4px solid #00ff88;
    background: rgba(0,20,10,0.85);
    padding: 1.2rem;
    margin-bottom: 1rem;
}
.stSelectbox > div > div { background: #000a03 !important; color: #00ff88 !important; border: 1px solid rgba(0,255,136,0.3) !important; }
p, li, span, label { color: rgba(200,255,200,0.9) !important; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── FUENTES ACTUALIZADAS (2026 READY) ────────────────────────────────────────
FEEDS = {
    "◈ TODAS": ["https://thehackernews.com/feeds/posts/default", "https://www.bleepingcomputer.com/feed/"],
    "⚠ BRECHAS": ["https://www.bleepingcomputer.com/feed/", "https://krebsonsecurity.com/feed/"],
    "⚙ HERRAMIENTAS": ["https://www.kitploit.com/feeds/posts/default", "https://packetstormsecurity.com/feeds/public/"],
    "☣ CVEs": [
        "https://seclists.org/rss/fulldisclosure.rss",  # Avisos frescos (Apple, Cisco, etc)
        "https://www.vulnerability-lab.com/rss/rss.php", # Últimos hallazgos
        "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml" # NIST (Filtrado por año)
    ],
    "◉ GRUPOS APT": ["https://thehackernews.com/search/label/APT", "https://www.mandiant.com/resources/blog/rss.xml"],
    "₿ CRYPTO": ["https://www.rekt.news/rss"]
}

CAT_ICONS = {"◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙", "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿"}

# ── PROCESAMIENTO ───────────────────────────────────────────────────────────
@st.cache_data(ttl=1200)
def limpiar_y_traducir(texto):
    if not texto: return "Sin descripción."
    clean = re.sub('<[^<]+?>', '', texto).strip()
    try:
        return GoogleTranslator(source='en', target='es').translate(clean[:400])
    except:
        return clean

def fetch_intel(cat_label):
    articles = []
    urls = FEEDS.get(cat_label, [])
    
    # SOLO QUEREMOS ESTOS AÑOS
    YEARS_ALLOWED = ["2025", "2026"] 

    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                title = entry.title
                desc = entry.get("summary", entry.get("description", ""))
                
                # --- FILTRO CRONOLÓGICO PARA CVEs ---
                if cat_label == "☣ CVEs":
                    content = (title + desc).lower()
                    # Si menciona un CVE antiguo (ej: CVE-2017), lo descartamos
                    if "cve-" in content:
                        if not any(year in content for year in YEARS_ALLOWED):
                            continue
                    # Si no menciona CVE ni vulnerabilidad técnica reciente, fuera
                    if not any(k in content for k in ["vulnerability", "exploit", "cve-", "apple-sa-"]):
                        continue

                source = url.split("//")[1].split("/")[0].replace("www.", "").upper()
                articles.append({"title": title, "description": desc, "link": entry.link, "source": source})
        except: continue
            
    # Únicos
    unique = []
    seen = set()
    for a in articles:
        if a['title'].lower() not in seen:
            unique.append(a)
            seen.add(a['title'].lower())
    return unique[:12]

# ── UI ───────────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(f"<p style='text-align:center; font-size:0.65rem; color:rgba(0,255,136,0.4);'>INTEL ACTUALIZADA · {datetime.now().strftime('%H:%M')}</p>", unsafe_allow_html=True)
st.markdown("---")

cat_label = st.selectbox("Sector", list(FEEDS.keys()), label_visibility="collapsed")

with st.spinner("Filtrando vulnerabilidades obsoletas..."):
    results = fetch_intel(cat_label)
    if results:
        for art in results:
            t_title = limpiar_y_traducir(art["title"])
            t_desc = limpiar_y_traducir(art["description"])
            st.markdown(f"""
            <div class="news-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
                    <span style="font-size:0.65rem; color:#00cfff; font-weight:bold;">{CAT_ICONS.get(cat_label, "◈")} {cat_label.split()[-1]}</span>
                    <span style="font-size:0.55rem; color:rgba(0,255,136,0.4);">{art['source']}</span>
                </div>
                <div style="font-size:1rem; font-weight:bold; margin-bottom:0.6rem;">{t_title}</div>
                <div style="font-size:0.8rem; color:rgba(200,255,200,0.7); line-height:1.5; margin-bottom:0.8rem;">{t_desc}</div>
                <a href="{art['link']}" target="_blank" style="color:#00ff88; font-size:0.7rem; text-decoration:none; border: 1px solid #00ff88; padding: 3px 8px;">ANALIZAR NODO ▶</a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("No hay vulnerabilidades críticas detectadas en las últimas 48h.")
