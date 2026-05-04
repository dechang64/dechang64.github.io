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

START_MARKER = "<!-- AUTO-GENERATED-START -->"
END_MARKER = "<!-- AUTO-GENERATED-END -->"
HTML_START = "<!-- PROJECTS-AUTO-START -->"
HTML_END = "<!-- PROJECTS-AUTO-END -->"


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


def generate_section(title, repo_names, repo_map, config):
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
    separator = "|------|------|"
    has_lang = any(repo_map.get(n, {}).get("language") for n in repo_names if n in repo_map)
    has_stars = any(repo_map.get(n, {}).get("stargazers_count", 0) > 0 for n in repo_names if n in repo_map)
    if has_lang:
        header += " 语言 |"
        separator += "------|"
    if has_stars:
        header += " ⭐ |"
        separator += "----|"

    return f"### {title}\n\n{header}\n{separator}\n" + "\n".join(rows)


def generate_uncategorized(repos, config):
    categorized = set()
    for names in config["categories"].values():
        categorized.update(names)
    categorized.update(config.get("exclude", []))
    uncategorized = [r for r in repos if r["name"] not in categorized]
    if not uncategorized:
        return ""

    desc_overrides = config.get("descriptions", {})
    rows = []
    for r in uncategorized:
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
    separator = "|------|------|"
    has_lang = any(r.get("language") for r in uncategorized)
    has_stars = any(r.get("stargazers_count", 0) > 0 for r in uncategorized)
    if has_lang:
        header += " 语言 |"
        separator += "------|"
    if has_stars:
        header += " ⭐ |"
        separator += "----|"

    return f"### 📦 其他项目\n\n{header}\n{separator}\n" + "\n".join(rows)


def generate_html_projects(repos, config):
    """Generate HTML project cards for index.html."""
    display = config.get("homepage_display", {})
    desc_overrides = config.get("descriptions", {})

    # Collect all repos in order
    all_names = []
    for names in config["categories"].values():
        all_names.extend(names)

    repo_map = {r["name"]: r for r in repos}
    cards = []

    for name in all_names:
        if name not in repo_map:
            continue
        r = repo_map[name]
        info = display.get(name, {})
        desc = info.get("desc") or desc_overrides.get(name) or r.get("description") or ""
        tags = info.get("tags") or ([r["language"]] if r.get("language") else [])
        stars = r.get("stargazers_count", 0)

        tags_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
        star_html = f' <span class="tag" style="background:#1a3a2a;color:#4ade80">⭐ {stars}</span>' if stars > 0 else ""

        cards.append(
            f'    <div class="proj">\n'
            f'      <h3>{html.escape(name)}</h3>\n'
            f'      <p>{html.escape(desc)}</p>\n'
            f'      {tags_html}{star_html}\n'
            f'    </div>'
        )

    # Uncategorized
    categorized = set(all_names) | set(config.get("exclude", []))
    for r in repos:
        if r["name"] not in categorized:
            name = r["name"]
            info = display.get(name, {})
            desc = info.get("desc") or desc_overrides.get(name) or r.get("description") or ""
            tags = info.get("tags") or ([r["language"]] if r.get("language") else [])
            stars = r.get("stargazers_count", 0)
            tags_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)
            star_html = f' <span class="tag" style="background:#1a3a2a;color:#4ade80">⭐ {stars}</span>' if stars > 0 else ""
            cards.append(
                f'    <div class="proj">\n'
                f'      <h3>{html.escape(name)}</h3>\n'
                f'      <p>{html.escape(desc)}</p>\n'
                f'      {tags_html}{star_html}\n'
                f'    </div>'
            )

    return "\n".join(cards)


def update_file(filepath, start_marker, end_marker, content):
    with open(filepath, "r") as f:
        text = f.read()

    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)
    replacement = start_marker + "\n" + content + "\n" + end_marker

    new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)
    if count == 0:
        print(f"WARNING: Markers not found in {filepath}")
        return False

    with open(filepath, "w") as f:
        f.write(new_text)
    return True


def main():
    repos = fetch_repos()
    repo_map = {r["name"]: r for r in repos}
    config = load_config()

    # --- Update README.md ---
    sections = []
    for cat_name, repo_names in config["categories"].items():
        section = generate_section(cat_name, repo_names, repo_map, config)
        if section:
            sections.append(section)

    uncategorized = generate_uncategorized(repos, config)
    if uncategorized:
        sections.append(uncategorized)

    readme_content = "\n\n---\n\n".join(sections)
    update_file(README_PATH, START_MARKER, END_MARKER, readme_content)
    print(f"README.md updated")

    # --- Update index.html ---
    html_cards = generate_html_projects(repos, config)
    update_file(HTML_PATH, HTML_START, HTML_END, html_cards)
    print(f"index.html updated")

    print(f"Done — {len(repos)} repos processed")


if __name__ == "__main__":
    main()
