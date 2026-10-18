"""TinyFish sidecar routes: session surfaces and service-token ingest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from samvedna.api import tinyfish_routes
from samvedna.api.app import AppState, create_app
from samvedna.config.flags import reset_settings

TOKEN = "test-sidecar-token"


def _pid(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setenv("SAMVEDNA_SERVICE_TOKEN", TOKEN)
    monkeypatch.setenv("SAMVEDNA_TINYFISH_ROOT", str(tmp_path))
    reset_settings()
    tinyfish_routes._welfare_directory = []
    tinyfish_routes._hrms_records = []

    data = tmp_path / "data"
    config = tmp_path / "config"
    reports = tmp_path / "reports"
    data.mkdir()
    config.mkdir()
    reports.mkdir()
    (data / "welfare_directory.json").write_text(
        json.dumps(
            [
                {
                    "scheme_name": "CAPF Welfare Helpline (placeholder)",
                    "type": "helpline",
                    "contact": "1800-XXX-XXXX",
                    "url": "https://www.crpf.gov.in/welfare.htm",
                }
            ]
        ),
        encoding="utf-8",
    )
    (config / "evidence_baseline.json").write_text(
        json.dumps(
            {
                "capf_suicide_per_year": 130,
                "source": "fixture",
                "last_checked": None,
            }
        ),
        encoding="utf-8",
    )
    (reports / "nightly_trust_report_2026-10-17.md").write_text(
        "\n".join(
            [
                "# Nightly Trust Test Report — 2026-10-17",
                "",
                "| Role | Action | Outcome |",
                "|------|--------|---------|",
                "| commander | open_individual_case | ✓ PASS |",
                "| auditor | change_verdict | ✗ FAIL |",
                "",
                "**Overall:** FAIL",
            ]
        ),
        encoding="utf-8",
    )

    client = TestClient(create_app(AppState()))
    yield client, tmp_path
    reset_settings()
    tinyfish_routes._welfare_directory = []
    tinyfish_routes._hrms_records = []


def wo():
    return {"X-Role": "welfare_officer", "X-Operator": "WO-1", "X-Units": "UNIT-01"}


def au():
    return {"X-Role": "auditor", "X-Operator": "AU-1"}


def svc():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_refresh_returns_200_and_correct_shape(world):
    client, _ = world
    body = client.post("/api/welfare/directory/refresh", headers=wo()).json()
    assert client.post("/api/welfare/directory/refresh", headers=wo()).status_code == 200
    assert body["status"] == "ok"
    assert body["count"] == 1
    assert "refreshed_at" in body


def test_get_directory_returns_items_list(world):
    client, _ = world
    client.post("/api/welfare/directory/refresh", headers=wo())
    body = client.get("/api/welfare/directory", headers=wo()).json()
    assert body["count"] == 1
    assert body["items"][0]["scheme_name"]
    assert body["items"][0]["type"] == "helpline"


def test_evidence_drift_with_valid_body_returns_200(world):
    client, _ = world
    response = client.post(
        "/api/alerts/evidence_drift",
        headers=svc(),
        json={
            "field": "capf_suicide_per_year",
            "old_value": 130.0,
            "new_value": 140.0,
            "source_url": "https://example.test/paper",
            "snippet": "synthetic",
            "run_id": "run-1",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "logged"}


def test_evidence_drift_without_service_token_returns_403(world):
    client, _ = world
    response = client.post(
        "/api/alerts/evidence_drift",
        json={
            "field": "capf_suicide_per_year",
            "old_value": 130.0,
            "new_value": 140.0,
            "source_url": "https://example.test/paper",
            "snippet": "synthetic",
            "run_id": "run-1",
        },
    )
    assert response.status_code == 403


@pytest.mark.parametrize("outcome", ["PASS", "FAIL", "INCONCLUSIVE"])
def test_trust_test_outcomes_are_accepted(world, outcome):
    client, _ = world
    response = client.post(
        "/api/audit/trust_test",
        headers=svc(),
        json={
            "role": "commander",
            "action": "open_individual_case",
            "outcome": outcome,
            "timestamp": "2026-10-17T21:00:00Z",
            "run_id": "run-2",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"status": "logged"}


def test_trust_test_with_invalid_outcome_returns_422(world):
    client, _ = world
    response = client.post(
        "/api/audit/trust_test",
        headers=svc(),
        json={
            "role": "commander",
            "action": "open_individual_case",
            "outcome": "MAYBE",
            "timestamp": "2026-10-17T21:00:00Z",
            "run_id": "run-2",
        },
    )
    assert response.status_code == 422


def test_trust_failure_alert_writes_to_audit_ledger(world):
    client, _ = world
    response = client.post(
        "/api/alerts/trust_failure",
        headers=svc(),
        json={"text": "RBAC fail on commander/open_individual_case"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "alerted"}
    audit = client.get("/api/audit", headers=au()).json()
    actions = [e["action"] for e in audit["entries"]]
    assert "tinyfish.trust_failure_alert" in actions


def test_get_directory_without_auth_returns_401(world):
    client, _ = world
    assert client.get("/api/welfare/directory").status_code == 401


def test_hrms_ingest_accepts_a_full_batch(world):
    client, _ = world
    records = [
        {
            "pid_hash": _pid("SYNTHETIC_001"),
            "duty_days_consecutive": 31,
            "leave_balance_days": 7,
            "last_posting_change_date": "2026-08-15",
            "unit_code": "U01",
        }
    ]
    response = client.post(
        "/api/ingest/hrms",
        headers={**svc(), "X-TinyFish-Run-Id": "run-hrms"},
        json=records,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_hrms_ingest_rejects_a_partial_invalid_batch(world):
    client, _ = world
    records = [
        {
            "pid_hash": _pid("SYNTHETIC_001"),
            "duty_days_consecutive": 31,
            "leave_balance_days": 7,
            "last_posting_change_date": "2026-08-15",
            "unit_code": "U01",
        },
        {"pid_hash": "not-a-hash", "duty_days_consecutive": 1, "leave_balance_days": 0, "unit_code": "U02"},
    ]
    response = client.post("/api/ingest/hrms", headers=svc(), json=records)
    assert response.status_code == 422
    assert tinyfish_routes._hrms_records == []


def test_evidence_baseline_is_auditor_readable(world):
    client, _ = world
    body = client.get("/api/tinyfish/evidence-baseline", headers=au()).json()
    assert body["capf_suicide_per_year"] == 130
    audit = client.get("/api/audit", headers=au()).json()
    assert any(e["action"] == "tinyfish.evidence_baseline_viewed" for e in audit["entries"])


def test_latest_trust_tests_parse_the_markdown_table(world):
    client, _ = world
    body = client.get("/api/tinyfish/trust-tests/latest", headers=au()).json()
    assert body["date"] == "2026-10-17"
    assert body["overall"] == "FAIL"
    assert {r["outcome"] for r in body["results"]} == {"PASS", "FAIL"}
