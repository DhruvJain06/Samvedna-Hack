# SAMVEDNA: Privacy-First Mental Health & Early Welfare System for Armed Forces

> **SAMVEDNA** is an early-intervention, privacy-preserving welfare and mental health decision-support system designed specifically for India's Central Armed Police Forces (CAPF) and military personnel.

---

## ðŸŽ–ï¸ What is SAMVEDNA? (In Layman's Terms)

In the armed forces, soldiers face high-stress operational realitiesâ€”long deployments, prolonged night duties, separation from family, and tough physical conditions. Due to military culture and fear of career stigma, jawans rarely ask for psychological help openly, often saying *"Sab theek hai, sir"* (Everything is fine) until extreme burnout or crisis occurs.

**SAMVEDNA solves this quietly without stigmatizing anyone.**

It acts as a smart, confidential protective shield that:
1. **Never labels someone based on guesswork:** Instead of using opaque black-box AI, it uses a **4-Gate Evidence Engine** that requires verified, multi-domain proof before any welfare officer is alerted.
2. **Listens to Physical Strain, Not Just Words:** Includes an ephemeral **Voice Biomarker Engine** that measures vocal cord strain (pitch tremor, speech cadence, monotone fatigue) during routine calls without ever recording or storing audio.
3. **Adaptive Tactical Self-Assessments (ATAS):** Replaces rigid civilian questionnaires with duty-related questions (sentry recovery, weapon drill stamina, section friction) and dynamically rotates out questions that add zero value.
4. **Protects Career & Confidentiality:** A Commanding Officer cannot view confidential medical or emotional notes. Only authorized medical/welfare officers receive anonymous early warnings to provide leave or support before a crisis develops.

---

## ðŸ›ï¸ How the SAMVEDNA Core Engine Works

```
  [ Administrative HRMS Data ]      [ Tactical Self-Report ]      [ Ephemeral Voice Analysis ]
  (Duty cycles, denied leave)       (Duty recovery, sentry sleep)   (Acoustic strain, no audio kept)
               â”‚                                â”‚                                â”‚
               â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                â”‚
                                                â–¼
                              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                              â”‚     4-Gate Verification Engine    â”‚
                              â”‚ 1. Concordance (Words vs Tone)    â”‚
                              â”‚ 2. Corroboration (â‰¥2 Domains)     â”‚
                              â”‚ 3. Persistence (Not just 1 bad day)â”‚
                              â”‚ 4. Proportionality Gate           â”‚
                              â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                                â”‚
                                                â–¼
                                [ Timely Confidential Welfare Action ]
                                (Leave rotation, peer buddy check,
                                 or immediate medical officer visit)
```

---

## ðŸŸ What Does TinyFish Do in SAMVEDNA? (In Layman's Terms)

Think of SAMVEDNA as a clinical decision room, and **TinyFish as our 24/7 automated digital field officer, auditor, and courier**:

1. **The Automatic HRMS Courier (Legacy HRMS Connector):**
   * *Problem:* CAPF internal personnel portals do not have modern public APIs.
   * *What TinyFish does:* Logs into the legacy portal on schedule, extracts anonymized duty days, leave balances, and postings, and feeds them into SAMVEDNA's evidence engine without storing passwords or exposing identities.

2. **The 24/7 Policy & Scheme Detective (Live Welfare Directory):**
   * *Problem:* Government financial aids, helplines, educational grants for children, and ex-gratia policies change constantly across different circulars.
   * *What TinyFish does:* Crawls official portals daily, parses new government circulars, and updates SAMVEDNA's welfare directory so personnel always see live, valid assistance contacts.

3. **The Clinical Research Assistant (Evidence & Policy Watch):**
   * *Problem:* Risk thresholds must reflect the latest medical and operational research (ICMR, WHO, Ministry of Home Affairs).
   * *What TinyFish does:* Executes periodic automated searches across scientific databases and flags whenever clinical stress benchmarks update.

4. **The Security Guard / Auditor (Nightly RBAC Trust Tests):**
   * *Problem:* Role-Based Access Control (RBAC) must never leak private medical disclosures to Commanding Officers.
   * *What TinyFish does:* Every night at 03:00 IST, TinyFish simulates 4 distinct user roles (Commanding Officer, Welfare Officer, Auditor, Jawan) and attempts unauthorized access. If any privacy gate fails, an immediate alert is dispatched.

---

## ðŸŽ¯ Summary of System Capabilities

| Domain | Mechanism | Purpose |
|---|---|---|
| **Early Warning** | 4-Gate Cross-Verification Engine | Prevents false alarms by demanding multi-source corroboration before naming. |
| **Tactical Assessment** | Adaptive Self-Assessment (ATAS) | Dynamic question rotation; measures sentry recovery and operational stress. |
| **Voice Analytics** | Ephemeral Vocal Cord Biomarkers | Detects strain & exhaustion in real-time; **zero audio is ever stored**. |
| **HRMS Ingestion** | TinyFish Web Agent + Vault | Nightly automated ingestion of duty records from legacy force portals. |
| **Welfare Directory** | TinyFish Fetch Monitor | Daily live tracking of CAPF circulars, grants, and support helplines. |
| **Security Audit** | TinyFish Nightly Trust Runner | Automated penetration tests verifying zero unauthorized data leakage. |

---

## ðŸš€ Quick Start & Setup

### 1. Environment & Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 2. Verify TinyFish CLI
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

## ðŸ“‚ Project Architecture

```
samvedna-tinyfish/
â”œâ”€â”€ agents/             # TinyFish Web Agent & Monitor configuration specs (.yaml)
â”œâ”€â”€ config/             # Baseline clinical evidence thresholds & parameters
â”œâ”€â”€ dags/               # Airflow automation DAGs for scheduled execution
â”œâ”€â”€ data/               # Live welfare directory cache & extracted indices
â”œâ”€â”€ reports/            # Automated nightly trust and RBAC audit reports
â”œâ”€â”€ scripts/            # CLI wrappers, orchestration, and sync scripts
â”‚   â”œâ”€â”€ tinyfish_cli.py     # Unified CLI bridge for Search, Fetch & Agent runs
â”‚   â”œâ”€â”€ welfare_fetch.py    # Automatic circular & welfare directory crawler
â”‚   â”œâ”€â”€ evidence_watch.py   # Clinical literature & policy monitoring script
â”‚   â””â”€â”€ hrms_connector.py   # Portal automation connector
â”œâ”€â”€ tests/              # 40 unit and integration tests
â”œâ”€â”€ samvedna_overlay/   # Application-level patches and API bridges
â””â”€â”€ README.md           # Project documentation
```

---

## ðŸ›¡ï¸ Privacy & Security Invariants

* **No Plaintext Passwords:** Credentials reside exclusively in the secure **TinyFish Vault**; never committed to git or stored in `.env`.
* **Salted Identity Hashes:** All personnel IDs are hashed (`pid_hash`) before processing; no plain personal identifiers ever leave the connector.
* **Ephemeral Audio Analysis:** Voice analysis operates entirely in temporary volatile memory; raw audio files and conversation transcripts are permanently discarded immediately after feature extraction.

---

## ðŸ‘¥ Authors
Team CodeZila
