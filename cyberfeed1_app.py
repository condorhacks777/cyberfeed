import streamlit as st
import feedparser
from datetime import datetime
from urllib.parse import urlparse
st.set_page_config(
    page_title="CyberFeed | CondorHacks",
    page_icon="🛡️",
    layout="wide",
)
SOURCES = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
}
st.markdown("""
<style>
.block-container {max-width: 1150px; padding-top: 2rem;}
.news-card {
    padding: 1.1rem;
    border: 1px solid rgba(128,128,128,.3);
    border-radius: 12px;
    margin-bottom: 1rem;
}
.source {font-size: .85rem; opacity: .75;}
</style>
""", unsafe_allow_html=True)
st.title("🛡️ CyberFeed")
st.caption("Inteligencia y noticias de ciberseguridad · CondorHacks")
with st.sidebar:
    st.header("Configuración")
    selected_sources = st.multiselect(
        "Fuentes",
        list(SOURCES.keys()),
        default=list(SOURCES.keys()),
    )
    search = st.text_input("Buscar noticias").strip().lower()
    limit = st.slider("Número de noticias", 5, 50, 20)
@st.cache_data(ttl=600, show_spinner=False)
def load_news(source_names):
    articles = []
    for name in source_names:
        try:
            feed = feedparser.parse(SOURCES[name])
            for entry in feed.entries:
                link = entry.get("link", "")
                parsed = urlparse(link)
                if parsed.scheme not in ("http", "https"):
                    continue
                articles.append({
                    "title": entry.get("title", "Sin título"),
                    "link": link,
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", ""),
                    "source": name,
                })
        except Exception:
            continue
    # Eliminar enlaces duplicados
    unique = {}
    for article in articles:
        unique[article["link"]] = article
    return list(unique.values())
if st.button("🔄 Actualizar noticias"):
    st.cache_data.clear()
with st.spinner("Cargando noticias..."):
    articles = load_news(tuple(selected_sources))
if search:
    articles = [
        a for a in articles
        if search in a["title"].lower()
        or search in a["summary"].lower()
        or search in a["source"].lower()
    ]
articles = articles[:limit]
st.caption(f"{len(articles)} noticias encontradas")
if not articles:
    st.info("No hay noticias disponibles. Prueba otra búsqueda o vuelve a intentarlo.")
else:
    for article in articles:
        st.markdown('<div class="news-card">', unsafe_allow_html=True)
        st.subheader(article["title"])
        st.markdown(
            f'<div class="source">{article["source"]} · '
            f'{article["published"] or "Fecha no disponible"}</div>',
            unsafe_allow_html=True,
        )
        summary = article["summary"]
        if summary:
            # Streamlit escapa el HTML al mostrar texto
            st.write(summary[:500].replace("<", " ").replace(">", " "))
        st.link_button("Leer noticia original", article["link"])
        st.markdown("</div>", unsafe_allow_html=True)
st.divider()
st.caption("CyberFeed · Proyecto de CondorHacks")