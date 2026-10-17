"""Natural-language TinyFish agent goals (CLI 0.49).

Never put passwords, tokens, or 2FA codes in these strings.
Use --use-vault at runtime. agents/*.yaml is the human spec that these encode.
"""
from __future__ import annotations

HRMS_GOAL_TEMPLATE = """Sign in to the force HRMS portal using vault-filled credentials only — do not type or invent a password.
For each unit code in: {unit_codes}
open the roster, leave-balance, and posting/transfer pages.
Extract one record per person with:
- pid_hash: SHA-256 hex of the raw personnel id, computed before any data is returned
- duty_days_consecutive: integer
- leave_balance_days: integer
- last_posting_change_date: ISO-8601 date or null
- unit_code: the unit being scraped
Abort immediately on CAPTCHA, login failure, or missing tables. Return no partial records.
Do not click purchase, submit extra forms, or change any settings."""

TRUST_GOALS: dict[tuple[str, str], tuple[str, str]] = {
    # (role, action): (start_path, goal)
    ("commanding_officer", "open_individual_case"): (
        "/officer?case=SYNTHETIC_001",
        "Sign in as demo user co01 using vault-filled credentials only. "
        "Attempt to open individual case SYNTHETIC_001 or any gate score for a named person. "
        "Do not change data. Record whether the UI or API refused (HTTP 403 or Access denied). "
        "Return JSON {{outcome: PASS if blocked, FAIL if the case was visible, INCONCLUSIVE if login or timeout}}. "
        "Never type a password into the page yourself.",
    ),
    ("commanding_officer", "view_small_unit"): (
        "/unit?unit=SMALL_UNIT_001",
        "Sign in as demo user co01 using vault-filled credentials only. "
        "Attempt to view unit SMALL_UNIT_001 which has fewer than 5 people. "
        "PASS if k-anonymity blocks it (403 or Access denied). FAIL if unit-level individual data is shown. "
        "Do not change settings or export data.",
    ),
    ("auditor", "change_verdict"): (
        "/audit",
        "Sign in as demo user au03 using vault-filled credentials only. "
        "Attempt to change a case verdict (POST escalate). "
        "PASS if refused with HTTP 403 or Access denied. FAIL if the verdict changes. "
        "Do not submit any other writes.",
    ),
    ("auditor", "download_raw_records"): (
        "/audit/export?raw=true",
        "Sign in as demo user au03 using vault-filled credentials only. "
        "Attempt to download non-aggregated raw records. "
        "PASS if blocked. FAIL if a raw export downloads. Do not keep files.",
    ),
    ("welfare_officer", "view_out_of_scope_unit"): (
        "/officer?unit=OUT_OF_SCOPE_UNIT",
        "Sign in as demo user wo12 using vault-filled credentials only. "
        "Attempt to view cases for OUT_OF_SCOPE_UNIT. "
        "PASS if refused. FAIL if out-of-scope cases are listed. Do not contact anyone.",
    ),
    ("personnel", "read_other_self_assessment"): (
        "/me?pid=OTHER_PERSONNEL_001",
        "Sign in as demo user personnel using vault-filled credentials only. "
        "Attempt to read another person's self-assessment (OTHER_PERSONNEL_001). "
        "PASS if refused. FAIL if another person's answers are visible.",
    ),
}


def hrms_goal(unit_codes: str) -> str:
    return HRMS_GOAL_TEMPLATE.format(unit_codes=unit_codes)
