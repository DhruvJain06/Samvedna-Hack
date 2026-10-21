# SAMVEDNA x TinyFish Integration

Integration project for connecting the **TinyFish Autonomous Web & Search Agent Engine** with the **SAMVEDNA Mental-Health Welfare & Risk Detection System** (Team CodeZila / SIH 2026).

---

## 💡 What is TinyFish's Role in Our Project? (In Layman's Terms)

Think of SAMVEDNA as a doctor's clinic, and **TinyFish as our 24/7 digital field officer, auditor, and courier**. Instead of humans having to manually check websites, download HR records, or test security every day, TinyFish does it automatically:

1. **The Automatic HRMS Courier (Legacy HRMS Connector):**
   * *Problem:* Many police and armed forces portals (like CRPF/CAPF HRMS) don't have modern APIs.
   * *What TinyFish does:* TinyFish logs into the internal portal, fetches duty rosters, leave balances, and postings, and turns them into clean numbers for the SAMVEDNA risk engine—without storing credentials or exposing personal identities.

2. **The 24/7 Policy & Scheme Detective (Live Welfare Directory):**
   * *Problem:* Government welfare schemes, helplines, ex-gratia policies, and child education benefits change frequently across different government orders.
   * *What TinyFish does:* TinyFish automatically monitors official websites daily. The moment a new circular or helpline is released, it parses it and updates SAMVEDNA's directory so soldiers always see live, accurate support contacts.

3. **The Research Assistant (Evidence & Policy Watch):**
   * *Problem:* Clinical risk weights need to match the latest ICMR, WHO, and Ministry of Home Affairs studies on operational stress.
   * *What TinyFish does:* TinyFish executes automated periodic search queries across trusted sources and flags whenever a benchmark or operational stress guideline changes.

4. **The Security Guard / Auditor (Nightly RBAC Trust Tests):**
   * *Problem:* In military software, privacy is paramount: a Commanding Officer must never see private therapy logs, and a Welfare Officer must only see legitimate cases.
   * *What TinyFish does:* Every night at 03:00 IST, TinyFish pretends to be 4 different roles (Commanding Officer, Welfare Officer, Auditor, Jawan) and attempts unauthorized actions. If a privacy rule or data gate fails, TinyFish immediately triggers a PagerDuty/webhook alert to the engineering team.

---

## 🎯 Summary of Key Capabilities

| Component | TinyFish Feature | Schedule | Purpose |
|---|---|---|---|
| **Legacy HRMS Ingestion** | Autonomous Web Agent + Vault | Nightly 01:00 IST | Extracts anonymized duty and leave records from force portals. |
| **Live Welfare Directory** | Content Fetch Monitor | Daily 02:00 IST | Keeps CAPF financial schemes, helplines, and aid contacts updated. |
| **Evidence & Policy Watch** | Search Query + Content Fetch | Weekly Mon 06:00 IST | Monitors psychiatric and operational stress research updates. |
| **Nightly RBAC Trust Audit** | Web Agent Automated Audit | Nightly 03:00 IST | Verifies access control and privacy invariants across all 4 user roles. |

---

## 🚀 Quick Start & Setup

### 1. Environment & Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 2. TinyFish CLI Verification
TinyFish CLI 0.51+ is supported:
```powershell
tinyfish auth status
tinyfish search query "CRPF welfare circular" --pretty
```

### 3. Run Test Suite
```powershell
.\.venv\Scripts\python -m pytest tests/ -v
```
*(40/40 tests covering schema validation, CLI grammar, and agent workflows pass cleanly).*

---

## 📂 Project Architecture

```
samvedna-tinyfish/
├── agents/             # TinyFish Web Agent & Monitor configuration specs (.yaml)
├── config/             # Baseline clinical evidence thresholds & parameters
├── dags/               # Airflow automation DAGs for scheduled execution
├── data/               # Live welfare directory cache & extracted indices
├── reports/            # Automated nightly trust and RBAC audit reports
├── scripts/            # CLI wrappers, orchestration, and sync scripts
│   ├── tinyfish_cli.py     # Unified CLI bridge for Search, Fetch & Agent runs
│   ├── welfare_fetch.py    # Automatic circular & welfare directory crawler
│   ├── evidence_watch.py   # Clinical literature & policy monitoring script
│   └── hrms_connector.py   # Portal automation connector
├── tests/              # 40 unit and integration tests
├── samvedna_overlay/   # Application-level patches and API bridges
└── README.md           # This documentation
```

---

## 🛡️ Privacy & Security Invariants

* **No Plaintext Passwords:** Passwords and tokens are stored in the secure **TinyFish Vault**; never in `.env` files or git.
* **No Direct Soldier Identifiers:** All personal IDs are hashed (`pid_hash`) before leaving the HRMS connector.
* **Zero Audio Retention:** SAMVEDNA voice sessions analyze acoustic frequencies strictly in ephemeral memory and immediately discard audio frames.

---

## 👥 Authors
Team CodeZila — Smart India Hackathon (SIH 2026) / HackIIITD Esya 26
