#!/usr/bin/env python3
"""Auto-update homepage README.md and index.html with latest repo data."""

import json
import urllib.request
import os
import re
import html

GITHUB_USER = "dechang64"
SCRIPT_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.join(SCRIPT_DIR, "..")
CONFIG_PATH = os.path.join(REPO_DIR, "repos-config.json")
README_PATH = os.path.join(REPO_DIR, "README.md")
HTML_PATH = os.path.join(REPO_DIR, "index.html")

REPO_START = "<!-- AUTO-GENERATED-START -->"
REPO_END = "<!-- AUTO-GENERATED-END -->"
HTML_START = "<!-- PROJECTS-AUTO-START -->"
HTML_END = "<!-- PROJECTS-AUTO-END -->"
STATS_START = "<!-- STATS-AUTO-START -->"
STATS_END = "<!-- STATS-AUTO-END -->"

STATS_PRIMARY_URL = (
    "https://github-readme-stats.vercel.app/api"
    f"?username={GITHUB_USER}&show_icons=true&theme=tokyonight&hide_border=true&count_private=true"
)
STATS_LANGS_URL = (
    "https://github-readme-stats.vercel.app/api/top-langs/"
    f"?username={GITHUB_USER}&layout=compact&theme=tokyonight&hide_border=true&langs_count=8"
)
STATS_STREAK_URL = (
    f"https://streak-stats.demolab.com?user={GITHUB_USER}&theme=tokyonight&hide_border=true"
)
STATS_SKILLS_ICONS = (
    "https://skillicons.dev/icons?i=rust,python,pytorch,docker,git,linux,"
    "grpc,react,streamlit,sqlite&theme=dark"
)


