# SAMVEDNA × TINYFISH  
# MASTER END-TO-END AGENT PROMPT  
# Paste the entire content of this file into your AI agent (Cursor / Antigravity / Claude / GPT).  
# The agent will build and wire the complete integrated system from scratch.

---

## WHO YOU ARE

You are a senior full-stack engineer working for Team CodeZila on **SAMVEDNA** —
a privacy-first mental-health early-warning system for India's Central Armed
Police Forces (CAPF). You have full autonomy to create files, run commands, and
edit code. Do not stop until every numbered task below is DONE and verified.

---

## WHAT ALREADY EXISTS (do not modify these)

### Main SAMVEDNA project (read-only reference)
Location: `D:\Samvedna SIH with Truevoice\samvedna\samvedna`

| Layer | Tech | Port |
|---|---|---|
| Backend API | Python 3.12, FastAPI, Apache Airflow | 8090 |
| Frontend console | Next.js 15 / React 19 / TypeScript | 3100 |
| Mobile app | Flutter | — |
| DB | PostgreSQL + TimescaleDB + Redis | — |
| Auth | Keycloak RBAC + scrypt sessions | — |
| Audit | Immutable hash-chained ledger | — |
| ML | XGBoost/LightGBM + SHAP + Temporal Transformer | — |

Existing demo accounts: `wo12` (welfare officer), `co01` (commanding officer),
`personnel` (personnel), `au03` (auditor), `mha1` (mental-health authority).
Run with: `cd "D:\Samvedna SIH with Truevoice\samvedna\samvedna" && .\run.ps1`

### TinyFish integration skeleton (your working directory)
Location: `D:\samvedna-tinyfish`

Files already written (DO NOT recreate, just edit if needed):
  agents/hrms_connector.yaml     — TinyFish HRMS web-agent definition
  agents/welfare_fetch.yaml      — TinyFish welfare fetch monitor
  agents/evidence_watch.yaml     — TinyFish evidence search+fetch monitor
  agents/trust_tests.yaml        — TinyFish RBAC trust-test agent
  dags/hrms_connector.py         — Airflow DAG (nightly HRMS ingest)
  dags/welfare_directory.py      — Airflow DAG (daily welfare fetch)
  dags/evidence_watch.py         — Airflow DAG (weekly evidence watch)
  dags/trust_tests.py            — Airflow DAG (nightly RBAC tests)
  scripts/welfare_fetch.py       — welfare fetch orchestration
  scripts/evidence_watch.py      — evidence watch orchestration
  config/evidence_baseline.json  — baseline numbers (seeded from pitch deck)
  data/welfare_directory.json    — seed welfare directory
  reports/nightly_trust_report.md — trust report template
  tests/test_hrms_schema.py      — HRMS schema unit tests
  TINYFISH_INTEGRATION_PROMPT.md — detailed prompt library per use-case
  README.md                      — project overview
  .env.example                   — env var reference

TinyFish CLI is already installed and connected to Cursor.
TinyFish API key is already configured in the system via `tinyfish vault`.

---

## FOUR USE-CASES TO IMPLEMENT (from pitch deck Slide 7)

```
1. Legacy HRMS connector  — web agent signs in with vaulted credentials,
   opens roster/leave/posting pages on web-only CAPF portals, returns
   clean JSON to the SAMVEDNA ingest endpoint.

2. Live welfare directory — fetch keeps counselling centres, helplines,
   welfare schemes and circulars current (daily).

3. Policy & evidence watch — search+fetch monitors PRS, MHA, PubMed so
   gate thresholds are reviewed against the latest published evidence (weekly).

4. Nightly trust tests — web agent logs into each role console and tries
   forbidden actions; every attempt must be refused and logged.
```

Data boundary (CRITICAL, enforce in every task):
- HRMS connector: personal records → runs inside force network or on
  de-identified exports. Pilot uses synthetic CRPF data ONLY.
- Welfare fetch, evidence watch, trust tests: public or synthetic data ONLY.
- No real name or unmasked PID ever leaves the ingest step.

---

## YOUR TASKS (complete in order, do not skip any)

