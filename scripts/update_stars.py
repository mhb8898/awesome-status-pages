#!/usr/bin/env python3
"""Refresh GitHub star counts in data/opensource.yml and re-render the
Opensource section of README.md, sorted by stars (descending).

Usage:
    GITHUB_TOKEN=... python3 scripts/update_stars.py          # fetch + render
    python3 scripts/update_stars.py --no-fetch                # render only
"""
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "opensource.yml"
README = ROOT / "README.md"
START = "<!-- opensource:start -->"
END = "<!-- opensource:end -->"


def fetch_stars(repos):
    """Return {"owner/name": (stars, archived, canonical_name)} via one GraphQL call per 50 repos."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required to fetch stars (or pass --no-fetch)")
    result = {}
    repos = sorted(set(repos))
    for i in range(0, len(repos), 50):
        chunk = repos[i : i + 50]
        fields = []
        for j, full in enumerate(chunk):
            owner, name = full.split("/", 1)
            fields.append(
                f'r{j}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) '
                "{ nameWithOwner stargazerCount isArchived }"
            )
        query = "query {" + "\n".join(fields) + "}"
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": query}).encode(),
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.load(resp)
        data = payload.get("data") or {}
        for j, full in enumerate(chunk):
            node = data.get(f"r{j}")
            if node:
                result[full] = (node["stargazerCount"], node["isArchived"], node["nameWithOwner"])
            else:
                print(f"warning: could not resolve {full}, keeping last known count", file=sys.stderr)
    return result


def fmt_stars(n):
    if n is None:
        return "–"
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def render_line(e):
    stars = f"⭐ {fmt_stars(e.get('stars'))}"
    link = f"[{e['name']}]({e['url']})"
    if e.get("discontinued"):
        link = f"~~{link}~~"
    parts = [f"* `{stars}` {link}"]
    if e.get("repo") and "github.com" not in e["url"]:
        parts.append(f"([source](https://github.com/{e['repo']}))")
    line = " ".join(parts)
    if e.get("description"):
        line += f" - {e['description']}"
    if e.get("discontinued"):
        line += " *(Discontinued)*"
    elif e.get("archived"):
        line += " *(Archived)*"
    return line


def render(entries):
    by_stars = lambda e: (-(e.get("stars") or -1), e["name"].lower())
    active = sorted((e for e in entries if not e.get("discontinued")), key=by_stars)
    dead = sorted((e for e in entries if e.get("discontinued")), key=by_stars)
    lines = [f"*Sorted by GitHub stars — last updated {date.today().isoformat()}.*", ""]
    lines += [render_line(e) for e in active]
    if dead:
        lines += ["", "<details>", "<summary>Discontinued projects</summary>", ""]
        lines += [render_line(e) for e in dead]
        lines += ["", "</details>"]
    return "\n".join(lines)


def main():
    entries = yaml.safe_load(DATA.read_text())
    if "--no-fetch" not in sys.argv:
        stars = fetch_stars(e["repo"] for e in entries if e.get("repo"))
        for e in entries:
            if e.get("repo") in stars:
                count, archived, canonical = stars[e["repo"]]
                e["stars"] = count
                if e["url"].rstrip("/").lower() == f"https://github.com/{e['repo']}".lower():
                    e["url"] = f"https://github.com/{canonical}"
                e["repo"] = canonical
                if archived:
                    e["archived"] = True
                else:
                    e.pop("archived", None)
        DATA.write_text(yaml.safe_dump(entries, sort_keys=False, allow_unicode=True, width=1000))

    readme = README.read_text()
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    README.write_text(f"{head}{START}\n{render(entries)}\n{END}{tail}")


if __name__ == "__main__":
    main()
