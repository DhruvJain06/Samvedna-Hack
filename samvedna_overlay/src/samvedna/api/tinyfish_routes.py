"""TinyFish sidecar ingest and console surfaces.

These routes never call the network. Welfare, evidence and trust-test payloads
arrive already fetched by the sidecar; this process only reads local files,
caches them, and writes the hash-chained ledger. Service-token POSTs are for
Airflow/scripts; session/demo identity is for the officer and auditor consoles.
"""
from __future__ import annotations

import hmac
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, Header, HTTPException, Request

from samvedna.config.flags import settings
from samvedna.disclosure.rbac import Principal

__all__ = ["attach"]

log = logging.getLogger("samvedna.tinyfish")

_welfare_directory: list[dict] = []
_hrms_records: list[dict] = []

_PID_HASH = re.compile(r"^[a-f0-9]{64}$")
_TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
_OUTCOMES = frozenset({"PASS", "FAIL", "INCONCLUSIVE"})
_WELFARE_ROLES = frozenset({"welfare_officer"})
_EVIDENCE_ROLES = frozenset({"auditor", "mental_health_authority"})
_TRUST_ROLES = frozenset({"auditor"})


def _root() -> Path:
    return Path(settings().tinyfish_root)


def _welfare_path() -> Path:
    return _root() / "data" / "welfare_directory.json"


def _baseline_path() -> Path:
    return _root() / "config" / "evidence_baseline.json"


def _reports_dir() -> Path:
    return _root() / "reports"


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


def service_token_ok(request: Request) -> bool:
    expected = settings().service_token
    offered = _bearer(request)
    if not expected or not offered:
        return False
    return hmac.compare_digest(offered, expected)


def require_service_token(request: Request) -> None:
    if not service_token_ok(request):
        raise HTTPException(status_code=403, detail="service token required")


def _principal(request: Request) -> Principal:
    from samvedna.api.app import principal_from

    return principal_from(
        request,
        request.headers.get("x-role", ""),
        request.headers.get("x-operator", ""),
        request.headers.get("x-units", ""),
    )


def _require_roles(principal: Principal, allowed: frozenset[str]) -> None:
    if principal.role not in allowed:
        raise HTTPException(status_code=403, detail="role is not permitted for this route")


def _read_welfare_file() -> list[dict]:
    path = _welfare_path()
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise HTTPException(status_code=500, detail="welfare directory is not a list")
    return [item for item in raw if isinstance(item, dict)]


def _flatten(detail: dict) -> dict[str, str | int | float | bool]:
    out: dict[str, str | int | float | bool] = {}
    for key, value in detail.items():
        if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
            out[str(key)] = value
        elif value is None:
            continue
        else:
            out[str(key)] = str(value)
    return out


def _load_welfare_if_empty() -> list[dict]:
    global _welfare_directory
    if not _welfare_directory:
        _welfare_directory = _read_welfare_file()
    return _welfare_directory


