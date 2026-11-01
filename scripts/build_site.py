#!/usr/bin/env python3
"""Build the GitHub Pages site into ./site from data/opensource.yml and README.md.

Usage:
    python3 scripts/build_site.py
"""
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
SITE_URL = "https://mhb8898.github.io/awesome-status-pages/"
REPO_URL = "https://github.com/mhb8898/awesome-status-pages"
UPSTREAM_URL = "https://github.com/ivbeg/awesome-status-pages"

TITLE = "Awesome Status Pages: Open Source & Self-Hosted Status Page Software Ranked by GitHub Stars"
DESCRIPTION = (
    "Curated list of the best open source and self-hosted status page tools, ranked by GitHub stars "
    "and updated weekly, plus hosted status page services (Statuspage.io alternatives) and public "
    "status pages of major companies and cloud providers."
)

# README section heading -> (anchor id, intro shown on the site)
SECTIONS = [
    ("Hosted Status Page Services", "services"),
    ("Public Status Pages of Major Companies", "public"),
    ("Cloud & Hosting Provider Status Pages", "cloud"),
]


def inline_md(text):
    """Convert the small subset of inline Markdown used in this list to HTML."""
    t = html.escape(text, quote=False)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(m[2])}" rel="noopener">{m[1]}</a>', t)
    t = re.sub(r"~~(.+?)~~", r"<s>\1</s>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"(?<![\"=/])(https?://[^\s<)]+)", r'<a href="\1" rel="noopener">\1</a>', t)
    return t


def readme_section(readme, heading):
    body = readme.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
    lines = body.strip().splitlines()
    intro = lines[0] if lines and not lines[0].startswith("*") else ""
    items = [l[2:].strip() for l in lines if l.startswith("* ")]
    return intro, items


def fmt_stars(n):
    if n is None:
        return "–"
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def opensource_rows(entries):
    rows = []
    for rank, e in enumerate(entries, 1):
        name = f'<a href="{html.escape(e["url"])}" rel="noopener">{html.escape(e["name"])}</a>'
        if e.get("repo") and "github.com" not in e["url"]:
            name += f' <a class="src" href="https://github.com/{html.escape(e["repo"])}" rel="noopener">source</a>'
        tags = ""
        if e.get("archived"):
            tags = ' <span class="tag">archived</span>'
        rows.append(
            f'<tr data-stars="{e.get("stars") or -1}" data-name="{html.escape(e["name"].lower())}">'
            f'<td class="rank">{rank}</td><td class="name">{name}{tags}</td>'
            f'<td class="stars">{fmt_stars(e.get("stars"))}</td>'
            f'<td class="desc">{inline_md(e.get("description") or "")}</td></tr>'
        )
    return "\n".join(rows)


def build():
    readme = (ROOT / "README.md").read_text()
    entries = yaml.safe_load((ROOT / "data" / "opensource.yml").read_text())
    by_stars = lambda e: (-(e.get("stars") or -1), e["name"].lower())
    active = sorted((e for e in entries if not e.get("discontinued")), key=by_stars)
    dead = sorted((e for e in entries if e.get("discontinued")), key=by_stars)
    today = date.today().isoformat()

    sections_html = []
    counts = {"opensource": len(active)}
    for heading, anchor in SECTIONS:
        intro, items = readme_section(readme, heading)
        counts[anchor] = len(items)
        lis = "\n".join(f"<li>{inline_md(i)}</li>" for i in items)
        sections_html.append(
            f'<section id="{anchor}"><h2>{html.escape(heading)} <span class="count">{len(items)}</span></h2>'
            f'<p class="intro">{inline_md(intro)}</p><ul class="list">{lis}</ul></section>'
        )

    json_ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Open source & self-hosted status page software ranked by GitHub stars",
        "url": SITE_URL,
        "dateModified": today,
        "numberOfItems": len(active),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "item": {
                    "@type": "SoftwareApplication",
                    "name": e["name"],
                    "url": e["url"],
                    "applicationCategory": "DeveloperApplication",
                    **({"description": e["description"]} if e.get("description") else {}),
                },
            }
            for i, e in enumerate(active, 1)
        ],
    }

    nav = "".join(
        f'<a href="#{a}">{label} <span>{counts[a]}</span></a>'
        for label, a in [("Open source", "opensource"), ("Hosted services", "services"),
                         ("Public status pages", "public"), ("Cloud providers", "cloud")]
    )

    page = TEMPLATE.format(
        title=html.escape(TITLE),
        description=html.escape(DESCRIPTION),
        site_url=SITE_URL,
        repo_url=REPO_URL,
        upstream_url=UPSTREAM_URL,
        today=today,
        nav=nav,
        os_count=len(active),
        os_rows=opensource_rows(active),
        dead_rows=opensource_rows(dead),
        dead_count=len(dead),
        sections="\n".join(sections_html),
        json_ld=json.dumps(json_ld, ensure_ascii=False).replace("</", "<\\/"),
    )

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "index.html").write_text(page)
    shutil.copy(ROOT / "assets" / "social-preview.png", OUT / "social-preview.png")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}sitemap.xml\n")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{SITE_URL}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>\n"
        "</urlset>\n"
    )
    (OUT / ".nojekyll").write_text("")
    print(f"built {OUT} ({len(active)} open source, {sum(counts.values()) - len(active)} other entries)")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{site_url}">
