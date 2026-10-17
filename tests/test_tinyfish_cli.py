"""Unit tests for TinyFish CLI 0.49 JSON parsing and --since filtering."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from tinyfish_cli import (
    agent_run_cmd,
    extract_agent_payload,
    extract_outcome,
    extract_records,
    extract_search_items,
    extract_text,
    extract_urls,
    fetch_content_cmd,
    item_is_on_or_after,
    parse_cli_json,
    resolve_since,
    search_query_cmd,
    with_after_clause,
)


def test_search_query_cmd_uses_cli_049_grammar():
    cmd = search_query_cmd("CAPF welfare")
    assert cmd[-3:] == ["search", "query", "CAPF welfare"]


def test_fetch_content_cmd_uses_cli_049_grammar():
    cmd = fetch_content_cmd(["https://example.com"])
    assert cmd[-4:-1] == ["fetch", "content", "get"]
    assert cmd[-1] == "https://example.com"


def test_agent_run_cmd_sync_url_vault():
    cmd = agent_run_cmd("do the thing", "https://portal.example", use_vault=True)
    assert "agent" in cmd and "run" in cmd
    assert "--url" in cmd and "--sync" in cmd and "--use-vault" in cmd
    assert "do the thing" in cmd
    assert cmd[cmd.index("--url") + 1] == "https://portal.example"


def test_parse_cli_json_object():
    payload = parse_cli_json('{"results":[{"url":"https://pib.gov.in/a"}]}')
    assert payload["results"][0]["url"] == "https://pib.gov.in/a"


def test_parse_cli_json_ignores_banner():
    raw = 'TinyFish CLI\n{"markdown":"# Hello"}\n'
    payload = parse_cli_json(raw)
    assert payload["markdown"] == "# Hello"


def test_extract_urls_from_search_results():
    payload = {"results": [{"url": "https://a.example"}, {"link": "https://b.example"}]}
    assert extract_urls(payload) == ["https://a.example", "https://b.example"]


def test_extract_text_prefers_markdown():
    payload = {"results": [{"markdown": "page body", "html": "<p>x</p>"}]}
    text = extract_text(payload)
    assert "page body" in text


def test_extract_search_items():
    payload = {"data": {"results": [{"url": "https://x", "date": "2024-06-01"}]}}
    items = extract_search_items(payload)
    assert items[0]["url"] == "https://x"


def test_resolve_since_prefers_cli_over_last_checked():
    dt = resolve_since("2024-01-01", "2025-01-01T00:00:00+00:00")
    assert dt.date().isoformat() == "2024-01-01"


def test_resolve_since_falls_back_to_last_checked():
    dt = resolve_since(None, "2024-03-15T12:00:00Z")
    assert dt.year == 2024 and dt.month == 3 and dt.day == 15


def test_with_after_clause():
    since = datetime(2024, 1, 1, tzinfo=timezone.utc)
    q = with_after_clause("CAPF suicide report", since)
    assert "after:2024-01-01" in q


def test_item_is_on_or_after_drops_old():
    since = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert item_is_on_or_after({"url": "https://x", "date": "2023-01-01"}, since) is False
    assert item_is_on_or_after({"url": "https://x", "date": "2024-07-01"}, since) is True
    assert item_is_on_or_after({"url": "https://x"}, since) is True


def test_extract_agent_payload_sync_shape():
    payload = {
        "run_id": "run-1",
        "status": "COMPLETED",
        "result": [{"pid_hash": "a" * 64, "unit_code": "U01"}],
    }
    result, run_id = extract_agent_payload(payload)
    assert run_id == "run-1"
    records = extract_records(result)
    assert records[0]["unit_code"] == "U01"


def test_extract_outcome_from_result():
    assert extract_outcome({"outcome": "pass"}) == "PASS"
    assert extract_outcome({}) == "INCONCLUSIVE"
