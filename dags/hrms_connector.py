"""
Airflow DAG: hrms_connector
Schedule: Nightly at 01:00 IST (19:30 UTC previous day)

Calls TinyFish CLI 0.49: agent run "<goal>" --url --sync --use-vault.
agents/hrms_connector.yaml is the human spec, not executed as a DSL.
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
    extract_records,
    parse_cli_json,
    run_tinyfish,
)
from tinyfish_goals import hrms_goal  # noqa: E402

log = logging.getLogger(__name__)

SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")
TARGET_PORTAL_URL = os.getenv("TARGET_PORTAL_URL", "")
UNIT_CODES = os.getenv("UNIT_CODES", "U01")
SCHEMA_FILE = ROOT / "config" / "hrms_records.schema.json"


def run_tinyfish_agent(**context) -> dict:
    """Invoke TinyFish HRMS agent (natural-language goal) and return JSON."""
    if not TARGET_PORTAL_URL:
        raise ValueError("TARGET_PORTAL_URL env var is not set")

    goal = hrms_goal(UNIT_CODES)
    cmd = agent_run_cmd(
        goal,
        TARGET_PORTAL_URL,
        use_vault=True,
        output_schema_file=SCHEMA_FILE,
    )
    log.info("Running TinyFish HRMS agent for units: %s", UNIT_CODES)
    result = run_tinyfish(cmd, timeout=600)

    if result.returncode != 0:
        log.error("TinyFish agent failed: %s", result.stderr)
        raise RuntimeError(f"TinyFish agent exited with code {result.returncode}")

    payload = parse_cli_json(result.stdout)
    inner, run_id = extract_agent_payload(payload)
    records = extract_records(inner)

    log.info("Agent completed run_id=%s, records=%d", run_id, len(records))
    context["task_instance"].xcom_push(key="run_id", value=run_id)
    context["task_instance"].xcom_push(key="records", value=records)
    return {"run_id": run_id, "record_count": len(records)}


def validate_and_ingest(**context) -> None:
    """Validate the schema and POST to /api/ingest/hrms."""
    import re
    import requests  # noqa: PLC0415

    ti = context["task_instance"]
    records = ti.xcom_pull(key="records", task_ids="run_tinyfish_agent")
    run_id = ti.xcom_pull(key="run_id", task_ids="run_tinyfish_agent")

    if not records:
        raise ValueError("No records returned from TinyFish agent — skipping ingest")

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
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

with DAG(
    dag_id="hrms_connector",
    description="Nightly TinyFish HRMS web-agent ingest for SAMVEDNA",
    schedule="30 19 * * *",
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
