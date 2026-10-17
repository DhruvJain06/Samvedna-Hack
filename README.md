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

1. Install TinyFish CLI (already done if you ran connect --all):
   npx -y @tiny-fish/cli@latest --version

2. Set vault secrets (Section 6 of TINYFISH_INTEGRATION_PROMPT.md):
   tinyfish vault set TINYFISH_VAULT_HRMS_USER "..."

3. Run connectivity check:
   tinyfish fetch https://www.crpf.gov.in/welfare.htm

4. Follow the 7-step sequence in TINYFISH_INTEGRATION_PROMPT.md Section 7.

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
