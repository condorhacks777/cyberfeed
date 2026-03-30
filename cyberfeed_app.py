import streamlit as st
import requests
import json
from datetime import datetime, timedelta

st.set_page_config(page_title="CyberFeed", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

NEWSAPI_KEY = "51214314c9a148fa9cf8ee9d69771431"
GEMINI_KEY  = "AIzaSyANtAQiQg3wdvxw6XcQxOdv1cATbOvvC5w"
GEMINI_URL  = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"

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

CYBER_DOMAINS = (
    "thehackernews.com,bleepingcomputer.com,krebsonsecurity.com,"
    "threatpost.com,darkreading.com,securityweek.com,"
    "cyberscoop.com,wired.com,arstechnica.com,techcrunch.com,"
    "portswigger.net,helpnetsecurity.com,infosecurity-magazine.com,"
    "github.blog,offensive-security.com,kitploit.com"
)

CATEGORIAS = {
    "◈ TODAS":        "cybersecurity hacking (breach OR ransomware OR malware OR CVE OR exploit OR vulnerability)",
    "⚠ BRECHAS":      "(\"data breach\" OR \"data leak\" OR ransomware) (company OR hospital OR government OR million records)",
    "⚙ HERRAMIENTAS": "(\"new tool\" OR \"open source\" OR \"released\" OR \"github\" OR \"framework\") (pentest OR \"red team\" OR \"offensive security\" OR \"security tool\" OR \"hacking tool\" OR nmap OR metasploit OR burpsuite OR wireshark)",
    "☣ CVEs":         "(CVE OR vulnerability OR \"zero-day\" OR \"patch tuesday\") (critical OR high severity OR CVSS)",
    "◉ GRUPOS APT":   "(APT OR \"nation state\" OR \"state sponsored\") (hacking OR cyberespionage OR campaign OR attack)",
    "₿ CRYPTO":       "(crypto OR DeFi OR blockchain OR NFT OR exchange) (hack OR exploit OR stolen OR breach OR million)",
}

CAT_ICONS = {
    "◈ TODAS": "◈", "⚠ BRECHAS": "⚠", "⚙ HERRAMIENTAS": "⚙",
    "☣ CVEs": "☣", "◉ GRUPOS APT": "◉", "₿ CRYPTO": "₿",
}

# ── Traducción con Gemini ─────────────────────────────────────────────────────
def traducir_con_gemini(articulos: list) -> tuple:
    """
    Devuelve (articulos_traducidos, error_msg).
    error_msg es None si todo fue bien.
    """
    entrada = [
        {"id": i, "title": (a.get("title") or "")[:150], "desc": (a.get("description") or "")[:250]}
        for i, a in enumerate(articulos)
    ]

    prompt = f"""Eres un traductor especializado en ciberseguridad.
Traduce al español los títulos y descripciones. Mantén términos técnicos en inglés (CVE, ransomware, phishing, exploit, malware, APT, zero-day, DeFi, etc).
Devuelve SOLO el array JSON, sin markdown ni explicaciones.
Input: {json.dumps(entrada, ensure_ascii=False)}
Output format: [{{"id": 0, "title": "...", "desc": "..."}}, ...]"""

    try:
        r = requests.post(
            GEMINI_URL,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=25,
        )

        if r.status_code != 200:
            return articulos, f"Gemini error {r.status_code}: {r.text[:200]}"

        raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        raw = raw.strip().replace("```json", "").replace("```", "").strip()
        traducidos = json.loads(raw)

        mapa = {item["id"]: item for item in traducidos}
        resultado = []
        for i, art in enumerate(articulos):
            nuevo = dict(art)
            if i in mapa:
                nuevo["title"]       = mapa[i].get("title", art.get("title"))
                nuevo["description"] = mapa[i].get("desc",  art.get("description"))
            resultado.append(nuevo)
        return resultado, None

    except requests.exceptions.ConnectionError as e:
        return articulos, f"Error de conexión con Gemini: {str(e)[:150]}"
    except requests.exceptions.Timeout:
        return articulos, "Gemini tardó demasiado (timeout). Inténtalo de nuevo."
    except json.JSONDecodeError as e:
        return articulos, f"Gemini devolvió JSON inválido: {str(e)[:150]}"
    except Exception as e:
        return articulos, f"Error inesperado en Gemini: {str(e)[:150]}"


# ── NewsAPI ───────────────────────────────────────────────────────────────────
def fetch_news(cat_label: str, page_size: int = 10) -> list:
    r = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": CATEGORIAS[cat_label],
            "domains": CYBER_DOMAINS,
            "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": page_size,
            "apiKey": NEWSAPI_KEY,
        },
        timeout=10,
    )
    if r.status_code == 401:
        raise ValueError("API key de NewsAPI inválida.")
    if r.status_code == 429:
        raise ValueError("Límite de llamadas alcanzado. Inténtalo más tarde.")
    r.raise_for_status()
    arts = r.json().get("articles", [])
    for a in arts:
        if a.get("title") and " - " in a["title"]:
            a["title"] = a["title"].rsplit(" - ", 1)[0]
    return arts


