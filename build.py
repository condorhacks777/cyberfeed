"""CyberFeed: genera dist/index.html (sitio estático) a partir de feeds RSS.

Sin API keys. Se ejecuta en GitHub Actions y se publica en Cloudflare Pages.
"""
import calendar
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from deep_translator import GoogleTranslator, MyMemoryTranslator

FEEDS = {
    "The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "Dark Reading": "https://www.darkreading.com/rss.xml",
    "PortSwigger": "https://portswigger.net/research/rss",
    "KitPloit": "https://www.kitploit.com/feeds/posts/default?alt=rss",
    "Packet Storm": "https://rss.packetstormsecurity.com/news/",
}

# Etiqueta -> regex sobre título + descripción
CATEGORIAS = {
    "⚠ BRECHAS": r"breach|ransomware|data leak|leaked|stolen data|extortion",
    "⚙ HERRAMIENTAS": r"github|\btool\b|framework|scanner|pentest|open[- ]source|repository",
    "☣ CVEs": r"CVE-\d|vulnerabilit|zero[- ]day|exploit|\bRCE\b",
    "◉ GRUPOS APT": r"\bAPT\d*\b|espionage|nation[- ]state|state[- ]sponsored|threat actor",
    "₿ CRYPTO": r"crypto|blockchain|\bdefi\b|bitcoin|ethereum|wallet",
}

PER_FEED = 15   # artículos máximos por fuente
TOTAL = 80      # artículos totales en la página


def clean(text, limit=300):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    text = re.sub(r"\[\s*(\.\.\.|…)\s*\]", "", text)
    text = re.sub(r"The post .{0,200}? appeared first on .*$", "", text).strip()
    return text[:limit]


def fetch_all():
    items, seen = [], set()
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url, agent="Mozilla/5.0 (CyberFeed build)")
        except Exception as e:
            print(f"[!] {source}: {e}")
            continue
        n = 0
        for e in feed.entries:
            link = e.get("link", "")
            if not link.startswith(("http://", "https://")) or link in seen:
                continue
            seen.add(link)
            ts = e.get("published_parsed") or e.get("updated_parsed")
            items.append({
                "title": clean(e.get("title"), 200),
                "desc": clean(e.get("summary") or e.get("description")),
                "url": link,
                "source": source,
                "ts": calendar.timegm(ts) if ts else 0,
            })
            n += 1
            if n >= PER_FEED:
                break
        print(f"[ok] {source}: {n} artículos")
    items.sort(key=lambda a: a["ts"], reverse=True)
    return items[:TOTAL]


def categorize(a):
    text = f'{a["title"]} {a["desc"]}'
    cats = [c for c, rx in CATEGORIAS.items() if re.search(rx, text, re.I)]
    if a["source"] == "KitPloit" and "⚙ HERRAMIENTAS" not in cats:
        cats.append("⚙ HERRAMIENTAS")
    return cats


