"""
scripts/evidence_watch.py
Monitors policy/research sources for changes to SAMVEDNA baseline numbers.

Usage:
  python evidence_watch.py              # check since last_checked in baseline
  python evidence_watch.py --since 2024-01-01
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
BASELINE_FILE = CONFIG_DIR / "evidence_baseline.json"
CACHE_DIR = ROOT / "data" / "evidence_cache"

SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")

SEARCH_QUERIES = [
    "CAPF suicide report MHA site:pib.gov.in OR site:mha.gov.in",
    "CAPF suicide 2023 OR 2024 OR 2025 report",
    "burnout prediction AUROC armed forces",
    "CAPF personnel suicide prevention circular",
]

# Patterns that extract numeric values near known keywords
EXTRACTION_PATTERNS = {
    "capf_suicide_per_year": [
        r"(\d+)\s*(?:CAPF|police)\s*(?:personnel)?\s*(?:died by suicide|suicide deaths?)\s*(?:per year|annually|each year)",
        r"(?:per year|annual|yearly)[^.]*?(\d+)\s*(?:CAPF|police)\s*suicide",
    ],
    "capf_suicide_5yr": [
        r"(\d[\d,]+)\s*(?:CAPF|police)\s*(?:personnel)?\s*(?:died by suicide|suicide deaths?)[^.]*(?:2018|2019|2020|2021|2022|five.year|5.year)",
    ],
    "burnout_specificity": [
        r"specificity[^\d]*?(0\.\d+)",
        r"(0\.\d+)\s*specificity",
    ],
    "target_auroc": [
        r"AUROC[^\d]*?(0\.\d+)",
        r"(0\.\d+)\s*AUROC",
    ],
}

DRIFT_THRESHOLD = 0.05  # 5 %


def tinyfish_search(query: str) -> list[str]:
    """Run a TinyFish search and return a list of URLs."""
    result = subprocess.run(
        ["npx", "-y", "@tiny-fish/cli@latest", "search", query, "--fetch"],
        capture_output=True, text=True, timeout=120,
    )
    urls = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
            if event.get("type") == "COMPLETE":
                for item in event.get("result", {}).get("results", []):
                    urls.append(item.get("url", ""))
        except json.JSONDecodeError:
            if line.startswith("http"):
                urls.append(line.strip())
    return [u for u in urls if u]


def tinyfish_fetch(url: str) -> str:
    """Fetch a URL via TinyFish and return text content."""
    result = subprocess.run(
        ["npx", "-y", "@tiny-fish/cli@latest", "fetch", url],
        capture_output=True, text=True, timeout=60,
    )
    return result.stdout if result.returncode == 0 else ""


def extract_numbers(text: str) -> dict[str, float]:
    """Extract numeric values for each baseline field."""
    found: dict[str, float] = {}
    for field, patterns in EXTRACTION_PATTERNS.items():
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                raw = m.group(1).replace(",", "")
                try:
                    found[field] = float(raw)
                    break
                except ValueError:
                    pass
    return found


def check_drift(baseline: dict, extracted: dict, source_url: str) -> list[dict]:
    """Return list of drift events where |new - old| / old > threshold."""
    drifts = []
    for field, new_val in extracted.items():
        old_val = baseline.get(field)
        if old_val is None:
            continue
        if old_val == 0:
            continue
        if abs(new_val - old_val) / abs(old_val) > DRIFT_THRESHOLD:
            drifts.append({
                "field": field,
                "old_value": old_val,
                "new_value": new_val,
                "source_url": source_url,
                "snippet": f"Extracted {new_val} vs baseline {old_val}",
            })
    return drifts


def alert_drift(drift: dict, run_id: str) -> None:
    import requests  # noqa: PLC0415
    try:
        resp = requests.post(
            f"{SAMVEDNA_API_BASE}/api/alerts/evidence_drift",
            json={**drift, "run_id": run_id},
            headers={"Authorization": f"Bearer {SAMVEDNA_SERVICE_TOKEN}"},
            timeout=15,
        )
        log.info("Drift alert sent: %s", resp.status_code)
    except Exception as exc:
        log.warning("Could not send drift alert: %s", exc)


def load_baseline() -> dict:
    if BASELINE_FILE.exists():
        with open(BASELINE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_baseline(baseline: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)


def cache_text(url: str, text: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9]", "_", url)[:80]
    path = CACHE_DIR / f"{safe_name}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text[:1_000_000])  # max 1 MB


def main(since: str | None = None) -> None:
    baseline = load_baseline()
    run_id = datetime.now(timezone.utc).strftime("evidence-watch-%Y%m%dT%H%M%S")

    all_urls: list[str] = []
    for query in SEARCH_QUERIES:
        log.info("Searching: %s", query)
        urls = tinyfish_search(query)
        log.info("  Found %d URLs", len(urls))
        all_urls.extend(urls[:5])  # top 5 per query

    all_urls = list(dict.fromkeys(all_urls))  # deduplicate, preserve order
    log.info("Total unique URLs to fetch: %d", len(all_urls))

    any_drift = False
    for url in all_urls:
        log.info("Fetching %s", url)
        text = tinyfish_fetch(url)
        if not text:
            log.warning("  Empty — skipped")
            continue
        cache_text(url, text)
        extracted = extract_numbers(text)
        if not extracted:
            continue
        drifts = check_drift(baseline, extracted, url)
        for drift in drifts:
            log.warning("DRIFT DETECTED: %s", drift)
            alert_drift(drift, run_id)
            any_drift = True

    now = datetime.now(timezone.utc).isoformat()
    baseline["last_checked"] = now
    save_baseline(baseline)
    log.info("last_checked updated to %s", now)

    if any_drift:
        log.warning("Evidence drift detected — alerts sent to SAMVEDNA.")
    else:
        log.info("No significant drift detected.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="ISO-8601 date; only fetch docs newer than this")
    args = parser.parse_args()
    main(since=args.since)
