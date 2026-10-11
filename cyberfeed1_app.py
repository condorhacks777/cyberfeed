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
    "The Hacker News":
        "https://feeds.feedburner.com/TheHackersNews",
    "Krebs on Security":
        "https://krebsonsecurity.com/feed/",
    "BleepingComputer":
        "https://www.bleepingcomputer.com/feed/",
    "Dark Reading":
        "https://www.darkreading.com/rss.xml",
}

CATEGORIES = {
    "Vulnerabilidades": [
        "cve", "vulnerability", "vulnerabilidad",
        "exploit", "zero-day", "zero day", "patch",
    ],
    "Malware": [
        "malware", "ransomware", "trojan",
        "botnet", "infostealer", "spyware",
    ],
    "Hacking": [
        "hacker", "hacking", "phishing",
        "cyberattack", "ciberataque", "breach",
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
    background-color: #080d18;
    color: #e6edf7;
}

.block-container {
    max-width: 1250px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background-color: #0c1422;
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
    padding: 20px;
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
    """Elimina etiquetas HTML y limpia el texto."""
    value = re.sub(r"<[^>]*>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def valid_url(url):
    """Solo acepta enlaces HTTP y HTTPS."""
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
    """Convierte la fecha RSS cuando está disponible."""
    try:
        parsed = (
            entry.get("published_parsed")
            or entry.get("updated_parsed")
        )

        if parsed:
            return datetime(
                *parsed[:6],
                tzinfo=timezone.utc,
            )
    except (TypeError, ValueError, OverflowError):
        pass

    return None


# ==========================================
# CARGA DE NOTICIAS CON TIEMPO LÍMITE
# ==========================================

@st.cache_data(ttl=600, show_spinner=False)
def load_news(source_names):
    articles = []
    source_status = {}

    for source_name in source_names:
        feed_url = SOURCES.get(source_name)

        if not feed_url:
            continue

        try:
            response = requests.get(
                feed_url,
                timeout=8,
                headers={
                    "User-Agent": "CyberFeed/1.0"
                },
            )

            response.raise_for_status()
            feed = feedparser.parse(response.content)

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
                    "summary": summary[:1200],
                    "source": source_name,
                    "published": parse_date(entry),
                    "category": detect_category(
                        title, summary
                    ),
                })

            count = len(articles) - count_before
            source_status[source_name] = f"{count} noticias"

        except requests.RequestException:
            source_status[source_name] = (
                "Fuente no disponible"
            )

        except Exception:
            source_status[source_name] = (
                "Error al procesar el feed"
            )

    # Eliminar duplicados
    unique = {}

    for article in articles:
        unique[article["link"]] = article

    result = list(unique.values())

    # Las noticias con fecha más reciente aparecen primero
    result.sort(
        key=lambda item: (
            item["published"]
            or datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )

    return result, source_status