<meta name="robots" content="index, follow">
<meta property="og:type" content="website">
<meta property="og:title" content="Awesome Status Pages: open source status page tools ranked by stars">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{site_url}">
<meta property="og:image" content="{site_url}social-preview.png">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="640">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Awesome Status Pages: open source status page tools ranked by stars">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="{site_url}social-preview.png">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><circle cx='8' cy='8' r='7' fill='%233fb950'/></svg>">
<script type="application/ld+json">{json_ld}</script>
<style>
:root {{ --bg:#ffffff; --fg:#1f2328; --muted:#59636e; --border:#d1d9e0; --panel:#f6f8fa; --accent:#0969da; --green:#1a7f37; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0d1117; --fg:#e6edf3; --muted:#9198a1; --border:#30363d; --panel:#151b23; --accent:#4493f8; --green:#3fb950; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
a {{ color:var(--accent); text-decoration:none; }} a:hover {{ text-decoration:underline; }}
.wrap {{ max-width:1100px; margin:0 auto; padding:0 16px; }}
header {{ padding:48px 0 24px; border-bottom:1px solid var(--border); }}
h1 {{ font-size:clamp(28px,5vw,44px); line-height:1.15; margin:0 0 12px; }}
h1 .dot {{ display:inline-block; width:.5em; height:.5em; border-radius:50%; background:var(--green); vertical-align:middle; margin-right:.3em; }}
.lead {{ font-size:18px; color:var(--muted); max-width:760px; margin:0 0 20px; }}
.actions {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; }}
.btn {{ display:inline-block; padding:8px 16px; border-radius:6px; border:1px solid var(--border); background:var(--panel); color:var(--fg); font-weight:600; }}
.btn.primary {{ background:var(--green); border-color:var(--green); color:#fff; }}
.credit {{ font-size:14px; color:var(--muted); margin-top:16px; }}
nav.toc {{ position:sticky; top:0; z-index:2; background:var(--bg); border-bottom:1px solid var(--border); }}
nav.toc .wrap {{ display:flex; gap:6px; overflow-x:auto; padding-top:10px; padding-bottom:10px; align-items:center; }}
nav.toc a {{ white-space:nowrap; padding:4px 10px; border-radius:999px; color:var(--fg); font-size:14px; }}
nav.toc a span {{ color:var(--muted); }}
nav.toc input {{ margin-left:auto; min-width:180px; padding:6px 10px; border-radius:6px; border:1px solid var(--border); background:var(--panel); color:var(--fg); font:inherit; font-size:14px; }}
section {{ padding:32px 0 8px; scroll-margin-top:60px; }}
h2 {{ font-size:24px; margin:0 0 6px; }}
h2 .count {{ font-size:14px; color:var(--muted); font-weight:500; border:1px solid var(--border); border-radius:999px; padding:1px 8px; vertical-align:middle; }}
.intro {{ color:var(--muted); margin:0 0 16px; }}
.table-wrap {{ overflow-x:auto; border:1px solid var(--border); border-radius:8px; }}
table {{ width:100%; border-collapse:collapse; font-size:15px; }}
th, td {{ text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); vertical-align:top; }}
tr:last-child td {{ border-bottom:0; }}
th {{ background:var(--panel); font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); }}
th button {{ all:unset; cursor:pointer; }} th button:hover {{ color:var(--fg); }}
td.rank {{ color:var(--muted); width:3em; }}
td.name {{ font-weight:600; white-space:nowrap; }}
td.stars {{ white-space:nowrap; font-variant-numeric:tabular-nums; }}
td.stars::before {{ content:"★ "; color:#d4a72c; }}
td.desc {{ color:var(--muted); min-width:280px; }}
.src, .tag {{ font-size:12px; font-weight:500; border:1px solid var(--border); border-radius:999px; padding:0 6px; margin-left:4px; }}
.tag {{ color:var(--muted); }}
details {{ margin-top:16px; }} summary {{ cursor:pointer; color:var(--muted); }}
ul.list {{ list-style:none; padding:0; margin:0; display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:10px; }}
ul.list li {{ border:1px solid var(--border); border-radius:8px; padding:10px 12px; background:var(--panel); color:var(--muted); font-size:14px; }}
ul.list li a:first-child {{ font-weight:600; font-size:15px; }}
.hidden {{ display:none !important; }}
footer {{ border-top:1px solid var(--border); margin-top:40px; padding:24px 0 48px; color:var(--muted); font-size:14px; }}
</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1><span class="dot"></span>Awesome Status Pages</h1>
    <p class="lead">The best <strong>open source &amp; self-hosted status page</strong> software ranked by GitHub stars and updated weekly, plus hosted status page services (Statuspage.io alternatives) and public status pages of major companies.</p>
    <div class="actions">
      <a class="btn primary" href="{repo_url}">★ Star on GitHub</a>
      <a class="btn" href="{repo_url}#contributing">Add a project</a>
      <span class="credit">Last updated {today}</span>
    </div>
    <p class="credit">Based on <a href="{upstream_url}">ivbeg/awesome-status-pages</a> by Ivan Begtin, with star rankings and weekly updates.</p>
  </div>
</header>
<nav class="toc" aria-label="Sections">
  <div class="wrap">{nav}<input id="q" type="search" placeholder="Filter…" aria-label="Filter the list"></div>
</nav>
<main class="wrap">
<section id="opensource">
  <h2>Open Source &amp; Self-Hosted Status Page Software <span class="count">{os_count}</span></h2>
  <p class="intro">Free, open source status page and uptime monitoring tools you can self-host, ranked by GitHub stars.</p>
  <div class="table-wrap">
  <table id="os">
    <thead><tr><th>#</th><th><button data-sort="name">Project</button></th><th><button data-sort="stars">Stars ↓</button></th><th>Description</th></tr></thead>
    <tbody>
{os_rows}
    </tbody>
  </table>
  </div>
  <details>
    <summary>Discontinued projects ({dead_count})</summary>
    <div class="table-wrap" style="margin-top:12px"><table><tbody>
{dead_rows}
    </tbody></table></div>
  </details>
</section>
{sections}
</main>
<footer>
  <div class="wrap">
    Open source projects ranked by GitHub stars, refreshed every week by GitHub Actions. ·
    <a href="{repo_url}">Source on GitHub</a> ·
    Based on <a href="{upstream_url}">ivbeg/awesome-status-pages</a> (MIT).
  </div>
</footer>
<script>
(function () {{
  var q = document.getElementById('q');
  q.addEventListener('input', function () {{
    var term = q.value.trim().toLowerCase();
    document.querySelectorAll('#os tbody tr, ul.list li').forEach(function (el) {{
      el.classList.toggle('hidden', term && el.textContent.toLowerCase().indexOf(term) === -1);
    }});
  }});
  var tbody = document.querySelector('#os tbody');
  document.querySelectorAll('#os th button').forEach(function (b) {{
    b.addEventListener('click', function () {{
      var key = b.dataset.sort;
      var rows = Array.prototype.slice.call(tbody.rows);
      rows.sort(key === 'stars'
        ? function (a, c) {{ return c.dataset.stars - a.dataset.stars; }}
        : function (a, c) {{ return a.dataset.name.localeCompare(c.dataset.name); }});
      rows.forEach(function (r) {{ tbody.appendChild(r); }});
    }});
  }});
}})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
