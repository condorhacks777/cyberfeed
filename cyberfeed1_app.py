import re
import html
from datetime import datetime, timezone
from urllib.parse import urlparse
import feedparser
import requests
import streamlit as st
from deep_translator import GoogleTranslator
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
        "infostealer", "spyware", "virus",
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
    max-width: 1200px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
[data-testid="stSidebar"] {
    background: #0c1422;
    border-right: 1px solid #223147;
}
.hero {
    background: linear-gradient(120deg, #101d31, #0b302d);
    border: 1px solid #24453f;
    padding: 24px;
    border-radius: 18px;
    margin-bottom: 22px;
}
.hero h1 {
    color: #f1f7ff;
    font-size: 2.2rem;
    margin: 0;
}
.hero p {
    color: #a7bacd;
    margin-bottom: 0;
}
.metric {
    background: #101827;
    border: 1px solid #223147;
    padding: 15px;
    border-radius: 14px;
    min-height: 90px;
}
.metric-label {
    color: #9bacbf;
    font-size: .85rem;
}
.metric-value {
    color: #65e6bd;
    font-size: 1.6rem;
    font-weight: 700;
}
.news-meta {
    color: #91a5bc;
    font-size: .85rem;
}
div.stButton > button,
div.stLinkButton > a {
    border-radius: 9px;
}
a {
    color: #65e6bd !important;
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
            return datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    return None
def format_date(value):
    if not value:
        return "Fecha no disponible"
    return value.strftime("%d/%m/%Y %H:%M UTC")
# ==========================================
# TRADUCCIÓN AL ESPAÑOL
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def translate_to_spanish(text):
    if not text or not text.strip():
        return text
    try:
        translator = GoogleTranslator(
            source="auto",
            target="es",
        )
        translated = translator.translate(text[:4000])
        if translated and translated.strip():
            return translated.strip()
    except Exception:
        pass
    # Si falla la traducción, conserva el original.
    return text
# ==========================================
# CARGA RSS
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
                statuses[source_name] = "Sin noticias disponibles"
                continue
            before = len(articles)
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
                    "original_title": title,
                    "original_summary": summary[:1000],
                    "title": title,
                    "summary": summary[:1000],
                    "link": link,
                    "source": source_name,
                    "published": parse_date(entry),
                    "category": detect_category(title, summary),
                })
            count = len(articles) - before
            statuses[source_name] = f"{count} noticias"
        except requests.RequestException:
            statuses[source_name] = "Error de conexión"
        except Exception:
            statuses[source_name] = "Error al leer el feed"
    # Eliminar duplicados
    unique = {}
    for article in articles:
        unique[article["link"]] = article
    result = list(unique.values())
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
    st.caption("CONDORHACKS · CIBERSEGURIDAD")
    st.divider()
    selected_sources = st.multiselect(
        "Fuentes de noticias",
        options=list(SOURCES.keys()),
        default=list(SOURCES.keys()),
    )
    category_options = [
        "Todas",
        *CATEGORIES.keys(),
        "General",
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
        [5, 10, 20, 30],
        index=1,
    )
    st.divider()
    if st.button("🔄 Actualizar noticias", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Fuentes RSS internacionales")
    st.caption("Traducción automática al español")
# ==========================================
# CABECERA
# ==========================================
st.markdown("""
<div class="hero">
    <h1>CyberFeed <span style="color:#65e6bd">/</span> Dashboard</h1>
    <p>
        Noticias de ciberseguridad en español.
        Amenazas, vulnerabilidades e investigación en un solo lugar.
    </p>
</div>
""", unsafe_allow_html=True)
# ==========================================
# OBTENER NOTICIAS
# ==========================================
if not selected_sources:
    st.info("Selecciona al menos una fuente en el menú lateral.")
    st.stop()
with st.spinner("Consultando fuentes de ciberseguridad..."):
    articles, statuses = load_news(tuple(selected_sources))
# ==========================================
# FILTRAR ANTES DE TRADUCIR
# ==========================================
if selected_category != "Todas":
    articles = [
        a for a in articles
        if a["category"] == selected_category
    ]
if search_query:
    articles = [
        a for a in articles
        if search_query in a["original_title"].lower()
        or search_query in a["original_summary"].lower()
        or search_query in a["source"].lower()
        or search_query in a["category"].lower()
    ]
total_found = len(articles)
working_sources = sum(
    1 for status in statuses.values()
    if status.endswith("noticias")
)
# ==========================================
# MÉTRICAS
# ==========================================
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f'<div class="metric">'
        f'<div class="metric-label">Noticias encontradas</div>'
        f'<div class="metric-value">{total_found}</div></div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="metric">'
        f'<div class="metric-label">Fuentes con resultados</div>'
        f'<div class="metric-value">'
        f'{working_sources}/{len(selected_sources)}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="metric">'
        f'<div class="metric-label">Hora de consulta</div>'
        f'<div class="metric-value">'
        f'{datetime.now().strftime("%H:%M")}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
st.write("")
with st.expander("Estado de las fuentes RSS"):
    for name, status in statuses.items():
        st.write(f"**{name}:** {status}")
# ==========================================
# MOSTRAR NOTICIAS EN ESPAÑOL
# ==========================================
st.subheader("📰 Noticias de ciberseguridad")
if not articles:
    st.info(
        "No hay noticias con estos filtros. "
        "Prueba otra categoría o cambia la búsqueda."
    )
else:
    visible_articles = articles[:max_articles]
    with st.spinner("Traduciendo noticias al español..."):
        for article in visible_articles:
            article["title"] = translate_to_spanish(
                article["original_title"]
            )
            article["summary"] = translate_to_spanish(
                article["original_summary"]
            )
    for index, article in enumerate(visible_articles):
        # Sin contenedores con borde adicional para evitar
        # los rectángulos vacíos que aparecían en el móvil.
        st.caption(
            f"{article['source']} · "
            f"{article['category']} · "
            f"{format_date(article['published'])}"
        )
        st.markdown(f"### {article['title']}")
        if article["summary"]:
            st.write(article["summary"])
        st.link_button(
            "Leer noticia original ↗",
            article["link"],
            key=f"article_{index}",
        )
        if (
            article["title"] == article["original_title"]
            and article["summary"] == article["original_summary"]
        ):
            st.caption(
                "Aviso: la traducción no estuvo disponible; "
                "se muestra el contenido original."
            )
        if index < len(visible_articles) - 1:
            st.divider()
# ==========================================
# PIE DE PÁGINA
# ==========================================
st.divider()
st.caption(
    "CyberFeed · CondorHacks | Traducción automática. "
    "Consulta la fuente original para verificar los detalles técnicos."
)