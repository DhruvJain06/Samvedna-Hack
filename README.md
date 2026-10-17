# SAMVEDNA x TinyFish Integration

Separate project for integrating TinyFish API into the SAMVEDNA mental-health
welfare screening system (Team CodeZila / SIH 2026).

> **This project does NOT modify the main SAMVEDNA codebase.**
> It lives at D:\samvedna-tinyfish and is deployed alongside it.

## What is SAMVEDNA?

SAMVEDNA is a privacy-first AI system for India's CAPF forces that detects
mental-health risk early, using a 4-gate evidence engine that only names a
person when the evidence earns it.

## What does TinyFish add?

| Use case | TinyFish feature | Cadence |
|---|---|---|
| Legacy HRMS connector | Web Agent + Vault | Nightly 01:00 IST |
| Live welfare directory | Fetch monitor | Daily 02:00 IST |
| Policy & evidence watch | Search + Fetch monitor | Weekly Mon 06:00 IST |
| Nightly RBAC trust tests | Web Agent | Nightly 03:00 IST |

## Quick Start

1. Copy `.env.example` to `.env` (placeholders only). Install deps:
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt

2. TinyFish CLI 0.49 (local `tinyfish` if installed, else npx @tiny-fish/cli):
   tinyfish search query "CAPF welfare"
   tinyfish fetch content get https://www.crpf.gov.in/welfare.htm
   tinyfish agent run "<goal>" --url <url> --sync

3. Store live credentials in TinyFish Vault / a connected password manager.
   Never commit `.env` or put passwords in agent goal strings.

4. Dry-run welfare fetch:
   .venv\Scripts\python scripts/welfare_fetch.py --dry-run

## Project Structure

  TINYFISH_INTEGRATION_PROMPT.md  — agent-ready prompt library (main file)
  README.md                       — this file
  .env.example                    — required env vars (no real secrets)
  agents/                         — TinyFish agent and monitor configs
  dags/                           — Airflow DAG definitions
  scripts/                        — Python orchestration scripts
  config/                         — evidence baselines and other config
  data/                           — auto-updated welfare directory and cache
  reports/                        — nightly trust-test report template
  tests/                          — unit tests for schema validators

## Data Boundary (Important)

  agents/hrms_connector.yaml     handles PERSONAL records
  -> must run inside force network or on de-identified exports
  -> pilot uses synthetic CRPF data only

  agents/welfare_fetch.yaml      PUBLIC data only
  agents/evidence_watch.yaml     PUBLIC data only
  agents/trust_tests.yaml        SYNTHETIC / DEMO data only

## Contact

Team CodeZila — HackIIITD Esya 26 / SIH 2026