### TASK 1 — Environment setup in D:\samvedna-tinyfish

1a. Create `requirements.txt` with these exact dependencies:
    apache-airflow>=2.9.0
    requests>=2.31.0
    pytest>=8.0.0
    python-dotenv>=1.0.0
    jsonschema>=4.22.0

1b. Create a Python virtual environment:
    cd D:\samvedna-tinyfish
    python -m venv .venv

1c. Activate it and install:
    .venv\Scripts\pip install -r requirements.txt

1d. Create `D:\samvedna-tinyfish\pytest.ini`:
    [pytest]
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*

1e. Verify the test suite passes:
    .venv\Scripts\pytest tests/ -v
    All tests in tests/test_hrms_schema.py must pass (there are 16 tests).
    If any fail, fix the code — do not remove tests.

1f. Copy `.env.example` to `.env` and fill in these concrete dev values:
    SAMVEDNA_API_BASE=http://127.0.0.1:8090
    SAMVEDNA_CONSOLE_URL=http://127.0.0.1:3100
    SAMVEDNA_TRUST_TEST_ENV=dev
    TARGET_PORTAL_URL=https://crpf.gov.in   (pilot placeholder)
    UNIT_CODES=U01,U02,U03
    Leave all vault-sourced secrets as placeholder strings.

---

### TASK 2 — New FastAPI routes in the SAMVEDNA backend

Working directory for this task:
`D:\Samvedna SIH with Truevoice\samvedna\samvedna\src\samvedna`

Add the following four new API routes. Follow EXACTLY the same style as
the existing routes in `api/app.py` and `api/voice_routes.py`.
Do NOT break any existing routes. Do NOT change auth logic.

**2a. POST /api/welfare/directory/refresh**
File: `api/tinyfish_routes.py` (create this file)

Purpose: Reload welfare_directory.json from disk so the welfare officer
console shows updated data without a restart.

Logic:
- Requires role: welfare_officer or system (service token)
- Read `D:\samvedna-tinyfish\data\welfare_directory.json` from disk
- Store the parsed list in a module-level variable
  `_welfare_directory: list[dict] = []`
- Return `{"status": "ok", "count": len(items), "refreshed_at": <ISO-8601>}`
- Write to the audit ledger: action=`tinyfish.welfare_directory_refreshed`,
  detail=`{"count": N}`

**2b. GET /api/welfare/directory**
File: same `api/tinyfish_routes.py`

Purpose: Return the current welfare directory to the frontend.
- Requires role: welfare_officer
- Return the `_welfare_directory` list (or reload from disk if empty)
- Response: `{"items": [...], "count": N}`

**2c. POST /api/alerts/evidence_drift**
File: same `api/tinyfish_routes.py`

Request body:
  {"field": str, "old_value": float, "new_value": float,
   "source_url": str, "snippet": str, "run_id": str}

Logic:
- Requires service token auth (same pattern as ingest routes)
- Write to audit ledger: action=`tinyfish.evidence_drift_alert`, detail=body
- Log at WARNING level: "Evidence drift: {field} {old} -> {new} ({source_url})"
- Return `{"status": "logged"}`

**2d. POST /api/audit/trust_test**
File: same `api/tinyfish_routes.py`

Request body:
  {"role": str, "action": str, "outcome": str,
   "timestamp": str, "run_id": str}

Logic:
- Requires service token auth
- Validate: outcome must be one of PASS, FAIL, INCONCLUSIVE
- Write to audit ledger: action=`tinyfish.trust_test`, detail=body
- If outcome == "FAIL", additionally log at ERROR level
- Return `{"status": "logged"}`

**2e. POST /api/alerts/trust_failure**
File: same `api/tinyfish_routes.py`

Request body: `{"text": str}` (webhook-style alert)

Logic:
- Requires service token auth
- Write to audit ledger: action=`tinyfish.trust_failure_alert`, detail=body
- Log at CRITICAL level
- Return `{"status": "alerted"}`

**2f. Wire the router:**
In `api/app.py`, import and include the new router:
  from samvedna.api.tinyfish_routes import tinyfish_router
  app.include_router(tinyfish_router, prefix="/api")