def format_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        return iso[:10] if iso else "—"


def render_card(article: dict, cat_label: str):
    title  = article.get("title") or "Sin título"
    desc   = article.get("description") or "Sin descripción disponible."
    source = article.get("source", {}).get("name", "Desconocida")
    url    = article.get("url", "#")
    fecha  = format_date(article.get("publishedAt", ""))
    icon   = CAT_ICONS.get(cat_label, "◈")

    st.markdown(f"""
    <div class="news-card">
        <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; margin-bottom:0.4rem;">
            <span style="font-size:0.6rem; color:#00cfff;">{icon} {cat_label.split()[-1]}</span>
            <span style="font-size:0.6rem; color:rgba(0,255,136,0.4);">📅 {fecha}</span>
            <span style="font-size:0.6rem; color:rgba(0,207,255,0.5);">🔗 {source}</span>
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


# ── Cabecera ──────────────────────────────────────────────────────────────────
st.markdown("<h1 style='text-align:center'>◈ CYBER<span style='color:#ff2d2d'>FEED</span></h1>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align:center; font-size:0.65rem; color:rgba(0,255,136,0.4); letter-spacing:0.15em'>"
    f"TERMINAL DE INTELIGENCIA DE AMENAZAS &nbsp;·&nbsp; {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    f"</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Controles ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])
with col1:
    cat_label = st.selectbox("cat", list(CATEGORIAS.keys()), label_visibility="collapsed")
with col2:
    buscar = st.button("↻ BUSCAR")

num_noticias    = st.slider("Número de noticias", 5, 20, 10, 5)
traducir_activo = st.toggle("🌐 Traducir al español (Gemini)", value=True)

# ── Sesión ────────────────────────────────────────────────────────────────────
for k, v in [("articles", []), ("ultima_cat", None), ("ultima_sync", None), ("gemini_error", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

cargar = buscar or st.session_state.ultima_cat != cat_label

if cargar:
    st.session_state.gemini_error = None
    with st.spinner("⚡ Buscando noticias..."):
        try:
            arts = fetch_news(cat_label, page_size=num_noticias)
            if traducir_activo and arts:
                with st.spinner("🌐 Traduciendo con Gemini..."):
                    arts, err = traducir_con_gemini(arts)
                    st.session_state.gemini_error = err
            st.session_state.articles    = arts
            st.session_state.ultima_cat  = cat_label
            st.session_state.ultima_sync = datetime.now().strftime("%H:%M:%S")
        except ValueError as e:
            st.error(f"⚠ {e}")
            st.session_state.articles = []
        except Exception as e:
            st.error(f"⚠ Error: {e}")
            st.session_state.articles = []

# ── Mostrar error de Gemini si lo hay ────────────────────────────────────────
if st.session_state.gemini_error:
    st.warning(f"⚠ Traducción fallida — {st.session_state.gemini_error}")

# ── Resultados ────────────────────────────────────────────────────────────────
articles = st.session_state.articles

if articles:
    st.markdown(
        f"<p style='font-size:0.62rem; color:rgba(0,255,136,0.35)'>"
        f"RESULTADOS: <span style='color:#00ff88'>{len(articles)}</span> &nbsp;·&nbsp; "
        f"ÚLTIMA SYNC: <span style='color:#00cfff'>{st.session_state.ultima_sync}</span>"
        f"</p>",
        unsafe_allow_html=True,
    )
    for art in articles:
        render_card(art, cat_label)

    st.markdown(
        "<p style='text-align:center; font-size:0.58rem; color:rgba(0,255,136,0.2); margin-top:1rem;'>"
        "◈ CYBERFEED · THEHACKERNEWS · BLEEPINGCOMPUTER · KREBSONSECURITY · Y MÁS ◈"
        "</p>",
        unsafe_allow_html=True,
    )
elif not cargar:
    st.info("Selecciona una categoría y pulsa ↻ BUSCAR.")
