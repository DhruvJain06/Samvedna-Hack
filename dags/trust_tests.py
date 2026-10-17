"""
Airflow DAG: trust_tests
Schedule: Nightly at 03:00 IST (21:30 UTC previous day)

Runs TinyFish CLI 0.49 agent run "<goal>" --url --sync --use-vault
for each forbidden action. agents/trust_tests.yaml is the human spec.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "scripts"))

from airflow import DAG
from airflow.operators.python import PythonOperator

from tinyfish_cli import (  # noqa: E402
    agent_run_cmd,
    extract_agent_payload,
    extract_outcome,
    parse_cli_json,
    run_tinyfish,
)
from tinyfish_goals import TRUST_GOALS  # noqa: E402

log = logging.getLogger(__name__)

SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")
SAMVEDNA_CONSOLE_URL = os.getenv("SAMVEDNA_CONSOLE_URL", "http://127.0.0.1:3100")
ONCALL_WEBHOOK_URL = os.getenv("ONCALL_WEBHOOK_URL", "")
REPORT_DIR = ROOT / "reports"
SCHEMA_FILE = ROOT / "config" / "trust_test_result.schema.json"

TEST_MATRIX = [
    ("commanding_officer", "open_individual_case"),
    ("commanding_officer", "view_small_unit"),
    ("auditor", "change_verdict"),
    ("auditor", "download_raw_records"),
    ("welfare_officer", "view_out_of_scope_unit"),
    ("personnel", "read_other_self_assessment"),
]


def run_trust_tests(**context) -> None:
    import requests  # noqa: PLC0415

    results = []
    any_fail = False

    for role, action in TEST_MATRIX:
        log.info("Testing role=%s action=%s", role, action)
        path, goal = TRUST_GOALS[(role, action)]
        start_url = SAMVEDNA_CONSOLE_URL.rstrip("/") + path
        cmd = agent_run_cmd(
            goal,
            start_url,
            use_vault=True,
            output_schema_file=SCHEMA_FILE,
        )
        try:
            completed = run_tinyfish(cmd, timeout=60)
        except Exception:
            log.warning("Timeout/error for role=%s action=%s — INCONCLUSIVE", role, action)
            results.append({"role": role, "action": action, "outcome": "INCONCLUSIVE"})
            continue

        outcome = "INCONCLUSIVE"
        run_id = None
        payload = parse_cli_json(completed.stdout)
        inner, run_id = extract_agent_payload(payload)
        outcome = extract_outcome(inner)

        results.append({"role": role, "action": action, "outcome": outcome, "run_id": run_id})

        if outcome == "FAIL":
            any_fail = True
            log.error("TRUST TEST FAIL: role=%s action=%s run_id=%s", role, action, run_id)
            if ONCALL_WEBHOOK_URL:
                requests.post(ONCALL_WEBHOOK_URL, json={
                    "text": f"SAMVEDNA RBAC FAIL: role={role} action={action} run_id={run_id}"
                }, timeout=10)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"nightly_trust_report_{date_str}.md"
    _write_report(str(report_path), results)

    if any_fail:
        raise RuntimeError("One or more trust tests FAILED — see report at " + str(report_path))


def _write_report(path: str, results: list) -> None:
    lines = [
        f"# Nightly Trust Test Report — {datetime.utcnow().strftime('%Y-%m-%d')}",
        "",
        "| Role | Action | Outcome |",
        "|------|--------|---------|",
    ]
    for r in results:
        icon = {"PASS": "✓", "FAIL": "✗", "INCONCLUSIVE": "?"}.get(r["outcome"], "?")
        lines.append(f"| {r['role']} | {r['action']} | {icon} {r['outcome']} |")
    lines += ["", f"Generated at {datetime.utcnow().isoformat()}Z"]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log.info("Trust test report written to %s", path)


default_args = {
    "owner": "samvedna",
    "retries": 0,
    "email_on_failure": False,
}

with DAG(
    dag_id="trust_tests",
    description="Nightly TinyFish RBAC boundary tests for SAMVEDNA",
    schedule="30 21 * * *",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args=default_args,
    tags=["samvedna", "tinyfish", "security", "rbac"],
) as dag:
    PythonOperator(task_id="run_trust_tests", python_callable=run_trust_tests)
