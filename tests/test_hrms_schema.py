"""
tests/test_hrms_schema.py
Unit tests for the HRMS connector JSON schema validator.
Uses synthetic data only — no real PIDs or personal information.

Run with:  python -m pytest tests/test_hrms_schema.py -v
"""
import hashlib
import re
import pytest

# ---------------------------------------------------------------------------
# Helpers mirroring the validation logic in dags/hrms_connector.py
# ---------------------------------------------------------------------------
PID_HASH_RE = re.compile(r"^[a-f0-9]{64}$")


def validate_record(r: dict) -> None:
    """Raise AssertionError if the record does not match the HRMS schema."""
    assert PID_HASH_RE.match(r.get("pid_hash", "")), \
        f"pid_hash must be a 64-char lowercase hex string, got: {r.get('pid_hash')!r}"
    assert isinstance(r.get("duty_days_consecutive"), int) and r["duty_days_consecutive"] >= 0, \
        f"duty_days_consecutive must be a non-negative int, got: {r.get('duty_days_consecutive')!r}"
    assert isinstance(r.get("leave_balance_days"), int) and r["leave_balance_days"] >= 0, \
        f"leave_balance_days must be a non-negative int, got: {r.get('leave_balance_days')!r}"
    assert isinstance(r.get("unit_code"), str) and r["unit_code"], \
        f"unit_code must be a non-empty string, got: {r.get('unit_code')!r}"
    # last_posting_change_date is optional (may be None)
    lpcd = r.get("last_posting_change_date")
    if lpcd is not None:
        # Must look like an ISO-8601 date
        assert re.match(r"^\d{4}-\d{2}-\d{2}", lpcd), \
            f"last_posting_change_date must be ISO-8601, got: {lpcd!r}"


def make_pid_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
VALID_RECORD = {
    "pid_hash": make_pid_hash("SYNTHETIC_001"),
    "duty_days_consecutive": 31,
    "leave_balance_days": 7,
    "last_posting_change_date": "2026-08-15",
    "unit_code": "U01",
}

VALID_RECORD_NO_POSTING = {
    "pid_hash": make_pid_hash("SYNTHETIC_002"),
    "duty_days_consecutive": 0,
    "leave_balance_days": 0,
    "last_posting_change_date": None,
    "unit_code": "U02",
}


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------
def test_valid_record():
    validate_record(VALID_RECORD)


def test_valid_record_no_posting_date():
    validate_record(VALID_RECORD_NO_POSTING)


def test_valid_record_zero_duty_days():
    r = {**VALID_RECORD, "duty_days_consecutive": 0}
    validate_record(r)


def test_valid_large_leave_balance():
    r = {**VALID_RECORD, "leave_balance_days": 365}
    validate_record(r)


# ---------------------------------------------------------------------------
# Negative tests — each should fail validation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_pid", [
    "",                      # empty
    "abc123",                # too short
    "Z" * 64,                # not hex
    make_pid_hash("x").upper(),  # uppercase
    None,                    # missing
])
def test_bad_pid_hash(bad_pid):
    r = {**VALID_RECORD, "pid_hash": bad_pid}
    with pytest.raises((AssertionError, TypeError)):
        validate_record(r)


@pytest.mark.parametrize("bad_duty", [-1, "14", 3.5, None])
def test_bad_duty_days(bad_duty):
    r = {**VALID_RECORD, "duty_days_consecutive": bad_duty}
    with pytest.raises((AssertionError, TypeError)):
        validate_record(r)


@pytest.mark.parametrize("bad_leave", [-1, "7", None])
def test_bad_leave_balance(bad_leave):
    r = {**VALID_RECORD, "leave_balance_days": bad_leave}
    with pytest.raises((AssertionError, TypeError)):
        validate_record(r)


@pytest.mark.parametrize("bad_unit", ["", None, 123])
def test_bad_unit_code(bad_unit):
    r = {**VALID_RECORD, "unit_code": bad_unit}
    with pytest.raises((AssertionError, TypeError)):
        validate_record(r)


@pytest.mark.parametrize("bad_date", ["15-08-2026", "August 2026", ""])
def test_bad_posting_date(bad_date):
    r = {**VALID_RECORD, "last_posting_change_date": bad_date}
    with pytest.raises(AssertionError):
        validate_record(r)


# ---------------------------------------------------------------------------
# Batch validation
# ---------------------------------------------------------------------------
def test_batch_of_records():
    batch = [VALID_RECORD, VALID_RECORD_NO_POSTING] * 120  # 240 records
    for rec in batch:
        validate_record(rec)


def test_pid_hash_is_deterministic():
    h1 = make_pid_hash("SYNTHETIC_999")
    h2 = make_pid_hash("SYNTHETIC_999")
    assert h1 == h2


def test_different_pids_produce_different_hashes():
    h1 = make_pid_hash("SYNTHETIC_001")
    h2 = make_pid_hash("SYNTHETIC_002")
    assert h1 != h2


def test_real_pid_not_in_hash():
    """Ensure the raw PID cannot be trivially recovered from the hash."""
    raw = "REAL_PID_12345"
    hashed = make_pid_hash(raw)
    assert raw not in hashed
