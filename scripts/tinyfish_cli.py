"""TinyFish CLI 0.49 helpers for SAMVEDNA sidecar scripts and DAGs.

CLI grammar (not MCP tool names):
  tinyfish search query "<query>"
  tinyfish fetch content get <url> [<url> ...]   # up to 10
  tinyfish agent run "<goal>" --url <url> --sync

Uses a local `tinyfish` binary when present; otherwise npx @tiny-fish/cli.
YAML under agents/ is a human spec / goal source — the CLI does not execute it.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

NPX_PACKAGE = "@tiny-fish/cli@latest"
FETCH_BATCH = 10

DATE_KEYS = (
    "published_at",
    "publishedAt",
    "published",
    "date",
    "last_updated",
    "lastUpdated",
    "timestamp",
)


def tinyfish_argv() -> list[str]:
    """Prefer an installed CLI; fall back to npx only if tinyfish is absent."""
    resolved = shutil.which("tinyfish")
    if resolved:
        return [resolved]
    return ["npx", "-y", NPX_PACKAGE]


def search_query_cmd(query: str) -> list[str]:
    return tinyfish_argv() + ["search", "query", query]


def fetch_content_cmd(urls: list[str]) -> list[str]:
    if not urls:
        raise ValueError("fetch_content_cmd requires at least one URL")
    if len(urls) > FETCH_BATCH:
        raise ValueError(f"fetch_content_cmd accepts at most {FETCH_BATCH} URLs")
    return tinyfish_argv() + ["fetch", "content", "get", *urls]


def agent_run_cmd(
    goal: str,
    url: str,
    *,
    use_vault: bool = True,
    output_schema_file: str | Path | None = None,
    extra: list[str] | None = None,
) -> list[str]:
    cmd = tinyfish_argv() + ["agent", "run", goal, "--url", url, "--sync"]
    if use_vault:
        cmd.append("--use-vault")
    if output_schema_file:
        cmd.extend(["--output-schema-file", str(output_schema_file)])
    if extra:
        cmd.extend(extra)
    return cmd


def run_tinyfish(cmd: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    log.info("TinyFish: %s", " ".join(cmd[:8]) + (" …" if len(cmd) > 8 else ""))
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def parse_cli_json(stdout: str) -> Any:
    """Parse CLI JSON (default). Tolerate a trailing/leading non-JSON banner."""
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"[{\[]", text):
        try:
            obj, _end = decoder.raw_decode(text[match.start():])
            return obj
        except json.JSONDecodeError:
            continue
    return None


def _walk_dicts(payload: Any):
    if isinstance(payload, dict):
        yield payload
        for value in payload.values():
            yield from _walk_dicts(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _walk_dicts(item)


def extract_urls(payload: Any) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        if url and url.startswith("http") and url not in seen:
            seen.add(url)
            urls.append(url)

    if isinstance(payload, str) and payload.startswith("http"):
        add(payload)
        return urls

    for obj in _walk_dicts(payload):
        for key in ("url", "link", "href"):
            value = obj.get(key)
            if isinstance(value, str):
                add(value)
        results = obj.get("results")
        if isinstance(results, list):
            for item in results:
                if isinstance(item, str):
                    add(item)
                elif isinstance(item, dict):
                    for key in ("url", "link", "href"):
                        value = item.get(key)
                        if isinstance(value, str):
                            add(value)
    return urls


def extract_text(payload: Any) -> str:
    """Best-effort page text from fetch content JSON."""
    chunks: list[str] = []
    text_keys = ("markdown", "content", "text", "html", "body")
    if isinstance(payload, str):
        return payload
    for obj in _walk_dicts(payload):
        for key in text_keys:
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(value)
    return "\n\n".join(chunks)


def extract_search_items(payload: Any) -> list[dict]:
    items: list[dict] = []
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    for obj in _walk_dicts(payload):
        results = obj.get("results")
        if isinstance(results, list) and results and isinstance(results[0], dict):
            return [x for x in results if isinstance(x, dict)]
        hits = obj.get("hits")
        if isinstance(hits, list) and hits and isinstance(hits[0], dict):
            return [x for x in hits if isinstance(x, dict)]
    if isinstance(payload, dict) and any(k in payload for k in ("url", "link")):
        items.append(payload)
    return items


def parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if text.lower() in {"null", "none"}:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        try:
            dt = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def resolve_since(cli_since: str | None, last_checked: str | None) -> datetime | None:
    return parse_iso_datetime(cli_since) or parse_iso_datetime(last_checked)


def with_after_clause(query: str, since: datetime | None) -> str:
    if since is None:
        return query
    stamp = since.date().isoformat()
    if f"after:{stamp}" in query.lower():
        return query
    return f"{query} after:{stamp}"


def item_is_on_or_after(item: dict, since: datetime | None) -> bool:
    """Keep items with no date; drop dated items older than since."""
    if since is None or not isinstance(item, dict):
        return True
    for key in DATE_KEYS:
        dt = parse_iso_datetime(str(item[key]) if key in item and item[key] is not None else None)
        if dt is not None:
            return dt >= since
    return True


def extract_agent_payload(payload: Any) -> tuple[Any, str | None]:
    """Return (result, run_id) from a --sync agent run JSON object."""
    if payload is None:
        return None, None
    if isinstance(payload, list):
        return payload, None
    if not isinstance(payload, dict):
        return payload, None
    run_id = payload.get("run_id") or payload.get("id") or payload.get("runId")
    if isinstance(run_id, str) and not run_id:
        run_id = None
    result = payload.get("result", payload)
    if isinstance(result, dict):
        inner = result.get("result", result)
        nested_id = result.get("run_id") or result.get("id")
        if isinstance(nested_id, str) and nested_id:
            run_id = run_id or nested_id
        return inner, run_id
    return result, run_id


def extract_records(result: Any) -> list[dict]:
    if isinstance(result, list):
        return [x for x in result if isinstance(x, dict)]
    if isinstance(result, dict):
        for key in ("records", "items", "data", "result"):
            value = result.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def extract_outcome(result: Any) -> str:
    if isinstance(result, dict):
        outcome = result.get("outcome")
        if isinstance(outcome, str) and outcome:
            return outcome.upper()
    return "INCONCLUSIVE"


def load_cli_goal(yaml_path: Path) -> str:
    """Read a top-level folded `cli_goal: |` block from a human-spec YAML file."""
    text = yaml_path.read_text(encoding="utf-8")
    match = re.search(r"^cli_goal:\s*[|>]\s*\n((?:[ \t]+.*\n?)+)", text, re.MULTILINE)
    if not match:
        raise ValueError(f"No cli_goal block in {yaml_path}")
    lines = []
    for line in match.group(1).splitlines():
        lines.append(re.sub(r"^[ \t]{2,}", "", line) if line.startswith((" ", "\t")) else line)
    return "\n".join(lines).strip()


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_sidecar_env() -> None:
    env_path = project_root() / ".env"
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if env_path.exists():
        load_dotenv(env_path)


def samvedna_env() -> dict[str, str]:
    keys = (
        "SAMVEDNA_API_BASE",
        "SAMVEDNA_SERVICE_TOKEN",
        "SAMVEDNA_CONSOLE_URL",
        "SAMVEDNA_TRUST_TEST_ENV",
        "TARGET_PORTAL_URL",
        "UNIT_CODES",
        "ONCALL_WEBHOOK_URL",
    )
    return {k: os.getenv(k, "") for k in keys}
