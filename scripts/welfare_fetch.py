"""
scripts/welfare_fetch.py
Orchestrates the TinyFish welfare directory fetch for SAMVEDNA.

Usage:
  python welfare_fetch.py            # run and write data/welfare_directory.json
  python welfare_fetch.py --dry-run  # print what would change, write nothing
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DIRECTORY_FILE = DATA_DIR / "welfare_directory.json"
CHANGELOG_FILE = DATA_DIR / "welfare_directory_changelog.jsonl"
AGENT_CONFIG = ROOT / "agents" / "welfare_fetch.yaml"

SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")

PUBLIC_URLS = [
    "https://www.crpf.gov.in/welfare.htm",
    "https://www.mha.gov.in/",
    "https://pib.gov.in/",
]


def fetch_url(url: str) -> str:
    """Use TinyFish CLI to fetch a public URL and return page text."""
    result = subprocess.run(
        ["npx", "-y", "@tiny-fish/cli@latest", "fetch", url],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        log.warning("Failed to fetch %s: %s", url, result.stderr[:200])
        return ""
    return result.stdout


def parse_welfare_items(html: str, source_url: str) -> list[dict]:
    """Naive extraction — replace with proper parser for production."""
    import re
    items = []
    # Look for phone patterns near welfare keywords
    phone_re = re.compile(r"\b(?:1800[\s-]?\d{6,}|\d{10})\b")
    for match in phone_re.finditer(html):
        start = max(0, match.start() - 120)
        snippet = html[start: match.end() + 40]
        items.append({
            "scheme_name": snippet.strip()[:80],
            "type": "helpline",
            "contact": match.group(),
            "effective_date": None,
            "url": source_url,
        })
    return items[:20]  # cap per source


def load_existing() -> list[dict]:
    if DIRECTORY_FILE.exists():
        with open(DIRECTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def deduplicate_key(item: dict) -> tuple:
    return (item.get("url", ""), item.get("effective_date"))


def diff(existing: list[dict], new_items: list[dict]) -> tuple[list, list]:
    """Return (added, unchanged)."""
    existing_keys = {deduplicate_key(i) for i in existing}
    added = [i for i in new_items if deduplicate_key(i) not in existing_keys]
    return added, existing


def notify_samvedna():
    import requests  # noqa: PLC0415
    try:
        resp = requests.post(
            f"{SAMVEDNA_API_BASE}/api/welfare/directory/refresh",
            headers={"Authorization": f"Bearer {SAMVEDNA_SERVICE_TOKEN}"},
            timeout=15,
        )
        log.info("Refresh notified: %s", resp.status_code)
    except Exception as exc:
        log.warning("Could not notify SAMVEDNA: %s", exc)


def main(dry_run: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_new_items: list[dict] = []
    for url in PUBLIC_URLS:
        log.info("Fetching %s", url)
        html = fetch_url(url)
        if html:
            items = parse_welfare_items(html, url)
            log.info("  Extracted %d items", len(items))
            all_new_items.extend(items)
        else:
            log.warning("  Skipped (unreachable)")

    existing = load_existing()
    added, _ = diff(existing, all_new_items)
    now = datetime.now(timezone.utc).isoformat()

    if dry_run:
        log.info("DRY RUN — would add %d entries:", len(added))
        for item in added:
            print(json.dumps(item))
        return

    if not added:
        log.info("No new entries found.")
        return

    for item in added:
        item["added_at"] = now
    merged = existing + added

    with open(DIRECTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    log.info("Wrote %d total entries to %s", len(merged), DIRECTORY_FILE)

    with open(CHANGELOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": now, "added": added}) + "\n")

    notify_samvedna()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