def translate(items):
    engines = (
        ("google", GoogleTranslator(source="en", target="es")),
        ("mymemory", MyMemoryTranslator(source="en-US", target="es-ES")),
    )
    ok = fail = errors = 0
    streak = {name: 0 for name, _ in engines}  # fallos seguidos por traductor
    for a in items:
        for k in ("title", "desc"):
            if not a[k]:
                continue
            done = False
            for name, engine in engines:
                if streak[name] >= 3:  # traductor caído: no insistir
                    continue
                try:
                    out = engine.translate(a[k])
                    if out and out.strip():
                        a[k] = out
                        streak[name] = 0
                        done = True
                        break
                except Exception as e:
                    streak[name] += 1
                    errors += 1
                    if errors <= 5:  # no llenar el registro
                        print(f"[!] {name} falló: {type(e).__name__}: {str(e)[:120]}")
                    if streak[name] >= 3:
                        print(f"[!] {name} desactivado tras 3 fallos seguidos")
            if done:
                ok += 1
            else:
                fail += 1  # se queda en inglés
    print(f"Traducción: {ok} correctos, {fail} sin traducir")
    return items


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CyberFeed · Noticias de ciberseguridad en español</title>
<meta name="description" content="Monitor de noticias de ciberseguridad en español: brechas, herramientas, CVEs, grupos APT y crypto. Actualizado cada hora.">
<link rel="canonical" href="https://cyberfeed.app/">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🛡️</text></svg>">
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap');
html,body{background:#000a03;color:#00ff88;font-family:'Share Tech Mono',monospace;margin:0}
body::after{content:"";position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,255,136,.015) 2px,rgba(0,255,136,.015) 4px);pointer-events:none;z-index:9999}
main{max-width:700px;margin:0 auto;padding:1rem}
h1{font-family:'Orbitron',monospace;letter-spacing:.15em;text-align:center}
h1 span{color:#ff2d2d}
.sub{text-align:center;font-size:.65rem;color:rgba(0,255,136,.4);letter-spacing:.15em}
hr{border:0;border-top:1px solid rgba(0,255,136,.15)}
select{width:100%;background:#000a03;border:1px solid rgba(0,255,136,.3);color:#00ff88;padding:.6rem;border-radius:0;font-family:inherit;font-size:.9rem;margin-bottom:1rem}
.card{border:1px solid rgba(0,255,136,.2);border-left:3px solid #00ff88;background:rgba(0,10,5,.85);padding:.9rem 1rem;margin-bottom:.5rem}
.meta{display:flex;gap:.5rem;font-size:.6rem;margin-bottom:.4rem}
.cat{color:#00cfff}.src{color:rgba(0,255,136,.4)}
.t{font-size:.88rem;color:#e8ffe8;line-height:1.4;margin-bottom:.5rem;font-weight:bold}
.d{font-size:.76rem;color:rgba(200,255,200,.75);line-height:1.7;margin-bottom:.5rem}
a{color:#00ff88;font-size:.72rem;text-decoration:none}
.empty{text-align:center;opacity:.3;margin-top:2rem}
.foot{text-align:center;font-size:.55rem;color:rgba(0,255,136,.25);margin-top:2rem}
</style>
</head>
<body>
<main>
<h1>◈ CYBER<span>FEED</span></h1>
<p class="sub">MONITOR DE INTELIGENCIA · actualizado __DATE__</p>
<hr>
<select id="cat"></select>
<div id="list">__CARDS__</div>
<p class="empty" id="empty" hidden>Sin señales en este sector...</p>
<p class="foot">SISTEMA ACTIVO</p>
</main>
<script>
const CATS = ["◈ TODAS", ...__CATS__];
const LIMIT = 15;
const sel = document.getElementById("cat"), list = document.getElementById("list"), empty = document.getElementById("empty");
CATS.forEach(c => { const o = document.createElement("option"); o.textContent = c; sel.appendChild(o); });
const cards = Array.from(list.querySelectorAll(".card"));
function render() {
  const c = sel.value, all = c === CATS[0];
  let shown = 0;
  cards.forEach(card => {
    const cats = card.dataset.cats ? card.dataset.cats.split("|") : [];
    const show = (all || cats.includes(c)) && shown < LIMIT;
    card.hidden = !show;
    if (show) { shown++; card.querySelector(".cat").textContent = all ? (cats[0] || "◈") : c; }
  });
  empty.hidden = shown > 0;
}
sel.addEventListener("change", render);
render();
</script>
</body>
</html>
"""


def render_cards(items):
    """Tarjetas en HTML estático (visibles para Google y sin JavaScript)."""
    esc = lambda s: html.escape(s or "", quote=True)
    out = []
    for a in items:
        cats = a["cats"]
        out.append(
            f'<article class="card" data-cats="{esc("|".join(cats))}">'
            f'<div class="meta"><span class="cat">{esc(cats[0] if cats else "◈")}</span>'
            f'<span class="src">🔗 {esc(a["source"])}</span></div>'
            f'<div class="t">{esc(a["title"])}</div>'
            f'<div class="d">{esc(a["desc"])}</div>'
            f'<a href="{esc(a["url"])}" target="_blank" rel="noopener noreferrer">▶ Leer artículo completo</a>'
            f"</article>"
        )
    return "\n".join(out)


def main():
    items = fetch_all()
    for a in items:
        a["cats"] = categorize(a)
    items = translate(items)
    page = (
        TEMPLATE
        .replace("__CATS__", json.dumps(list(CATEGORIAS.keys()), ensure_ascii=False))
        .replace("__DATE__", datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"))
        .replace("__CARDS__", render_cards(items))  # el último, por seguridad
    )
    out = Path("dist")
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"dist/index.html generado con {len(items)} artículos")


if __name__ == "__main__":
    main()
