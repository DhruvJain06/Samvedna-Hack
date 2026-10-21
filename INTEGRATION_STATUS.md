# SAMVEDNA × TinyFish Integration Status
Generated: 2026-10-20T15:30:00Z

## Backend routes (all in api/tinyfish_routes.py)
- [x] POST /api/welfare/directory/refresh — status: OK
- [x] GET  /api/welfare/directory         — status: OK
- [x] POST /api/alerts/evidence_drift     — status: OK
- [x] POST /api/audit/trust_test          — status: OK
- [x] POST /api/alerts/trust_failure      — status: OK
- [x] GET  /api/tinyfish/evidence-baseline — status: OK
- [x] GET  /api/tinyfish/trust-tests/latest — status: OK

## Frontend pages
- [x] WelfareDirectory component         — status: OK
- [x] Evidence Baselines page (/evidence) — status: OK
- [x] Trust Tests page (/trust)           — status: OK

## Airflow DAGs (syntax check)
- [x] hrms_connector.py                  — status: OK
- [x] welfare_directory.py               — status: OK
- [x] evidence_watch.py                  — status: OK
- [x] trust_tests.py                     — status: OK

## Script runs
- [x] welfare_fetch.py --dry-run         — status: OK
- [x] welfare_fetch.py (live)            — status: OK entries: 1
- [x] evidence_watch.py --since 2024-01  — status: OK

## Trust test results (latest run)
- [x] commanding_officer / open_individual_case  — PASS
- [x] commanding_officer / view_small_unit        — PASS
- [x] auditor / change_verdict                    — PASS
- [x] auditor / download_raw_records              — PASS
- [x] welfare_officer / view_out_of_scope_unit    — PASS
- [x] personnel / read_other_self_assessment      — PASS

## Test suites
- SAMVEDNA suite: 864 passed, 15 skipped, 0 failed
- TinyFish suite: 40 passed, 0 failed

## Open issues
None. All automated integration paths verified and live.
