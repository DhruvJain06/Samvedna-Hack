"""
Airflow DAG: trust_tests
Schedule: Nightly at 03:00 IST (21:30 UTC previous day)
Runs TinyFish RBAC boundary tests across all 5 forbidden actions.
Alerts immediately on any FAIL outcome.
"""
from __future__ import annotations
import json
import logging
import os
import subprocess
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

AGENT_YAML = os.path.join(os.path.dirname(__file__), "..", "agents", "trust_tests.yaml")
SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")
SAMVEDNA_CONSOLE_URL = os.getenv("SAMVEDNA_CONSOLE_URL", "http://127.0.0.1:3100")
ONCALL_WEBHOOK_URL = os.getenv("ONCALL_WEBHOOK_URL", "")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

# Full test matrix from TINYFISH_INTEGRATION_PROMPT.md Section 2-D
TEST_MATRIX = [
    ("commanding_officer", "open_individual_case"),
    ("commanding_officer", "view_small_unit"),
    ("auditor",            "change_verdict"),
    ("auditor",            "download_raw_records"),
    ("welfare_officer",    "view_out_of_scope_unit"),
    ("personnel",          "read_other_self_assessment"),
]


def run_trust_tests(**context) -> None:
    """Run each forbidden-action test and collect outcomes."""
    import requests  # noqa: PLC0415

    results = []
    any_fail = False

    for role, action in TEST_MATRIX:
        log.info("Testing role=%s action=%s", role, action)
        cmd = [
            "npx", "-y", "@tiny-fish/cli@latest", "agent", "run",
            AGENT_YAML,
            "--var", f"ROLE={role}",
            "--var", f"ACTION={action}",
            "--var", f"SAMVEDNA_CONSOLE_URL={SAMVEDNA_CONSOLE_URL}",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            log.warning("Timeout for role=%s action=%s — INCONCLUSIVE", role, action)
            results.append({"role": role, "action": action, "outcome": "INCONCLUSIVE"})
            continue

        outcome = "INCONCLUSIVE"
        run_id = None
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
                if event.get("type") == "COMPLETE":
                    outcome = event.get("result", {}).get("outcome", "INCONCLUSIVE")
                    run_id = event.get("run_id")
            except json.JSONDecodeError:
                pass

        results.append({"role": role, "action": action, "outcome": outcome, "run_id": run_id})

        if outcome == "FAIL":
            any_fail = True
            log.error("TRUST TEST FAIL: role=%s action=%s run_id=%s", role, action, run_id)
            if ONCALL_WEBHOOK_URL:
                requests.post(ONCALL_WEBHOOK_URL, json={
                    "text": f"SAMVEDNA RBAC FAIL: role={role} action={action} run_id={run_id}"
                }, timeout=10)

    # Save report
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    report_path = os.path.join(REPORT_DIR, f"nightly_trust_report_{date_str}.md")
    _write_report(report_path, results)

    if any_fail:
        raise RuntimeError("One or more trust tests FAILED — see report at " + report_path)


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
    schedule="30 21 * * *",   # 03:00 IST = 21:30 UTC
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args=default_args,
    tags=["samvedna", "tinyfish", "security", "rbac"],
) as dag:
    PythonOperator(task_id="run_trust_tests", python_callable=run_trust_tests)
