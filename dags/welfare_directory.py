"""
Airflow DAG: welfare_directory
Schedule: Daily at 02:00 IST (20:30 UTC previous day)
Runs the TinyFish welfare fetch monitor via scripts/welfare_fetch.py.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
SAMVEDNA_API_BASE = os.getenv("SAMVEDNA_API_BASE", "http://127.0.0.1:8090")
SAMVEDNA_SERVICE_TOKEN = os.getenv("SAMVEDNA_SERVICE_TOKEN", "")


def run_welfare_fetch(**context):
    import subprocess, logging
    log = logging.getLogger(__name__)
    script = os.path.join(SCRIPTS_DIR, "welfare_fetch.py")
    result = subprocess.run(
        ["python", script],
        capture_output=True, text=True, timeout=300,
        env={**os.environ,
             "SAMVEDNA_API_BASE": SAMVEDNA_API_BASE,
             "SAMVEDNA_SERVICE_TOKEN": SAMVEDNA_SERVICE_TOKEN}
    )
    log.info(result.stdout)
    if result.returncode != 0:
        log.error(result.stderr)
        raise RuntimeError("welfare_fetch.py failed")


default_args = {"owner": "samvedna", "retries": 1, "retry_delay": timedelta(minutes=10)}

with DAG(
    dag_id="welfare_directory",
    description="Daily TinyFish welfare directory fetch for SAMVEDNA",
    schedule="30 20 * * *",
    start_date=datetime(2026, 10, 1),
    catchup=False,
    default_args=default_args,
    tags=["samvedna", "tinyfish", "welfare"],
) as dag:
    PythonOperator(task_id="run_welfare_fetch", python_callable=run_welfare_fetch)
