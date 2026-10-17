# SAMVEDNA x TinyFish — Integration Prompt File

**Team:** CodeZila
**Project:** SAMVEDNA — AI-powered welfare screening for India's uniformed forces
**This file:** A complete, agent-ready prompt/context document. Copy any section
below into a TinyFish agent, Cursor, or any AI-assisted session to execute that
integration task without re-explaining the project.

---

## 1. Project Context (always paste this preamble)

You are working on SAMVEDNA, a privacy-first mental-health early-warning
system for India's Central Armed Police Forces (CAPF). It is built by Team CodeZila.

Architecture recap:
- Backend  : Python 3.12 + FastAPI + Apache Airflow (on-prem Kubernetes)
- Frontend : React + TypeScript (welfare / commander / auditor / personnel consoles)
- Mobile   : Flutter (personnel self-assessment app, 8 Indian languages)
- Privacy  : Pseudonymisation at ingest, AES-256 + HSM, differential privacy (Opacus),
             k-anonymity (k >= 5), DPDP 2023-compliant
- DB       : PostgreSQL + TimescaleDB (feature store), Redis (job queue)
- Auth     : Keycloak RBAC; four roles — welfare officer, commanding officer,
             auditor, personnel
- Audit    : Immutable hash-chained ledger; every verdict AND every refusal logged
- ML       : XGBoost / LightGBM + Temporal Transformer + SHAP explanations
- Gate engine: 4 deterministic gates — evidence, consistency, persistence,
             actionability. All four must clear before a name is disclosed.

TinyFish role in SAMVEDNA (from the pitch deck, Slide 7):
  1. Legacy HRMS connector — web agent signs in with vaulted credentials,
     opens roster / leave / posting pages on web-only force portals,
     returns clean JSON to the ingest pipeline.
  2. Live welfare directory — fetch keeps counselling centres, helplines,
     welfare schemes and leave/posting circulars current.
  3. Policy and evidence watch — search+fetch monitors PRS, MHA and research
     sources so gate thresholds are reviewed against the latest evidence.
  4. Nightly trust tests — a web agent logs into each role console and tries
     forbidden actions; every attempt must be refused and logged.

Data boundary rule (critical):
  The HRMS connector handles personal records and MUST run inside the force
  network or on de-identified exports. The three other use-cases touch only
  public or synthetic data. The pilot uses synthetic CRPF data only.

---

## 2. Use-Case 2-A: Legacy HRMS Connector (TinyFish WEB AGENT + VAULT)

Goal: replace manual CSV exports from web-only force portals with an
automated TinyFish web-agent pipeline.

Many CAPF force portals are web-only and have no REST API. We need a
nightly Airflow task that:

1. Uses a TinyFish web agent to sign in to the target portal using credentials
   stored in TinyFish Vault (NEVER in code or config files).
2. Navigates to roster, leave-balance, and posting/transfer pages for each unit.
3. Scrapes and returns clean JSON per record:
   - pid_hash: SHA-256 of the personnel ID, computed locally before sending
   - duty_days_consecutive: integer
   - leave_balance_days: integer
   - last_posting_change_date: ISO-8601 date
   - unit_code: string
4. POSTs the JSON to: POST /api/ingest/hrms  (auth: SAMVEDNA_SERVICE_TOKEN)
5. Runs inside the force network only.

Deliverables:
- agents/hrms_connector.yaml    — TinyFish agent definition
- dags/hrms_connector.py        — Airflow DAG (nightly, 01:00 IST)
- tests/test_hrms_schema.py     — unit tests for schema validation

Constraints:
- Ingest < 5 min for 10,000 records.
- On agent failure, raise Airflow alert and skip; never write partial data.
- Log TinyFish run_id to the SAMVEDNA audit ledger.
- Never log or print vault credentials.

---

## 3. Use-Case 2-B: Live Welfare Directory (TinyFish FETCH)

Goal: keep counselling centres, helplines, and welfare schemes current.

1. Daily TinyFish fetch monitor polling:
   - https://www.crpf.gov.in/welfare.htm
   - https://pib.gov.in/  (filter: CAPF, welfare, counselling, helpline)
   - https://www.mha.gov.in/  (filter: CAPF welfare circulars)
2. Parse HTML and extract:
   - scheme_name, type (helpline|centre|circular|scheme),
     contact, effective_date, url
3. Diff against data/welfare_directory.json; write additions/changes/removals.
4. Append changes to data/welfare_directory_changelog.jsonl.
5. POST /api/welfare/directory/refresh so consoles reload.

Deliverables:
- agents/welfare_fetch.yaml       — TinyFish fetch monitor config
- scripts/welfare_fetch.py        — orchestration script (supports --dry-run)
- dags/welfare_directory.py       — Airflow DAG (daily, 02:00 IST)

Constraints:
- Public data only. Deduplicate by (url + effective_date).
- On unreachable source: keep last-known data, log WARNING to audit ledger.

---

## 4. Use-Case 2-C: Policy and Evidence Watch (TinyFish SEARCH + FETCH)

Goal: alert the team when MHA/PRS statistics or research baselines change.

1. Weekly TinyFish search+fetch monitor (Monday 06:00 IST).
   Queries:
   - "CAPF suicide report MHA site:pib.gov.in OR site:mha.gov.in"
   - "CAPF suicide 2023 OR 2024 OR 2025 report"
   - "burnout prediction AUROC armed forces"
2. Fetch full text of documents newer than config/evidence_baseline.json last_checked.
3. Extract numeric claims and compare against baselines:
   - capf_suicide_per_year: 130
   - capf_suicide_5yr: 654
   - burnout_specificity: 0.84
   - target_auroc: 0.72
4. If any extracted value differs by > 5%: POST /api/alerts/evidence_drift