def fetch_repos():
    url = f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&type=owner&sort=updated"
    req = urllib.request.Request(url, headers={"User-Agent": "update-homepage-bot"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"token {token}")
    with urllib.request.urlopen(req) as resp:
        return [r for r in json.loads(resp.read()) if not r["fork"]]


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def star_badge(count):
    return f" ⭐{count}" if count > 0 else ""


def check_url(url, timeout=5):
    """Return True if URL returns HTTP 200."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "stats-check"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception:
        return False


def generate_stats():
    """Detect which stats service is available and generate markdown."""
    if check_url(STATS_PRIMARY_URL):
        return (
            f'<img src="{STATS_PRIMARY_URL}" width="48%"/>\n'
            f'<img src="{STATS_LANGS_URL}" width="48%"/>'
        )
    return (
        f'<img src="{STATS_STREAK_URL}" width="48%"/>\n'
        f'<img src="{STATS_SKILLS_ICONS}" width="48%"/>'
    )


def generate_section(title, repo_names, repo_map, config):
    """Generate a markdown table for one category."""
    desc_overrides = config.get("descriptions", {})
    rows = []
    for name in repo_names:
        if name not in repo_map:
            continue
        r = repo_map[name]
        desc = desc_overrides.get(name) or r.get("description") or ""
        lang = r.get("language") or ""
        badge = star_badge(r.get("stargazers_count", 0))
        link = f"[**{name}**](https://github.com/{GITHUB_USER}/{name})"
        cols = [link, desc]
        if lang:
            cols.append(f"`{lang}`")
        if badge:
            cols.append(badge)
        rows.append("| " + " | ".join(cols) + " |")

    if not rows:
        return ""

    header = "| 项目 | 简介 |"
    sep = "|------|------|"
    has_lang = any(repo_map.get(n, {}).get("language") for n in repo_names if n in repo_map)
    has_stars = any(repo_map.get(n, {}).get("stargazers_count", 0) > 0 for n in repo_names if n in repo_map)
    if has_lang:
        header += " 语言 |"
        sep += "------|"
    if has_stars:
        header += " ⭐ |"
        sep += "----|"

    return f"### {title}\n\n{header}\n{sep}\n" + "\n".join(rows)


def generate_uncategorized(repos, config):
    """Generate table for repos not in any category."""
    categorized = set()
    for names in config["categories"].values():
        categorized.update(names)
    categorized.update(config.get("exclude", []))
    uncat = [r for r in repos if r["name"] not in categorized]
    if not uncat:
        return ""

    desc_overrides = config.get("descriptions", {})
    rows = []
    for r in uncat:
        desc = desc_overrides.get(r["name"]) or r.get("description") or ""
        lang = r.get("language") or ""
        badge = star_badge(r.get("stargazers_count", 0))
        link = f"[**{r['name']}**](https://github.com/{GITHUB_USER}/{r['name']})"
        cols = [link, desc]
        if lang:
            cols.append(f"`{lang}`")
        if badge:
            cols.append(badge)
        rows.append("| " + " | ".join(cols) + " |")

    header = "| 项目 | 简介 |"
    sep = "|------|------|"
    has_lang = any(r.get("language") for r in uncat)
    has_stars = any(r.get("stargazers_count", 0) > 0 for r in uncat)
    if has_lang:
        header += " 语言 |"
        sep += "------|"
    if has_stars:
        header += " ⭐ |"
        sep += "----|"

    return f"### 📦 其他项目\n\n{header}\n{sep}\n" + "\n".join(rows)


def generate_html_projects(repos, config):
    """Generate HTML project cards for index.html."""
    display = config.get("homepage_display", {})
    desc_overrides = config.get("descriptions", {})

    categorized = set()
    for names in config["categories"].values():
        categorized.update(names)
    categorized.update(config.get("exclude", []))

    cards = []
    for r in repos:
        name = r["name"]
        if name in config.get("exclude", []):
            continue

        info = display.get(name, {})
        desc = info.get("desc") or desc_overrides.get(name) or r.get("description") or ""
        tags = info.get("tags", [])
        if not tags and r.get("language"):
            tags = [r["language"]]

        stars = r.get("stargazers_count", 0)
        star_html = f' <span style="color:#f59e0b">⭐{stars}</span>' if stars > 0 else ""

        tags_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)

        cards.append(
            f'    <div class="proj">\n'
            f'      <h3><a href="https://github.com/{GITHUB_USER}/{html.escape(name)}" '
            f'style="color:#4a9eff;text-decoration:none">{html.escape(name)}</a>{star_html}</h3>\n'
            f'      <p>{html.escape(desc)}</p>\n'
            f'      {tags_html}\n'
            f'    </div>'
        )

    return "\n".join(cards)


def replace_section(text, start, end, content):
    """Replace content between markers."""
    pattern = re.escape(start) + r".*?" + re.escape(end)
    replacement = start + "\n" + content + "\n" + end
    new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
    if count == 0:
        print(f"WARNING: Markers {start}...{end} not found")
        return text, False
    return new_text, True


def main():
    repos = fetch_repos()
    repo_map = {r["name"]: r for r in repos}
    config = load_config()

    # --- Generate repo sections ---
    sections = []
    for cat_name, repo_names in config["categories"].items():
        section = generate_section(cat_name, repo_names, repo_map, config)
        if section:
            sections.append(section)

    uncategorized = generate_uncategorized(repos, config)
    if uncategorized:
        sections.append(uncategorized)

    repo_content = "\n\n---\n\n".join(sections)

    # --- Generate stats ---
    stats_content = generate_stats()

    # --- Update README.md ---
    with open(README_PATH, "r") as f:
        readme = f.read()

    readme, ok1 = replace_section(readme, REPO_START, REPO_END, repo_content)
    readme, ok2 = replace_section(readme, STATS_START, STATS_END, stats_content)

    if ok1 and ok2:
        with open(README_PATH, "w") as f:
            f.write(readme)
        print("README.md updated")
    else:
        print("WARNING: Some README markers not found")

    # --- Update index.html ---
    html_cards = generate_html_projects(repos, config)
    with open(HTML_PATH, "r") as f:
        html_text = f.read()

    html_text, ok3 = replace_section(html_text, HTML_START, HTML_END, html_cards)

    if ok3:
        with open(HTML_PATH, "w") as f:
            f.write(html_text)
        print("index.html updated")
    else:
        print("WARNING: HTML markers not found")

    print(f"Done — {len(repos)} repos processed")


if __name__ == "__main__":
    main()