**2g. Tests for new routes:**
Create `tests/test_tinyfish_routes.py` in the SAMVEDNA test folder.
Write at minimum 8 tests covering:
- Refresh returns 200 and correct shape
- GET directory returns items list
- Evidence drift with valid body returns 200
- Evidence drift without service token returns 403
- Trust test PASS/FAIL/INCONCLUSIVE all accepted
- Trust test with invalid outcome returns 422
- Trust failure alert writes to audit ledger
- GET directory without auth returns 401

Run: `uv run pytest tests/test_tinyfish_routes.py -v`
All 8+ tests must pass.

---

### TASK 3 — Welfare Directory: Frontend integration

Working directory: `D:\Samvedna SIH with Truevoice\samvedna\samvedna\web`

**3a. Create `components/WelfareDirectory.tsx`**

A React component that:
- Fetches `GET /api/welfare/directory` on mount (using the existing `authApi`
  client from `lib/api.ts`)
- Shows a loading skeleton while fetching
- Renders a card list: each card shows scheme_name, type badge (colour-coded:
  helpline=blue, centre=green, circular=amber, scheme=purple), contact, and
  a link to the source URL (opens in new tab)
- Shows a friendly "No entries yet" state when empty
- Error state shows: "Could not load welfare directory"
- Follows the existing dark-mode design in globals.css

**3b. Add to the officer console:**
In `web/app/officer/page.tsx`, add a collapsible section at the bottom titled
"Welfare Resources" that renders `<WelfareDirectory />`.
Only visible to role `welfare_officer`.

**3c. Add translations:**
In the i18n locale files for all 8 languages, add:
  welfare_resources: "Welfare Resources"   (English)
  welfare_loading: "Loading welfare directory…"
  welfare_empty: "No welfare resources found."
  welfare_error: "Could not load welfare directory."
For the 7 non-English languages, use a placeholder like:
  [hi] welfare_resources: "कल्याण संसाधन"
  (translate accurately where possible, use English as fallback for others)

**3d. Build check:**
Run: `npm run build` (from the `web/` directory)
Fix any TypeScript errors before moving on.

---

### TASK 4 — Evidence Baseline: admin page

Working directory: `D:\Samvedna SIH with Truevoice\samvedna\samvedna\web`

**4a. Create `web/app/evidence/page.tsx`**

A read-only admin page (visible to role `auditor` and `mha1` only) that:
- Reads `D:\samvedna-tinyfish\config\evidence_baseline.json` via a new
  `GET /api/tinyfish/evidence-baseline` endpoint (add it to tinyfish_routes.py)
- Shows a table: Field | Baseline Value | Source | Last Checked
- Shows a prominent warning banner if `last_checked` is null or > 30 days ago:
  "Evidence baselines have not been verified in over 30 days.
   Run the evidence watch DAG to update."
- No edit functionality (read-only in the UI; changing values requires editing
  the JSON file directly and restarting, by design)

**4b. Wire GET /api/tinyfish/evidence-baseline in the backend:**
- Requires role: auditor or mha1
- Reads `D:\samvedna-tinyfish\config\evidence_baseline.json` from disk
- Returns the parsed JSON
- Write to audit ledger: action=`tinyfish.evidence_baseline_viewed`

**4c. Add to the sidebar navigation:**
In `web/components/Shell.tsx`, add an "Evidence Baselines" nav link under the
Audit section, visible to auditor and mha1 only.

---

### TASK 5 — Trust Test Dashboard

Working directory: `D:\Samvedna SIH with Truevoice\samvedna\samvedna\web`

**5a. Create `GET /api/tinyfish/trust-tests/latest`** in tinyfish_routes.py

