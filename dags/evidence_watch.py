"""
Airflow DAG: evidence_watch
Schedule: Weekly on Monday at 06:00 IST (00:30 UTC Monday)
Runs scripts/evidence_watch.py (TinyFish search query + fetch content get).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from airflow import DAG
from airflow.operators.python import PythonOperator

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "scripts"))

SCRIPTS_DIR = ROOT / "scripts"
SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")


def run_evidence_watch(**context):
    import logging
    import subprocess

    log = logging.getLogger(__name__)
    script = SCRIPTS_DIR / "evidence_watch.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=600,
        env={**os.environ,
             "SAMVEDNA_API_BASE": SAMVEDNA_API_BASE,
             "SAMVEDNA_SERVICE_TOKEN": SAMVEDNA_SERVICE_TOKEN},
    )
    log.info(result.stdout)
    if result.returncode != 0:
        log.error(result.stderr)
        raise RuntimeError("evidence_watch.py failed")


default_args = {"owner": "samvedna", "retries": 1, "retry_delay": timedelta(hours=1)}

with DAG(
    dag_id="evidence_watch",
    description="Weekly TinyFish policy & evidence watch for SAMVEDNA",
    schedule="30 0 * * 1",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args=default_args,
    tags=["samvedna", "tinyfish", "evidence"],
) as dag:
    PythonOperator(task_id="run_evidence_watch", python_callable=run_evidence_watch)
