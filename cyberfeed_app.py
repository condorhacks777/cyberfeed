import streamlit as st
import requests
import json
import re
from datetime import datetime, timedelta

# ── CONFIGURACIÓN DE PÁGINA ──────────────────────────────────────────────────
st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# ── CREDENCIALES (Asegúrate de que GEMINI_KEY sea correcta) ──────────────────
NEWSAPI_KEY = st.secrets.get("NEWSAPI_KEY", "51214314c9a148fa9cf8ee9d69771431")
GEMINI_KEY  = st.secrets.get("GEMINI_KEY", "AIzaSyANtAQiQg3wdvxw6XcQxOdv1cATbOvvC5w")

# URL CAMBIADA A v1 (Más estable que v1beta para evitar 404)
# Y usamos gemini-1.5-flash que es el estándar de producción.
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"

# ── CSS (TU ESTÉTICA MANTENIDA) ──────────────────────────────────────────────
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

# ── MOTOR DE TRADUCCIÓN (BLINDADO) ───────────────────────────────────────────
def traducir_con_gemini(articulos):
    if not articulos: return [], None
    
    # Simplificamos al máximo el objeto para no confundir a la IA
    data_to_translate = []
    for i, a in enumerate(articulos):
        data_to_translate.append({
            "i": i,
            "t": (a.get("title") or "")[:100],
            "d": (a.get("description") or "")[:150]
        })

    # Prompt directo sin rodeos
    prompt_text = (
        "Translate this JSON array to Spanish. Keep technical terms like CVE, Exploit, Breach. "
        "Return ONLY the translated JSON array, no conversational text: "
        f"{json.dumps(data_to_translate)}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}]
    }

    try:
        # Petición con manejo de errores explícito
        response = requests.post(GEMINI_URL, json=payload, timeout=30)
        
        if response.status_code != 200:
            # Si da 404 aquí, es que el modelo gemini-1.5-flash no está activo en tu cuenta o región.
            return articulos, f"Error {response.status_code}: {response.text[:100]}"

        res_data = response.json()
        
        # Extraer el texto de la respuesta de Google
        try:
            raw_output = res_data['candidates'][0]['content']['parts'][0]['text']
            # Limpiar posibles backticks de markdown
            clean_json = re.sub(r"```json|```", "", raw_output).strip()
            translated_data = json.loads(clean_json)
            
            # Mapear de vuelta a los artículos originales
            for item in translated_data:
                idx = item.get("i")
                if idx is not None and idx < len(articulos):
                    articulos[idx]["title"] = item.get("t")
                    articulos[idx]["description"] = item.get("d")
            
            return articulos, None
        except (KeyError, IndexError, json.JSONDecodeError):
            return articulos, "La IA respondió pero el formato falló."

    except Exception as e:
        return articulos, f"Error de red: {str(e)[:50]}"

# ── LÓGICA DE NOTICIAS ───────────────────────────────────────────────────────
def get_news(topic):
    # Diccionario de búsqueda simplificado para evitar errores de NewsAPI
    q = {
        "◈ TODAS": "cybersecurity", "⚠ BRECHAS": "data breach", 
        "⚙ HERRAMIENTAS": "hacking tools", "☣ CVEs": "vulnerability CVE", 
        "◉ GRUPOS APT": "APT hacking", "₿ CRYPTO": "crypto hack"
    }.get(topic, "cybersecurity")

    url = f"https://newsapi.org/v2/everything?q={q}&language=en&pageSize=8&apiKey={NEWSAPI_KEY}"
    r = requests.get(url, timeout=10)
    if r.status_code != 200: return []
    return r.json().get("articles", [])

# ── INTERFAZ ─────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)

col1, col2 = st.columns([3, 1])
with col1:
    seleccion = st.selectbox("CAT", ["◈ TODAS", "⚠ BRECHAS", "⚙ HERRAMIENTAS", "☣ CVEs", "◉ GRUPOS APT", "₿ CRYPTO"], label_visibility="collapsed")
with col2:
    if st.button("↻ SCAN"):
        with st.spinner("📡 SCANNING..."):
            raw_arts = get_news(seleccion)
            if raw_arts:
                # Traducir
                final_arts, err = traducir_con_gemini(raw_arts)
                if err: st.warning(err)
                st.session_state.feed = final_arts
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