Logic:
- Requires role: auditor
- Scans `D:\samvedna-tinyfish\reports\` for files matching
  `nightly_trust_report_*.md`
- Returns metadata of the latest report:
  {"date": "YYYY-MM-DD", "results": [...], "overall": "PASS|FAIL|INCONCLUSIVE"}
- Parse the markdown table rows to extract role, action, outcome
- If no reports exist yet, return `{"date": null, "results": [], "overall": null}`

**5b. Create `web/app/trust/page.tsx`**

A page (auditor only) that:
- Fetches `GET /api/tinyfish/trust-tests/latest`
- Shows a "Last Run: YYYY-MM-DD" header
- Renders a colour-coded table: PASS=green row, FAIL=red row with ⚠ icon,
  INCONCLUSIVE=yellow row
- If overall=FAIL, shows a red banner: "⚠ RBAC boundary violation detected.
  Review immediately."
- Shows "No trust tests have run yet" if no reports exist

**5c. Add to sidebar** under the Audit section, auditor only.

---

### TASK 6 — Airflow DAG wiring: make them runnable locally

Working directory: `D:\samvedna-tinyfish`

**6a. Create `airflow_setup.ps1`** (Windows PowerShell):

```powershell
# Sets up a local Airflow environment for samvedna-tinyfish
# Run once: .\airflow_setup.ps1

$env:AIRFLOW_HOME = "D:\samvedna-tinyfish\airflow"
$env:AIRFLOW__CORE__DAGS_FOLDER = "D:\samvedna-tinyfish\dags"
$env:AIRFLOW__CORE__LOAD_EXAMPLES = "False"
$env:AIRFLOW__DATABASE__SQL_ALCHEMY_CONN = "sqlite:///D:\samvedna-tinyfish\airflow\airflow.db"

New-Item -ItemType Directory -Force -Path "D:\samvedna-tinyfish\airflow"

# Install airflow in the venv
& "D:\samvedna-tinyfish\.venv\Scripts\pip" install apache-airflow>=2.9.0

# Init the DB
& "D:\samvedna-tinyfish\.venv\Scripts\airflow" db init

# Create admin user
& "D:\samvedna-tinyfish\.venv\Scripts\airflow" users create `
    --username admin --password admin --firstname Admin `
    --lastname User --role Admin --email admin@samvedna.local

Write-Host "Airflow ready. Run: airflow standalone"
```

**6b. Create `airflow_env.ps1`** (source before running any airflow command):

```powershell
$env:AIRFLOW_HOME = "D:\samvedna-tinyfish\airflow"
$env:AIRFLOW__CORE__DAGS_FOLDER = "D:\samvedna-tinyfish\dags"
$env:AIRFLOW__CORE__LOAD_EXAMPLES = "False"
$env:AIRFLOW__DATABASE__SQL_ALCHEMY_CONN = "sqlite:///D:\samvedna-tinyfish\airflow\airflow.db"

# Load .env if it exists
if (Test-Path "D:\samvedna-tinyfish\.env") {
    Get-Content "D:\samvedna-tinyfish\.env" | ForEach-Object {
        if ($_ -match "^([^#=]+)=(.*)$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim())
        }
    }
}
Write-Host "Airflow env loaded."
```

**6c. Update all four DAGs** to load env from `.env` at the top of the file
using python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv("D:/samvedna-tinyfish/.env")
```
Add this as the first non-comment import in each DAG file.

**6d. Test DAG syntax:**
For each of the four DAGs, verify they parse without error:
  .venv\Scripts\python -c "import importlib.util; s=importlib.util.spec_from_file_location('m','dags/hrms_connector.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print('OK')"
All four must print OK.

---

### TASK 7 — Welfare fetch script: make it fully runnable

Working directory: `D:\samvedna-tinyfish`

**7a.** Run in dry-run mode and confirm it prints output:
  .venv\Scripts\python scripts/welfare_fetch.py --dry-run

If it errors, fix the script. The three expected steps are:
  1. Calls `tinyfish fetch <url>` for each source URL
  2. Parses the result
  3. Prints what would be added (dry-run, writes nothing)

**7b.** Run for real and confirm `data/welfare_directory.json` is updated:
  .venv\Scripts\python scripts/welfare_fetch.py

The file must contain at least 1 valid entry with all required fields
(scheme_name, type, contact, effective_date, url, added_at).