Deliverables:
- agents/evidence_watch.yaml      — TinyFish monitor config
- scripts/evidence_watch.py       — extraction + comparison (supports --since)
- dags/evidence_watch.py          — Airflow DAG (weekly)
- config/evidence_baseline.json   — seed values above
- FastAPI stub: POST /api/alerts/evidence_drift

Constraints:
- Public sources only (PRS, PIB, PubMed, arXiv, MHA).
- Cache full text in data/evidence_cache/ (plain text, max 1 MB each).
- Do NOT auto-update thresholds — alert is advisory only.

---

## 5. Use-Case 2-D: Nightly Trust Tests (TinyFish WEB AGENT)

Goal: automatically verify every RBAC boundary is enforced nightly.

Test Matrix (attempt each forbidden action, assert it is blocked):

  commanding_officer  | Open any individual case record or gate score
  commanding_officer  | See any unit with fewer than 5 people (k-anonymity)
  auditor             | Change a verdict or download raw records
  welfare_officer     | View cases from a unit outside their scope
  personnel           | Read any other person's self-assessment

For each test:
1. Agent signs into SAMVEDNA console using seeded demo account (from Vault).
2. Attempts the forbidden action via UI or direct API call.
3. Asserts response is HTTP 403 or UI shows "Access denied".
4. Writes result: POST /api/audit/trust_test
5. On FAIL: POST /api/alerts/trust_failure (page on-call immediately).

Deliverables:
- agents/trust_tests.yaml         — parametric TinyFish agent
- dags/trust_tests.py             — Airflow DAG (nightly, 03:00 IST)
- FastAPI routes: POST /api/audit/trust_test and POST /api/alerts/trust_failure
- reports/nightly_trust_report.md — template the DAG fills and saves

Constraints:
- Never run against production unless SAMVEDNA_TRUST_TEST_ENV=production is set.
- Credentials in TinyFish Vault only.
- Timeout per test: 30 s. Abort and mark INCONCLUSIVE if exceeded.

---

## 6. Environment and Secrets Reference

TinyFish Vault keys to set (never hard-code):
  TINYFISH_VAULT_HRMS_USER     — HRMS portal username
  TINYFISH_VAULT_HRMS_PASS     — HRMS portal password
  SAMVEDNA_SERVICE_TOKEN       — internal API token
  SAMVEDNA_CONSOLE_URL         — base URL of SAMVEDNA console
  SAMVEDNA_DEMO_WO_PASS        — demo welfare officer password
  SAMVEDNA_DEMO_CO_PASS        — demo commanding officer password
  SAMVEDNA_DEMO_AU_PASS        — demo auditor password
  SAMVEDNA_DEMO_PERS_PASS      — demo personnel password
  ONCALL_WEBHOOK_URL           — on-call webhook for trust-test failures

To set a vault key:
  tinyfish vault set TINYFISH_VAULT_HRMS_USER "your-username"

---

## 7. Integration Sequence (run in this order)

Step 1 — Vault setup
  tinyfish vault set TINYFISH_VAULT_HRMS_USER "<username>"
  tinyfish vault set TINYFISH_VAULT_HRMS_PASS "<password>"
  tinyfish vault set SAMVEDNA_SERVICE_TOKEN   "<token>"
  tinyfish vault set SAMVEDNA_CONSOLE_URL     "http://127.0.0.1:3100"

Step 2 — Connectivity check
  tinyfish fetch https://www.crpf.gov.in/welfare.htm

Step 3 — HRMS Connector (synthetic data)
  tinyfish agent run --url <TARGET_PORTAL_URL> \
    "Sign in with vaulted HRMS credentials and return roster JSON for unit U01"

Step 4 — Welfare Directory
  python scripts/welfare_fetch.py --dry-run
  python scripts/welfare_fetch.py

Step 5 — Evidence Watch
  python scripts/evidence_watch.py --since 2024-01-01

Step 6 — Trust Tests
  tinyfish agent run agents/trust_tests.yaml \
    --var ROLE=commanding_officer \
    --var ACTION=open_individual_case

Step 7 — Register Airflow DAGs
  cp dags/*.py <AIRFLOW_DAGS_DIR>/
  airflow dags trigger hrms_connector
  airflow dags trigger welfare_directory
  airflow dags trigger evidence_watch
  airflow dags trigger trust_tests

---

## 8. Privacy and Compliance Checklist

Before any live (non-synthetic) run, confirm:
- [ ] HRMS connector runs inside the force network or on de-identified exports.
- [ ] No real name or unmasked PID is sent to TinyFish cloud API.
- [ ] TinyFish Vault credentials are rotated after each pilot phase.
- [ ] All TinyFish run_id values are written to the SAMVEDNA audit ledger.
- [ ] Welfare fetch and evidence watch touch only public URLs.
- [ ] Trust-test accounts use seeded demo credentials (never production accounts).
- [ ] DPDP 2023 Data Processing Agreements signed before pilot data is used.
- [ ] k-anonymity (k >= 5) enforced before any unit aggregate is shown.

---

## 9. TinyFish CLI Quick Reference

  tinyfish vault set <KEY> "<VALUE>"
  tinyfish vault list
  tinyfish fetch <URL>
  tinyfish agent run --url <URL> "<task>"
  tinyfish agent run <agent.yaml> --var KEY=VALUE
  tinyfish search "<query>" --fetch
  tinyfish monitor create --config <monitor.yaml>
  tinyfish monitor list
  tinyfish monitor run <monitor-id>
  tinyfish doctor --pretty

---
Document maintained by Team CodeZila.
Source of truth for TinyFish integration: pitch deck Slide 7.
Update Section 6 vault table after each key rotation.
