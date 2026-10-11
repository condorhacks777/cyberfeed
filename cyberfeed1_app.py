
import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import feedparser
import requests
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="CyberFeed | Cybersecurity Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# RSS SOURCES
# --------------------------------------------------

RSS_SOURCES = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "Krebs on Security": "https://krebsonsecurity.com/feed/",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
}

CATEGORIES = [
    "All",
    "Vulnerabilities",
    "Malware",
    "Hacking",
    "Artificial Intelligence",
    "Data Breaches",
    "General",
]


# --------------------------------------------------
# STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0b1220;
        color: #e5edf7;
    }

    [data-testid="stSidebar"] {
        background-color: #101a2b;
        border-right: 1px solid #243449;
    }

    h1, h2, h3 {
        color: #eaf2ff;
    }

    .hero {
        padding: 22px 24px;
        border-radius: 16px;
        background: linear-gradient(120deg, #10263c, #123b46);
        border: 1px solid #245365;
        margin-bottom: 20px;
    }

    .hero-title {
        font-size: 32px;
        font-weight: 800;
        color: #f0f9ff;
        margin-bottom: 5px;
    }

    .hero-subtitle {
        font-size: 14px;
        color: #b5cadb;
    }

    .news-card {
        background-color: #111c2e;
        border: 1px solid #26374e;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
    }

    .news-title {
        font-size: 19px;
        line-height: 1.4;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .news-title a {
        color: #70d6d1 !important;
        text-decoration: none;
    }

    .news-title a:hover {
        color: #a5f3fc !important;
        text-decoration: underline;
    }

    .news-meta {
        color: #9aadc4;
        font-size: 12px;
        margin-bottom: 12px;
    }

    .news-summary {
        color: #d2dceb;
        font-size: 14px;
        line-height: 1.65;
    }

    .category-tag {
        display: inline-block;
        background: #173b4a;
        color: #8ce8e0;
        padding: 4px 9px;
        border-radius: 20px;
        font-size: 11px;
        margin-bottom: 10px;
    }

    .source-tag {
        display: inline-block;
        background: #202e42;
        color: #bdcde0;
        padding: 4px 9px;
        border-radius: 20px;
        font-size: 11px;
        margin-right: 5px;
    }

    .status-text {
        color: #9aadc4;
        font-size: 12px;
    }

    div[data-testid="stMetric"] {
        background: #111c2e;
        border: 1px solid #26374e;
        padding: 14px;
        border-radius: 12px;
    }

    div[data-testid="stMetricValue"] {
        color: #70d6d1;
    }

    .footer {
        color: #8194ab;
        font-size: 12px;
        text-align: center;
        padding: 22px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def clean_text(value):
    """Convert feed HTML into readable plain text."""
    if not value:
        return ""

    value = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>",
        " ",
        str(value),
    )
    value = re.sub(r"(?i)<br\s*/?>", " ", value)
    value = re.sub(r"(?i)</p\s*>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def get_entry_date(entry):
    """Return a readable publication date when available."""
    parsed = entry.get("published_parsed") or entry.get(
        "updated_parsed"
    )

    if parsed:
        try:
            return datetime(
                parsed.tm_year,
                parsed.tm_mon,
                parsed.tm_mday,
                parsed.tm_hour,
                parsed.tm_min,
                parsed.tm_sec,
                tzinfo=timezone.utc,
            ).strftime("%b %d, %Y · %H:%M UTC")
        except (ValueError, TypeError, OverflowError):
            pass

    return "Date unavailable"


def categorize_article(title, summary):
    """Assign a category using simple keyword matching."""
    text = f"{title} {summary}".lower()

    rules = [
        (
            "Artificial Intelligence",
            [
                "artificial intelligence",
                "generative ai",
                "machine learning",
                "large language model",
                "chatgpt",
                "openai",
                "deepfake",
                "ai model",
            ],
        ),
        (
            "Data Breaches",
            [
                "data breach",
                "data leak",
                "exposed database",
                "stolen data",
                "customer records",
                "personal information",
                "ransomware leak",
            ],
        ),
        (
            "Vulnerabilities",
            [
                "vulnerability",
                "vulnerabilities",
                "zero-day",
                "zero day",
                "cve-",
                "security flaw",
                "patch",
                "remote code execution",
                "privilege escalation",
                "exploit",
            ],
        ),
        (
            "Malware",
            [
                "malware",
                "ransomware",
                "trojan",
                "spyware",
                "botnet",
                "infostealer",
                "backdoor",
                "rootkit",
                "worm",
                "keylogger",
            ],
        ),
        (
            "Hacking",
            [
                "hacker",
                "hackers",
                "hacking",
                "cyberattack",
                "cyber attack",
                "phishing",
                "credential theft",
                "cyber espionage",
                "threat actor",
                "attack campaign",
            ],
        ),
    ]

    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category

    return "General"


def get_summary(entry):
    """Get a summary from the available feed fields."""
    summary = entry.get("summary", "")

    if not summary and entry.get("description"):
        summary = entry.get("description", "")

    if not summary and entry.get("content"):
        try:
            summary = entry["content"][0].get("value", "")
        except (IndexError, KeyError, TypeError):
            summary = ""

    summary = clean_text(summary)

    if len(summary) > 650:
        summary = summary[:647].rsplit(" ", 1)[0] + "..."

    return summary or "No summary is available for this article."


# --------------------------------------------------
# RSS FETCHING
# --------------------------------------------------

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news():
    """Fetch articles from all configured RSS sources."""
    articles = []
    source_status = {}
    seen_urls = set()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; CyberFeed/1.0; "
            "+https://github.com/condorhacks777/cyberfeed)"
        ),
        "Accept": (
            "application/rss+xml, application/xml, "
            "text/xml, application/atom+xml, */*"
        ),
    }

    for source_name, feed_url in RSS_SOURCES.items():
        try:
            response = requests.get(
                feed_url,
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                source_status[source_name] = "No articles returned"
                continue

            added_count = 0

            for entry in feed.entries:
                title = clean_text(entry.get("title", ""))
                link = entry.get("link", "").strip()

                if not title or not link:
                    continue

                parsed_url = urlparse(link)

                if parsed_url.scheme not in ("http", "https"):
                    continue

                normalized_url = link.split("#", 1)[0]

                if normalized_url in seen_urls:
                    continue

                seen_urls.add(normalized_url)

                summary = get_summary(entry)

                articles.append(
                    {
                        "title": title,
                        "link": link,
                        "summary": summary,
                        "source": source_name,
                        "category": categorize_article(
                            title, summary
                        ),
                        "date": get_entry_date(entry),
                        "published_timestamp": (
                            entry.get("published_parsed")
                            or entry.get("updated_parsed")
                        ),
                    }
                )

                added_count += 1

            source_status[source_name] = (
                f"{added_count} articles loaded"
            )

        except requests.RequestException as exc:
            source_status[source_name] = (
                f"Connection error: {type(exc).__name__}"
            )

        except Exception as exc:
            source_status[source_name] = (
                f"Feed error: {type(exc).__name__}"
            )

    # Sort newest first when RSS publication dates are available.
    articles.sort(
        key=lambda article: (
            article["published_timestamp"] is not None,
            article["published_timestamp"] or (),
        ),
        reverse=True,
    )

    return articles, source_status


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🛡️ CyberFeed</div>
        <div class="hero-subtitle">
            Cybersecurity news, threat intelligence,
            vulnerabilities and emerging attacks — all in one place.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Dashboard Settings")
    st.markdown("---")

    selected_category = st.selectbox(
        "Category",
        CATEGORIES,
        index=0,
    )

    selected_sources = st.multiselect(
        "News Sources",
        options=list(RSS_SOURCES.keys()),
        default=list(RSS_SOURCES.keys()),
    )

    search_query = st.text_input(
        "Search articles",
        placeholder="Search keywords...",
    )

    st.markdown("---")

    if st.button(
        "🔄 Refresh News",
        use_container_width=True,
    ):
        fetch_news.clear()
        st.rerun()

    st.caption("Feed cache: 10 minutes")
    st.caption("Translation: disabled")
    st.caption("Articles remain in their original language.")


# --------------------------------------------------
# LOAD ARTICLES
# --------------------------------------------------

with st.spinner("Loading cybersecurity news..."):
    articles, source_status = fetch_news()


# --------------------------------------------------
# FILTER ARTICLES
# --------------------------------------------------

filtered_articles = []

for article in articles:
    if (
        selected_category != "All"
        and article["category"] != selected_category
    ):
        continue

    if article["source"] not in selected_sources:
        continue

    if search_query:
        searchable_text = (
            article["title"] + " " + article["summary"]
        ).lower()

        if search_query.lower() not in searchable_text:
            continue

    filtered_articles.append(article)


# --------------------------------------------------
# DASHBOARD METRICS
# --------------------------------------------------

metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    st.metric("Articles Loaded", len(articles))

with metric_col2:
    st.metric("Matching Articles", len(filtered_articles))

with metric_col3:
    st.metric("Active Sources", len(selected_sources))


# --------------------------------------------------
# SOURCE STATUS
# --------------------------------------------------

with st.expander("📡 RSS Source Status"):
    for source_name, status in source_status.items():
        st.markdown(f"**{source_name}:** {status}")


# --------------------------------------------------
# NEWS FEED
# --------------------------------------------------

st.markdown("## 📰 Latest Cybersecurity News")

if not selected_sources:
    st.info("Select at least one news source in the sidebar.")

elif not filtered_articles:
    st.warning(
        "No articles match your filters. "
        "Try another category or search term."
    )

else:
    st.caption(
        f"Showing {len(filtered_articles)} article(s). "
        "Open any headline to read the original article."
    )

    for article in filtered_articles:
        safe_title = html.escape(article["title"])
        safe_link = html.escape(article["link"], quote=True)
        safe_summary = html.escape(article["summary"])
        safe_source = html.escape(article["source"])
        safe_category = html.escape(article["category"])
        safe_date = html.escape(article["date"])

        st.markdown(
            f"""
            <div class="news-card">
                <span class="category-tag">
                    {safe_category}
                </span>
                <span class="source-tag">
                    {safe_source}
                </span>
                <div class="news-title">
                    <a href="{safe_link}"
                       target="_blank"
                       rel="noopener noreferrer">
                        {safe_title}
                    </a>
                </div>
                <div class="news-meta">
                    Published: {safe_date}
                </div>
                <div class="news-summary">
                    {safe_summary}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown(
    """
    <div class="footer">
        CyberFeed · Open-source cybersecurity news dashboard<br>
        News content belongs to its respective publishers.
        Follow the original links for full articles.
    </div>
    """,
    unsafe_allow_html=True,
)