def attach(app, get_state):
    """Wire TinyFish routes onto the existing app, sharing AppState."""

    @app.post("/api/welfare/directory/refresh")
    def refresh_welfare_directory(request: Request):
        global _welfare_directory
        state = get_state(request)
        if service_token_ok(request):
            actor = "system:tinyfish"
        else:
            principal = _principal(request)
            _require_roles(principal, _WELFARE_ROLES)
            actor = f"{principal.role}:{principal.subject_id}"
        items = _read_welfare_file()
        _welfare_directory = items
        refreshed_at = datetime.now(UTC).isoformat()
        state.ledger.append(
            actor=actor,
            action="tinyfish.welfare_directory_refreshed",
            purpose="welfare:screening",
            detail={"count": len(items)},
        )
        return {"status": "ok", "count": len(items), "refreshed_at": refreshed_at}

    @app.get("/api/welfare/directory")
    def get_welfare_directory(
        request: Request,
        principal: Principal = Depends(_principal),
    ):
        _require_roles(principal, _WELFARE_ROLES)
        items = _load_welfare_if_empty()
        return {"items": items, "count": len(items)}

    @app.post("/api/alerts/evidence_drift")
    def evidence_drift(request: Request, payload: dict):
        require_service_token(request)
        state = get_state(request)
        required = ("field", "old_value", "new_value", "source_url", "snippet", "run_id")
        missing = [key for key in required if key not in payload]
        if missing:
            raise HTTPException(status_code=422, detail=f"missing fields: {', '.join(missing)}")
        log.warning(
            "Evidence drift: %s %s -> %s (%s)",
            payload["field"], payload["old_value"], payload["new_value"], payload["source_url"],
        )
        state.ledger.append(
            actor="system:tinyfish",
            action="tinyfish.evidence_drift_alert",
            purpose="governance:audit",
            detail=_flatten({k: payload[k] for k in required}),
        )
        return {"status": "logged"}

    @app.post("/api/audit/trust_test")
    def log_trust_test(request: Request, payload: dict):
        require_service_token(request)
        state = get_state(request)
        required = ("role", "action", "outcome", "timestamp", "run_id")
        missing = [key for key in required if key not in payload]
        if missing:
            raise HTTPException(status_code=422, detail=f"missing fields: {', '.join(missing)}")
        outcome = str(payload["outcome"])
        if outcome not in _OUTCOMES:
            raise HTTPException(
                status_code=422,
                detail="outcome must be PASS, FAIL, or INCONCLUSIVE",
            )
        if outcome == "FAIL":
            log.error(
                "Trust test FAIL role=%s action=%s run_id=%s",
                payload["role"], payload["action"], payload["run_id"],
            )
        state.ledger.append(
            actor="system:tinyfish",
            action="tinyfish.trust_test",
            purpose="governance:audit",
            detail=_flatten({k: payload[k] for k in required}),
        )
        return {"status": "logged"}

    @app.post("/api/alerts/trust_failure")
    def trust_failure(request: Request, payload: dict):
        require_service_token(request)
        state = get_state(request)
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(status_code=422, detail="text is required")
        log.critical("Trust failure alert: %s", text)
        state.ledger.append(
            actor="system:tinyfish",
            action="tinyfish.trust_failure_alert",
            purpose="governance:audit",
            detail={"text": text},
        )
        return {"status": "alerted"}

    @app.get("/api/tinyfish/evidence-baseline")
    def evidence_baseline(
        request: Request,
        principal: Principal = Depends(_principal),
    ):
        _require_roles(principal, _EVIDENCE_ROLES)
        state = get_state(request)
        path = _baseline_path()
        if not path.is_file():
            raise HTTPException(status_code=404, detail="evidence baseline is not on disk")
        body = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(body, dict):
            raise HTTPException(status_code=500, detail="evidence baseline is not an object")
        state.ledger.append(
            actor=f"{principal.role}:{principal.subject_id}",
            action="tinyfish.evidence_baseline_viewed",
            purpose="governance:audit",
            detail={"source": str(path)},
        )
        return body

    @app.get("/api/tinyfish/trust-tests/latest")
    def latest_trust_tests(
        request: Request,
        principal: Principal = Depends(_principal),
    ):
        _require_roles(principal, _TRUST_ROLES)
        reports = sorted(_reports_dir().glob("nightly_trust_report_*.md"))
        if not reports:
            return {"date": None, "results": [], "overall": None}
        latest = reports[-1]
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", latest.name)
        date = date_match.group(1) if date_match else None
        results, overall = _parse_trust_report(latest.read_text(encoding="utf-8"))
        return {"date": date, "results": results, "overall": overall}

    @app.post("/api/ingest/hrms")
    def ingest_hrms(
        request: Request,
        payload: list[dict] | dict,
        x_tinyfish_run_id: str = Header(default="", alias="X-TinyFish-Run-Id"),
    ):
        """Accept a full HRMS batch or skip it. Never write a partial batch."""
        global _hrms_records
        require_service_token(request)
        state = get_state(request)
        records = payload if isinstance(payload, list) else payload.get("records")
        if not isinstance(records, list) or not records:
            raise HTTPException(status_code=422, detail="expected a non-empty records list")
        try:
            checked = [_validate_hrms(item) for item in records]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        _hrms_records = checked
        state.ledger.append(
            actor="system:tinyfish",
            action="tinyfish.hrms_ingested",
            purpose="welfare:screening",
            detail={"count": len(checked), "run_id": x_tinyfish_run_id or ""},
        )
        return {"status": "ok", "count": len(checked), "run_id": x_tinyfish_run_id or ""}


def _validate_hrms(record: dict) -> dict:
    if not isinstance(record, dict):
        raise ValueError("each HRMS row must be an object")
    pid = record.get("pid_hash", "")
    if not _PID_HASH.match(str(pid)):
        raise ValueError("pid_hash must be 64 lowercase hex characters")
    duty = record.get("duty_days_consecutive")
    leave = record.get("leave_balance_days")
    unit = record.get("unit_code")
    if not isinstance(duty, int) or duty < 0:
        raise ValueError("duty_days_consecutive must be a non-negative int")
    if not isinstance(leave, int) or leave < 0:
        raise ValueError("leave_balance_days must be a non-negative int")
    if not isinstance(unit, str) or not unit:
        raise ValueError("unit_code must be a non-empty string")
    posting = record.get("last_posting_change_date")
    if posting is not None and not re.match(r"^\d{4}-\d{2}-\d{2}", str(posting)):
        raise ValueError("last_posting_change_date must be ISO-8601 or null")
    return {
        "pid_hash": pid,
        "duty_days_consecutive": duty,
        "leave_balance_days": leave,
        "last_posting_change_date": posting,
        "unit_code": unit,
    }


def _parse_trust_report(markdown: str) -> tuple[list[dict], str | None]:
    results: list[dict] = []
    overall = None
    for line in markdown.splitlines():
        if line.startswith("**Overall:**"):
            token = line.split(":", 1)[1].strip().strip("*").strip()
            if token in _OUTCOMES:
                overall = token
            continue
        match = _TABLE_ROW.match(line)
        if not match:
            continue
        role, action, outcome_cell = (part.strip() for part in match.groups())
        if role.lower() == "role" or set(role) <= {"-"}:
            continue
        outcome = None
        for token in reversed(re.split(r"\s+", outcome_cell)):
            cleaned = token.strip("*")
            if cleaned in _OUTCOMES:
                outcome = cleaned
                break
        if outcome is None:
            continue
        results.append({"role": role, "action": action, "outcome": outcome})
    if overall is None and results:
        if any(r["outcome"] == "FAIL" for r in results):
            overall = "FAIL"
        elif any(r["outcome"] == "INCONCLUSIVE" for r in results):
            overall = "INCONCLUSIVE"
        else:
            overall = "PASS"
    return results, overall
