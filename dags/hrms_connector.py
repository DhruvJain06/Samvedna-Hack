"""
Airflow DAG: hrms_connector
Schedule: Nightly at 01:00 IST (19:30 UTC previous day)

Calls the TinyFish HRMS web agent, validates the returned JSON,
and POSTs clean records to the SAMVEDNA ingest endpoint.

All credentials come from TinyFish Vault (never from this file).
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

AGENT_YAML = os.path.join(os.path.dirname(__file__), "..", "agents", "hrms_connector.yaml")
SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")
TARGET_PORTAL_URL = os.getenv("TARGET_PORTAL_URL", "")
UNIT_CODES = os.getenv("UNIT_CODES", "U01")
MAX_RECORDS_PER_MINUTE = 2000  # throughput guard


def run_tinyfish_agent(**context) -> dict:
    """Invoke the TinyFish HRMS agent and return the JSON result."""
    if not TARGET_PORTAL_URL:
        raise ValueError("TARGET_PORTAL_URL env var is not set")

    cmd = [
        "npx", "-y", "@tiny-fish/cli@latest", "agent", "run",
        AGENT_YAML,
        "--var", f"TARGET_PORTAL_URL={TARGET_PORTAL_URL}",
        "--var", f"UNIT_CODES={UNIT_CODES}",
    ]
    log.info("Running TinyFish HRMS agent for units: %s", UNIT_CODES)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        log.error("TinyFish agent failed: %s", result.stderr)
        raise RuntimeError(f"TinyFish agent exited with code {result.returncode}")

    # Parse JSONL output; pick the COMPLETE line
    run_id = None
    records = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
            if event.get("type") == "COMPLETE":
                records = event["result"]["result"]
                run_id = event["run_id"]
        except json.JSONDecodeError:
            pass

    log.info("Agent completed run_id=%s, records=%d", run_id, len(records))
    context["task_instance"].xcom_push(key="run_id", value=run_id)
    context["task_instance"].xcom_push(key="records", value=records)
    return {"run_id": run_id, "record_count": len(records)}


def validate_and_ingest(**context) -> None:
    """Validate the schema and POST to /api/ingest/hrms."""
    import hashlib, re, requests  # noqa: PLC0415

    ti = context["task_instance"]
    records = ti.xcom_pull(key="records", task_ids="run_tinyfish_agent")
    run_id = ti.xcom_pull(key="run_id", task_ids="run_tinyfish_agent")

    if not records:
        raise ValueError("No records returned from TinyFish agent — skipping ingest")

    # Schema validation
    pid_re = re.compile(r"^[a-f0-9]{64}$")
    for i, r in enumerate(records):
        assert pid_re.match(r.get("pid_hash", "")), f"Bad pid_hash at index {i}"
        assert isinstance(r.get("duty_days_consecutive"), int), f"Bad duty_days at {i}"
        assert isinstance(r.get("leave_balance_days"), int), f"Bad leave_balance at {i}"
        assert isinstance(r.get("unit_code"), str), f"Bad unit_code at {i}"

    log.info("Schema valid for %d records — posting to ingest endpoint", len(records))

    resp = requests.post(
        f"{SAMVEDNA_API_BASE}/api/ingest/hrms",
        json=records,
        headers={
            "Authorization": f"Bearer {SAMVEDNA_SERVICE_TOKEN}",
            "X-TinyFish-Run-Id": run_id or "",
        },
        timeout=300,
    )
    resp.raise_for_status()
    log.info("Ingest accepted: %s", resp.json())


def log_run_to_audit(**context) -> None:
    """Write the TinyFish run_id to the SAMVEDNA audit ledger."""
    import requests  # noqa: PLC0415

    ti = context["task_instance"]
    run_id = ti.xcom_pull(key="run_id", task_ids="run_tinyfish_agent")

    requests.post(
        f"{SAMVEDNA_API_BASE}/api/audit/trust_test",
        json={
            "role": "system",
            "action": "hrms_connector_run",
            "outcome": "PASS",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_id": run_id,
        },
        headers={"Authorization": f"Bearer {SAMVEDNA_SERVICE_TOKEN}"},
        timeout=30,
    )


default_args = {
    "owner": "samvedna",
    "retries": 0,          # on failure, alert but do not retry with partial data
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="hrms_connector",
    description="Nightly TinyFish HRMS web-agent ingest for SAMVEDNA",
    schedule="30 19 * * *",   # 01:00 IST = 19:30 UTC
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args=default_args,
    tags=["samvedna", "tinyfish", "ingest"],
) as dag:

    t1 = PythonOperator(
        task_id="run_tinyfish_agent",
        python_callable=run_tinyfish_agent,
    )

    t2 = PythonOperator(
        task_id="validate_and_ingest",
        python_callable=validate_and_ingest,
    )

    t3 = PythonOperator(
        task_id="log_run_to_audit",
        python_callable=log_run_to_audit,
    )

    t1 >> t2 >> t3
