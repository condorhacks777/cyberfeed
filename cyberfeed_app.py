import streamlit as st
import requests
import json
import re
from datetime import datetime, timedelta

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── GESTIÓN DE CLAVES ────────────────────────────────────────────────────────
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "51214314c9a148fa9cf8ee9d69771431")
GEMINI_KEY  = st.secrets.get("GEMINI_KEY", "AIzaSyANtAQiQg3wdvxw6XcQxOdv1cATbOvvC5w")

# URL REVISADA: v1beta/models/gemini-1.5-flash:generateContent
# El error 404 suele ser por una errata aquí o el uso de v1 en lugar de v1beta
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

# ── CSS PERSONALIZADO (MANTENIDO INTACTO) ────────────────────────────────────
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

# ── LÓGICA DE TRADUCCIÓN ─────────────────────────────────────────────────────
def traducir_con_gemini(articulos: list) -> tuple:
    if not articulos: return [], None
    
    # Payload ultra-ligero para asegurar respuesta rápida y evitar errores
    entrada = [{"id": i, "t": (a.get("title") or "")[:90], "d": (a.get("description") or "")[:140]} for i, a in enumerate(articulos)]

    prompt = f"Traduce al español técnico (mantén CVE, Ransomware, Exploit). Responde SOLO un array JSON: {json.dumps(entrada)}"

    # Payload con la estructura exacta que pide la API de Google
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        r = requests.post(GEMINI_URL, json=payload, timeout=25)
        
        if r.status_code != 200:
            return articulos, f"Gemini API Error {r.status_code}"

        res_json = r.json()
        # Navegamos por el dict de respuesta de Google
        if "candidates" not in res_json:
            return articulos, "Respuesta inesperada de la IA"
            
        raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
        
        # Limpieza de bloques de código markdown
        raw_text = re.sub(r"```json|```", "", raw_text).strip()
        match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        
        if not match: return articulos, "La IA no devolvió un JSON válido"
        
        traducidos = json.loads(match.group(0))
        mapa = {item["id"]: item for item in traducidos}
        
        resultado = []
        for i, art in enumerate(articulos):
            nuevo = dict(art)
            if i in mapa:
                nuevo["title"] = mapa[i].get("t", art.get("title"))
                nuevo["description"] = mapa[i].get("d", art.get("description"))
            resultado.append(nuevo)
        return resultado, None
    except Exception as e:
        return articulos, f"Error de conexión: {str(e)[:50]}"

# ── LÓGICA DE NOTICIAS ───────────────────────────────────────────────────────
def fetch_news(cat_label: str, page_size: int = 8) -> list:
    queries = {
        "◈ TODAS": "cybersecurity", "⚠ BRECHAS": "data breach ransomware", 
        "⚙ HERRAMIENTAS": "hacking tools github", "☣ CVEs": "vulnerability CVE critical", 
        "◉ GRUPOS APT": "APT hacking group", "₿ CRYPTO": "crypto exploit defi"
    }
    
    r = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": queries.get(cat_label, "cybersecurity"),
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": page_size,
            "apiKey": NEWSAPI_KEY,
        },
        timeout=12
    )
    r.raise_for_status()
    return r.json().get("articles", [])

def render_card(article: dict):
    title = article.get("title") or "Sin título"
    desc = article.get("description") or "Sin descripción."
    url = article.get("url", "#")
    st.markdown(f"""
    <div class="news-card">
        <div style="font-size:0.88rem; color:#e8ffe8; font-weight:bold; margin-bottom:0.5rem;">{title}</div>
        <div style="font-size:0.76rem; color:rgba(200,255,200,0.75); margin-bottom:0.5rem;">{desc}</div>
        <a href="{url}" target="_blank" style="color:#00ff88; font-size:0.72rem; text-decoration:none;">▶ Leer más</a>
    </div>
    """, unsafe_allow_html=True)

# ── INTERFAZ ─────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    cat = st.selectbox("C", ["◈ TODAS", "⚠ BRECHAS", "⚙ HERRAMIENTAS", "☣ CVEs", "◉ GRUPOS APT", "₿ CRYPTO"], label_visibility="collapsed")
with col2:
    buscar = st.button("↻ SCAN")

if "articulos" not in st.session_state: st.session_state.articulos = []

if buscar:
    with st.spinner("⚡ BUSCANDO Y TRADUCIENDO..."):
        try:
            # 1. Obtener noticias en inglés
            arts = fetch_news(cat)
            # 2. Traducir (esto ya no debería dar 404)
            arts_es, err = traducir_con_gemini(arts)
            if err: st.warning(err)
            st.session_state.articulos = arts_es
        except Exception as e:
            st.error(f"Error general: {e}")

for a in st.session_state.articulos:
    render_card(a)
