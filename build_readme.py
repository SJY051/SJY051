"""Rebuild the Recent Activity section of README.md from public GitHub events.

Runs in CI (see .github/workflows/build-readme.yml) and locally:
    GITHUB_TOKEN=$(gh auth token) python build_readme.py
"""

import json
import os
import re
import urllib.request

USER = "SJY051"
README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
MAX_ITEMS = 5


def fetch_events():
    url = f"https://api.github.com/users/{USER}/events/public?per_page=30"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def describe(event):
    """Turn one event into (date, markdown line), or None if not worth showing."""
    repo = event["repo"]["name"]
    repo_url = f"https://github.com/{repo}"
    date = event["created_at"][:10]
    kind = event["type"]
    payload = event.get("payload", {})

    if kind == "PushEvent":
        n = payload.get("size") or len(payload.get("commits", []))
        return date, f"Pushed {n} commit{'s' if n != 1 else ''} to [{repo}]({repo_url})"
    if kind == "PullRequestEvent":
        pr = payload.get("pull_request", {})
        if payload.get("action") == "opened":
            return date, f"Opened PR [{pr.get('title', '?')}]({pr.get('html_url', repo_url)}) in [{repo}]({repo_url})"
        if payload.get("action") == "closed" and pr.get("merged"):
            return date, f"Merged PR [{pr.get('title', '?')}]({pr.get('html_url', repo_url)}) in [{repo}]({repo_url})"
        return None
    if kind == "IssuesEvent" and payload.get("action") == "opened":
        issue = payload.get("issue", {})
        return date, f"Opened issue [{issue.get('title', '?')}]({issue.get('html_url', repo_url)}) in [{repo}]({repo_url})"
    if kind == "ReleaseEvent" and payload.get("action") == "published":
        rel = payload.get("release", {})
        name = rel.get("name") or rel.get("tag_name", "?")
        return date, f"Released [{name}]({rel.get('html_url', repo_url)}) in [{repo}]({repo_url})"
    if kind == "CreateEvent" and payload.get("ref_type") == "repository":
        return date, f"Created repository [{repo}]({repo_url})"
    return None


def build_section(events):
    lines = []
    for event in events:
        item = describe(event)
        if item:
            lines.append(f"- `{item[0]}` — {item[1]}")
        if len(lines) >= MAX_ITEMS:
            break
    return "\n".join(lines) if lines else "*Quiet lately — building things offline.*"


def replace_section(text, content):
    pattern = re.compile(
        r"(<!-- recent_activity starts -->).*(<!-- recent_activity ends -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit("recent_activity markers not found in README.md")
    return pattern.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(2)}", text)


def main():
    section = build_section(fetch_events())
    with open(README, encoding="utf-8") as f:
        text = f.read()
    updated = replace_section(text, section)
    if updated != text:
        with open(README, "w", encoding="utf-8", newline="\n") as f:
            f.write(updated)
        print("README updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