**7c.** Run the evidence watch in backfill mode:
  .venv\Scripts\python scripts/evidence_watch.py --since 2024-01-01

It must complete without crashing, update `last_checked` in
`config/evidence_baseline.json`, and print INFO-level logs.

---

### TASK 8 — Trust tests: dry-run against the running SAMVEDNA console

**Prerequisite:** SAMVEDNA must be running. Start it:
  cd "D:\Samvedna SIH with Truevoice\samvedna\samvedna"
  .\run.ps1
Wait for "API ready" and "Console ready" messages.

**8a.** Run one trust test manually via TinyFish CLI:
  cd D:\samvedna-tinyfish
  npx -y @tiny-fish/cli@latest agent run agents/trust_tests.yaml ^
    --var ROLE=commanding_officer ^
    --var ACTION=open_individual_case ^
    --var SAMVEDNA_CONSOLE_URL=http://127.0.0.1:3100

Expected outcome: PASS (the console returns 403 / Access denied).
If the agent YAML needs adjusting to work with the actual running console,
fix it now.

**8b.** Run all 6 test combinations and record outcomes:
  commanding_officer + open_individual_case
  commanding_officer + view_small_unit
  auditor + change_verdict
  auditor + download_raw_records
  welfare_officer + view_out_of_scope_unit
  personnel + read_other_self_assessment

Write all outcomes to `reports/nightly_trust_report_<today>.md`
using the template in `reports/nightly_trust_report.md`.

**8c.** POST the results to the running SAMVEDNA API:
  For each result, call:
  POST http://127.0.0.1:8090/api/audit/trust_test
  With the outcome JSON and the service token from .env.

---

### TASK 9 — Integration smoke test

With SAMVEDNA running:

**9a.** Test the welfare directory endpoint:
  curl http://127.0.0.1:8090/api/welfare/directory
  Must return JSON with an `items` array.

**9b.** Test the directory refresh:
  curl -X POST http://127.0.0.1:8090/api/welfare/directory/refresh
  Must return `{"status":"ok","count":N,...}`

**9c.** Test evidence drift alert:
  curl -X POST http://127.0.0.1:8090/api/alerts/evidence_drift ^
    -H "Content-Type: application/json" ^
    -d "{\"field\":\"capf_suicide_per_year\",\"old_value\":130,\"new_value\":145,\"source_url\":\"https://pib.gov.in/test\",\"snippet\":\"test\",\"run_id\":\"smoke-test-001\"}"
  Must return `{"status":"logged"}`.

**9d.** Open http://127.0.0.1:3100 in a browser:
  - Sign in as `wo12` (welfare officer)
  - Navigate to the officer console
  - Confirm "Welfare Resources" section is visible and loads
  - Sign out

  - Sign in as `au03` (auditor)
  - Navigate to Evidence Baselines page
  - Confirm the baseline table is visible
  - Navigate to Trust Tests page
  - Confirm today's report is shown
  - Sign out

---

### TASK 10 — Final validation and report

**10a.** Run the full SAMVEDNA test suite (do not break existing tests):
  cd "D:\Samvedna SIH with Truevoice\samvedna\samvedna"
  uv run pytest -q
  Target: 849 passed, 15 skipped (or better). Zero new failures allowed.

**10b.** Run the TinyFish project tests:
  cd D:\samvedna-tinyfish
  .venv\Scripts\pytest tests/ -v
  All tests must pass.

**10c.** Run `tinyfish doctor --pretty` and confirm:
  cursor registration: PASS (already verified)
  authenticated call: PASS
  No new failures.

**10d.** Create `D:\samvedna-tinyfish\INTEGRATION_STATUS.md` with this template
(fill in real values after running):

