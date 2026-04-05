import streamlit as st
import feedparser
import re
import urllib.request
from datetime import datetime
import pytz
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
.kofi-banner {
    display: flex; align-items: center; justify-content: center; gap: 0.6rem;
    border: 1px solid rgba(255,94,10,0.3);
    background: rgba(255,94,10,0.06);
    padding: 0.6rem 1rem;
    margin-bottom: 1rem;
    text-decoration: none;
}
hr { border-color: rgba(0,255,136,0.2) !important; }
p, li, span, label { color: rgba(200,255,200,0.9) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem !important; max-width: 800px !important; }
</style>
""", unsafe_allow_html=True)

# ── FUENTES RSS POR CATEGORÍA ─────────────────────────────────────────────────
FEEDS = {
    "◈ TODAS": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.bleepingcomputer.com/feed/",
    ],
    "⚠ BRECHAS": [
        "https://www.bleepingcomputer.com/feed/",
        "https://krebsonsecurity.com/feed/",
        "https://hackread.com/feed/",
    ],
    "⚙ HERRAMIENTAS": [
        "https://www.kitploit.com/feeds/posts/default",
        "https://blog.rapid7.com/rss/",
        "https://www.rcesecurity.com/feed/",
        "https://feeds.feedburner.com/TheHackersNews",
    ],
    "☣ CVEs": [
        "https://www.cisa.gov/cybersecurity-advisories/all.xml",
        "https://blog.rapid7.com/rss/",
        "https://packetstormsecurity.com/feeds/advisories/",
    ],
    "◉ GRUPOS APT": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.mandiant.com/resources/blog/rss.xml",
        "https://cyble.com/feed/",
    ],
    "₿ CRYPTO": [
        "https://rekt.news/rss/feed.xml",
        "https://protos.com/feed/",
        "https://hackread.com/feed/",
    ],
}

FILTROS = {
    "◈ TODAS":        ["hack", "breach", "malware", "ransomware", "vulnerability", "exploit", "cve", "attack", "cyber"],
    "⚠ BRECHAS":      ["breach", "leak", "hack", "ransomware", "stolen", "exposed", "million records", "data"],
    "⚙ HERRAMIENTAS": ["tool", "framework", "exploit", "release", "github", "pentest", "scanner", "payload", "script", "offensive", "red team"],
    "☣ CVEs":         ["cve", "vulnerability", "patch", "advisory", "zero-day", "rce", "exploit", "critical", "severity"],
    "◉ GRUPOS APT":   ["apt", "nation", "state", "espionage", "campaign", "actor", "group", "attack", "threat"],
    "₿ CRYPTO":       ["crypto", "defi", "blockchain", "hack", "exploit", "stolen", "web3", "nft", "exchange", "rekt", "million"],
}

CAT_ICONS = {
    "◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙",
    "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿"
}

# ── TRADUCCIÓN CON CACHÉ ─────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def traducir(texto: str) -> str:
    if not texto:
        return "Sin descripción disponible."
    clean = re.sub('<[^<]+?>', '', texto).strip()[:400]
    try:
        return GoogleTranslator(source='en', target='es').translate(clean)
    except Exception:
        return clean

# ── FETCH RSS CON CACHÉ Y FILTRADO ───────────────────────────────────────────
@st.cache_data(ttl=600)
def fetch_intel(cat_label: str) -> list:
    articles = []
    urls = FEEDS.get(cat_label, [])
    keywords = FILTROS.get(cat_label, [])
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*',
    }
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                content = response.read()
            feed = feedparser.parse(content)
            for entry in feed.entries[:15]:
                title = entry.get("title", "")
                desc  = entry.get("summary", entry.get("description", ""))
                link  = entry.get("link", "#")
                if keywords and not any(k in (title + " " + desc).lower() for k in keywords):
                    continue
                source = url.split("//")[1].split("/")[0].replace("www.", "").upper()
                articles.append({"title": title, "description": desc, "link": link, "source": source})
        except Exception:
            continue
    seen, unique = set(), []
    for a in articles:
        key = a["title"].lower().strip()
        if key not in seen and key:
            unique.append(a)
            seen.add(key)
    return unique[:12]

# ── CABECERA ─────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)

madrid_tz = pytz.timezone('Europe/Madrid')
hora_local = datetime.now(madrid_tz).strftime('%H:%M')

st.markdown(f"""
<div style='text-align:center; margin-top:-0.5rem; margin-bottom:1rem;'>
    <p style='font-size:0.65rem; color:rgba(0,255,136,0.6); letter-spacing:0.15em; margin:0;'>
        INTEL ACTUALIZADA · {hora_local}
    </p>
    <p style='font-size:0.55rem; color:rgba(0,255,136,0.25); letter-spacing:0.25em; font-style:italic; margin-top:0.3rem; text-transform:uppercase;'>
        by condorhacks
    </p>
</div>
""", unsafe_allow_html=True)

# ── KO-FI BANNER ─────────────────────────────────────────────────────────────
st.markdown("""
<a href="https://ko-fi.com/condorhacks" target="_blank" class="kofi-banner">
    <span style="font-size:1.1rem;">☕</span>
    <span style="font-size:0.68rem; color:rgba(255,140,60,0.9); letter-spacing:0.1em;">
        ¿TE RESULTA ÚTIL? APOYA CYBERFEED EN KO-FI
    </span>
    <span style="font-size:0.6rem; color:rgba(255,94,10,0.5); letter-spacing:0.08em;">→ ko-fi.com/condorhacks</span>
</a>
""", unsafe_allow_html=True)

st.markdown("---")

# ── SELECTOR + BOTÓN REFRESCO ────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    cat_label = st.selectbox("Sector", list(FEEDS.keys()), label_visibility="collapsed")
with col2:
    if st.button("↻", help="Refrescar noticias"):
        st.cache_data.clear()
        st.rerun()

# ── CARGA Y RENDERIZADO ───────────────────────────────────────────────────────
with st.spinner("Estableciendo conexión segura con el nodo..."):
    results = fetch_intel(cat_label)

if results:
    st.markdown(
        f"<p style='font-size:0.62rem; color:rgba(0,255,136,0.35); margin-bottom:1rem;'>"
        f"NODOS ACTIVOS: <span style='color:#00ff88'>{len(results)}</span> &nbsp;·&nbsp; "
        f"FUENTES: <span style='color:#00cfff'>{len(FEEDS[cat_label])}</span>"
        f"</p>",
        unsafe_allow_html=True,
    )
    for art in results:
        t_title = traducir(art["title"])
        t_desc  = traducir(art["description"])
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
    st.error("⚠️ El sector seleccionado no responde. Pulsa ↻ para refrescar.")

# ── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center; margin-top:3rem;'>
    <a href="https://ko-fi.com/condorhacks" target="_blank"
       style="color:rgba(255,94,10,0.45); font-size:0.55rem; text-decoration:none; letter-spacing:0.2em;">
        ☕ APOYA EL PROYECTO · KO-FI.COM/CONDORHACKS
    </a>
    <p style='font-size:0.5rem; color:rgba(0,255,136,0.1); margin-top:0.5rem; letter-spacing:0.15em;'>
        ENCRIPTACIÓN RSA-4096 ACTIVA | RSS FEED DIRECTO | NODO ALCALÁ
    </p>
</div>
""", unsafe_allow_html=True)
