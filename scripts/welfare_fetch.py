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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from tinyfish_cli import (  # noqa: E402
    extract_text,
    fetch_content_cmd,
    load_sidecar_env,
    parse_cli_json,
    run_tinyfish,
)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

load_sidecar_env()

DATA_DIR = ROOT / "data"
DIRECTORY_FILE = DATA_DIR / "welfare_directory.json"
CHANGELOG_FILE = DATA_DIR / "welfare_directory_changelog.jsonl"

SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")

PUBLIC_URLS = [
    "https://www.crpf.gov.in/welfare.htm",
    "https://www.mha.gov.in/",
    "https://pib.gov.in/",
]


def fetch_url(url: str) -> str:
    """Fetch one public URL via TinyFish CLI 0.49 and return page text."""
    cmd = fetch_content_cmd([url])
    result = run_tinyfish(cmd, timeout=90)
    if result.returncode != 0:
        err = (result.stderr or "")[:200]
        log.warning("Failed to fetch %s: %s", url, err)
        return ""
    payload = parse_cli_json(result.stdout)
    text = extract_text(payload) if payload is not None else ""
    if not text:
        text = (result.stdout or "").strip()
    return text


def parse_welfare_items(html: str, source_url: str) -> list[dict]:
    """Naive extraction — replace with proper parser for production."""
    items = []
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
    return items[:20]


def load_existing() -> list[dict]:
    if DIRECTORY_FILE.exists():
        with open(DIRECTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def deduplicate_key(item: dict) -> tuple:
    return (item.get("url", ""), item.get("effective_date"))


def diff(existing: list[dict], new_items: list[dict]) -> tuple[list, list]:
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
            log.warning("  Skipped (unreachable) — keeping last-known data for this source")

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