```markdown
# SAMVEDNA × TinyFish Integration Status
Generated: <ISO-8601 timestamp>

## Backend routes (all in api/tinyfish_routes.py)
- [ ] POST /api/welfare/directory/refresh — status: <OK|FAIL>
- [ ] GET  /api/welfare/directory         — status: <OK|FAIL>
- [ ] POST /api/alerts/evidence_drift     — status: <OK|FAIL>
- [ ] POST /api/audit/trust_test          — status: <OK|FAIL>
- [ ] POST /api/alerts/trust_failure      — status: <OK|FAIL>
- [ ] GET  /api/tinyfish/evidence-baseline — status: <OK|FAIL>
- [ ] GET  /api/tinyfish/trust-tests/latest — status: <OK|FAIL>

## Frontend pages
- [ ] WelfareDirectory component         — status: <OK|FAIL>
- [ ] Evidence Baselines page (/evidence) — status: <OK|FAIL>
- [ ] Trust Tests page (/trust)           — status: <OK|FAIL>

## Airflow DAGs (syntax check)
- [ ] hrms_connector.py                  — status: <OK|FAIL>
- [ ] welfare_directory.py               — status: <OK|FAIL>
- [ ] evidence_watch.py                  — status: <OK|FAIL>
- [ ] trust_tests.py                     — status: <OK|FAIL>

## Script runs
- [ ] welfare_fetch.py --dry-run         — status: <OK|FAIL>
- [ ] welfare_fetch.py (live)            — status: <OK|FAIL> entries: <N>
- [ ] evidence_watch.py --since 2024-01  — status: <OK|FAIL>

## Trust test results (latest run)
- [ ] commanding_officer / open_individual_case  — <PASS|FAIL|INCONCLUSIVE>
- [ ] commanding_officer / view_small_unit        — <PASS|FAIL|INCONCLUSIVE>
- [ ] auditor / change_verdict                    — <PASS|FAIL|INCONCLUSIVE>
- [ ] auditor / download_raw_records              — <PASS|FAIL|INCONCLUSIVE>
- [ ] welfare_officer / view_out_of_scope_unit    — <PASS|FAIL|INCONCLUSIVE>
- [ ] personnel / read_other_self_assessment      — <PASS|FAIL|INCONCLUSIVE>

## Test suites
- SAMVEDNA suite: <N> passed, <N> skipped, <N> failed
- TinyFish suite: <N> passed, <N> failed

## Open issues
<list anything that is not DONE or is INCONCLUSIVE>
```

---

## CONSTRAINTS (apply to every line of code you write)

1. **Privacy first:** No real personnel name or unmasked PID ever appears in
   any log, API response, or file outside the ingest step.

2. **No secrets in code:** All credentials come from TinyFish Vault or .env.
   The .env file is never committed (already in .gitignore).

3. **Audit everything:** Every TinyFish run that touches SAMVEDNA data must
   write a run_id to the hash-chained audit ledger.

4. **Do not break existing SAMVEDNA:** The 849 passing tests and the working
   console must remain intact. If you must modify an existing file, make the
   minimum change needed.

5. **DPDP 2023 compliance:** k-anonymity (k>=5) enforced on all unit aggregates.
   No individual data visible to commanding officer role.

6. **Offline by default:** The SAMVEDNA core runs with UV_OFFLINE=1 and
   NEXT_TELEMETRY_DISABLED=1. Your new routes must not make external HTTP
   calls at request time. Only the background scripts (welfare_fetch.py,
   evidence_watch.py) may make outbound calls.

7. **Fail safely:** If TinyFish agent fails (CAPTCHA, timeout, network),
   never write partial data. Alert and skip.

8. **Test coverage:** Every new backend route must have at least one test.
   Do not delete or skip existing tests.

---

## WHAT TO REPORT WHEN DONE

When all 10 tasks are complete, write the final INTEGRATION_STATUS.md and
report:
1. Which tasks completed successfully
2. Which (if any) are INCONCLUSIVE and why
3. The trust test outcomes for all 6 role/action pairs
4. The count of welfare directory entries loaded
5. Whether the SAMVEDNA test suite is still clean
6. Any open items the human needs to finish (e.g., production vault setup,
   Airflow deployment to NIC infrastructure, obtaining real HRMS portal URL)

---

*End of master agent prompt.*
*Source: D:\samvedna-tinyfish\MASTER_AGENT_PROMPT.md*
*Pitch deck reference: SAMVEDNA_CodeZila_Pitch_9_slides.pdf, Slide 7*
