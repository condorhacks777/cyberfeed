import re
import html
from datetime import datetime, timezone
from urllib.parse import urlparse
import feedparser
import requests
import streamlit as st
# ==========================================
# CYBERFEED | CONDORHACKS
# ==========================================
st.set_page_config(
    page_title="CyberFeed | CondorHacks",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
SOURCES = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
}
CATEGORIES = {
    "Vulnerabilidades": [
        "cve-", "vulnerability", "vulnerabilidad", "exploit",
        "zero-day", "zero day", "patch", "parche",
    ],
    "Malware": [
        "malware", "ransomware", "trojan", "botnet",
        "infostealer", "spyware",
    ],
    "Hacking": [
        "hacker", "hacking", "phishing", "cyberattack",
        "ciberataque", "data breach", "filtración",
    ],
    "Inteligencia artificial": [
        "artificial intelligence", "machine learning",
        "inteligencia artificial", "llm",
    ],
}
# ==========================================
# DISEÑO
# ==========================================
st.markdown("""
<style>
.stApp {
    background: #080d18;
    color: #e6edf7;
}
.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}
[data-testid="stSidebar"] {
    background: #0c1422;
    border-right: 1px solid #223147;
}
.hero {
    background: linear-gradient(120deg, #101d31, #0b302d);
    border: 1px solid #24453f;
    padding: 28px;
    border-radius: 18px;
    margin-bottom: 24px;
}
.hero h1 {
    color: #f1f7ff;
    font-size: 2.5rem;
    margin: 0;
}
.hero p {
    color: #a7bacd;
    margin-bottom: 0;
}
.metric {
    background: #101827;
    border: 1px solid #223147;
    padding: 18px;
    border-radius: 14px;
    min-height: 95px;
}
.metric-label {
    color: #9bacbf;
    font-size: .9rem;
}
.metric-value {
    color: #65e6bd;
    font-size: 1.7rem;
    font-weight: 700;
}
.news-card {
    background: #101827;
    border: 1px solid #243248;
    border-radius: 14px;
    padding: 18px;
    margin: 12px 0;
}
.news-meta {
    color: #91a5bc;
    font-size: .85rem;
}
.news-summary {
    color: #c1ccda;
    line-height: 1.6;
}
div.stButton > button {
    border-radius: 9px;
}
footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)
# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def clean_text(value):
    """Limpia HTML y normaliza espacios."""
    value = re.sub(r"<[^>]*>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()
def valid_url(url):
    try:
        parsed = urlparse(url or "")
        return (
            parsed.scheme in ("https", "http")
            and bool(parsed.netloc)
        )
    except ValueError:
        return False
def detect_category(title, summary):
    text = f"{title} {summary}".lower()
    for category, keywords in CATEGORIES.items():
        if any(word in text for word in keywords):
            return category
    return "General"
def parse_date(entry):
    try:
        parsed = (
            entry.get("published_parsed")
            or entry.get("updated_parsed")
        )
        if parsed:
            return datetime(
                *parsed[:6], tzinfo=timezone.utc
            )
    except (TypeError, ValueError, OverflowError):
        pass
    return None
def display_date(value):
    if not value:
        return "Fecha no disponible"
    return value.strftime("%d/%m/%Y %H:%M UTC")
# ==========================================
# DESCARGA RSS CON TIMEOUT
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def load_news(source_names):
    articles = []
    statuses = {}
    for source_name in source_names:
        feed_url = SOURCES.get(source_name)
        if not feed_url:
            continue
        try:
            response = requests.get(
                feed_url,
                timeout=(3, 8),
                headers={"User-Agent": "CyberFeed/1.0"},
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if not feed.entries:
                statuses[source_name] = "Sin noticias"
                continue
            count_before = len(articles)
            for entry in feed.entries:
                title = clean_text(
                    entry.get("title", "Sin título")
                )
                link = entry.get("link", "")
                if not title or not valid_url(link):
                    continue
                summary = clean_text(
                    entry.get(
                        "summary",
                        entry.get("description", ""),
                    )
                )
                articles.append({
                    "title": title,
                    "link": link,
                    "summary": summary[:1000],
                    "source": source_name,
                    "published": parse_date(entry),
                    "category": detect_category(title, summary),
                })
            count = len(articles) - count_before
            statuses[source_name] = f"{count} noticias"
        except requests.RequestException:
            statuses[source_name] = "Error de conexión"
        except Exception:
            statuses[source_name] = "Error al leer el feed"
    # Eliminar duplicados por enlace
    unique = {}
    for article in articles:
        unique[article["link"]] = article
    result = list(unique.values())
    # Orden cronológico; los artículos sin fecha van al final
    result.sort(
        key=lambda item: (
            item["published"] is not None,
            item["published"] or datetime.min.replace(
                tzinfo=timezone.utc
            ),
        ),
        reverse=True,
    )
    return result, statuses
# ==========================================
# BARRA LATERAL
# ==========================================
with st.sidebar:
    st.markdown("## 🛡️ CyberFeed")
    st.caption("CONDORHACKS · SECURITY INTELLIGENCE")
    st.divider()
    selected_sources = st.multiselect(
        "Fuentes RSS",
        options=list(SOURCES.keys()),
        default=list(SOURCES.keys()),
    )
    category_options = ["Todas"] + list(CATEGORIES.keys()) + [
        "General"
    ]
    selected_category = st.selectbox(
        "Categoría",
        category_options,
    )
    search_query = st.text_input(
        "Buscar noticias",
        placeholder="CVE, ransomware, phishing...",
    ).strip().lower()
    max_articles = st.selectbox(
        "Noticias mostradas",
        [10, 20, 30, 50],
        index=1,
    )
    st.divider()
    if st.button("🔄 Actualizar noticias", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Caché de noticias: 10 minutos")
    st.caption("CyberFeed · CondorHacks")
# ==========================================
# CABECERA PRINCIPAL
# ==========================================
st.markdown("""
<div class="hero">
    <h1>CyberFeed <span style="color:#65e6bd">/</span> Dashboard</h1>
    <p>
        Tu centro de noticias de ciberseguridad.
        Amenazas, vulnerabilidades e investigación en un solo lugar.
    </p>
</div>
""", unsafe_allow_html=True)
# ==========================================
# CARGA Y FILTRADO
# ==========================================
if not selected_sources:
    st.info("Selecciona al menos una fuente en el menú lateral.")
    st.stop()
with st.spinner("Consultando fuentes de ciberseguridad..."):
    articles, statuses = load_news(tuple(selected_sources))
# Filtro por categoría
if selected_category != "Todas":
    articles = [
        item for item in articles
        if item["category"] == selected_category
    ]
# Filtro por búsqueda
if search_query:
    articles = [
        item for item in articles
        if search_query in item["title"].lower()
        or search_query in item["summary"].lower()
        or search_query in item["source"].lower()
        or search_query in item["category"].lower()
    ]
total_found = len(articles)
# ==========================================
# MÉTRICAS
# ==========================================
working_sources = sum(
    1 for status in statuses.values()
    if status.endswith("noticias")
)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        '<div class="metric"><div class="metric-label">'
        'Noticias encontradas</div><div class="metric-value">'
        f'{total_found}</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        '<div class="metric"><div class="metric-label">'
        'Fuentes con resultados</div><div class="metric-value">'
        f'{working_sources}/{len(selected_sources)}'
        '</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        '<div class="metric"><div class="metric-label">'
        'Última consulta</div><div class="metric-value">'
        f'{datetime.now().strftime("%H:%M")}'
        '</div></div>',
        unsafe_allow_html=True,
    )
st.write("")
st.subheader("📰 Noticias de ciberseguridad")
# Estado de cada fuente
with st.expander("Estado de las fuentes"):
    for name, status in statuses.items():
        st.write(f"**{name}:** {status}")
# ==========================================
# TARJETAS DE NOTICIAS
# ==========================================
if not articles:
    st.info(
        "No hay noticias para estos filtros. "
        "Prueba otra categoría o actualiza las fuentes."
    )
else:
    for article in articles[:max_articles]:
        st.markdown('<div class="news-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="news-meta">'
            f'{html.escape(article["source"])} · '
            f'{html.escape(article["category"])} · '
            f'{html.escape(display_date(article["published"]))}'
            f'</div>',
            unsafe_allow_html=True,
        )
        # Título tratado como texto para evitar inyección HTML
        st.subheader(article["title"])
        if article["summary"]:
            st.write(article["summary"])
        st.link_button(
            "Leer noticia original ↗",
            article["link"],
            key="article_" + str(abs(hash(article["link"]))),
        )
        st.markdown("</div>", unsafe_allow_html=True)
# ==========================================
# PIE DE PÁGINA
# ==========================================
st.divider()
st.caption(
    "CyberFeed · CondorHacks | "
    "Contenido procedente de fuentes RSS externas. "
    "Verifica los detalles técnicos en la fuente original."
)