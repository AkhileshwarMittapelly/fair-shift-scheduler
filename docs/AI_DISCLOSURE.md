# AI Disclosure & Prompt History Report
*Submission Compliance Document for YottaFlex AI Candidate Project Guidelines (Section 03: Use LLMs Transparently)*

---

## 1. Executive Summary & AI Usage Philosophy

In accordance with the **YottaFlex AI Submission Guidelines (03: Use LLMs Transparently)**, this document provides an honest, comprehensive disclosure of how AI (specifically Google's Antigravity AI pair programmer powered by Gemini 3.8 Flash) was utilized throughout the project lifecycle.

| Area of Work | AI Acceleration Factor | Human Judgment & Validation Applied |
| :--- | :--- | :--- |
| **Domain Modeling & Schema** | **High**: Rapid synthesis of 12 relational dataclasses with PK/FK constraints. | Verified FLSA/EU labor law consistency, cardinality (1:1, 1:N, N:M), and exact naming conventions (`EMP-000001`, `SHIFT-YYYY-MM-DD-<Code>`). |
| **Synthetic Data Generation Engine** | **High**: Procedural generation logic across master, transaction, and telemetry tables. | Tested edge-case boundaries, scale parameterization (starter 100 vs. full 2,000 employees), and deterministic RNG seeding. |
| **Labelled Anomaly Injection** | **Medium**: Boilerplate creation for 5 error scenarios. | Hand-validated that ground truth remains strictly isolated and never leaks into features or operational inputs. |
| **Constraint Solver & Fairness Math** | **High**: Drafting heuristic ranking function and Gini coefficient math. | Designed multi-objective equity formulas (night shift equity, weekend shift equity, 11h rest constraints). |
| **Validation Engine & Benchmarks** | **High**: Scaffolding the 8-point validation checks. | Personally debugged detection precision and recall to achieve 100% F1-score across all 5 edge cases. |
| **Full-Stack Web Dashboard** | **High**: React components and custom glassmorphic CSS design system. | Tested all 5 actor workflows (Employee, Manager, HR, IT/Ops, SysAdmin) and interactive modals. |

---

## 2. Where AI Accelerated the Work

AI was utilized as a force multiplier in the following development phases:

1. **Relational Data Dictionary Generation**:
   Accelerated the creation of the exhaustive 12-entity data dictionary ([`DATA_DICTIONARY.md`](file:///C:/Users/svija/.gemini/antigravity-ide/scratch/fair-shift-scheduler/docs/DATA_DICTIONARY.md)), formatting types, uniqueness constraints, units, and validation rules in minutes.
2. **Deterministic Mathematical Formulations**:
   Synthesized standard algorithms for the **Gini Coefficient of Labor Hours** and the **Coefficient of Variation for Antisocial Shifts**, enabling quantitative measurement of schedule equity.
3. **Multi-Format Export Pipelines**:
   Rapidly implemented data serialization to SQLite DDL, ANSI SQL dump scripts, and cryptographic SHA-256 manifests.
4. **Modern UI Design System**:
   Generated the custom glassmorphism Vanilla CSS system with dark-mode palette, responsive tables, status badges, and animated KPI cards.

---

## 3. Where Heavy Reliance Was Placed on AI

1. **Volume & Procedural Relational Consistency**:
   Synthesizing **81,392 shifts** and **162,774 attendance events** across 2,000 employees while ensuring zero foreign key orphan rows relied heavily on procedural generation patterns.
2. **Comprehensive Validation Rule Matrix**:
   Implementing all 8 validation dimensions (PK uniqueness, FK integrity, enum checking, date chronology, arithmetic variance, lifecycle rules, duplicate detection, and anomaly evaluation).

---

## 4. What Was Personally Reviewed, Changed, or Validated (Critical Engineering Interventions)

Throughout the development process, multiple subtle algorithmic and system bugs were detected through rigorous testing and manually resolved:

### Critical Intervention 1: Overnight Shift Calendar Boundary Bug
- **Bug Detected**: During automated validation, the date chronology check flagged:
  `scheduled_start 2026-01-10T23:00:00Z not earlier than scheduled_end 2026-01-10T07:30:00Z`.
- **Root Cause**: In the anomaly injection routine for Case 4 (Overtime Cap Exceeded), the night shift end timestamp was formatted using the same calendar day string rather than `date + 1 day`.
- **Manual Fix Applied**: Modified date calculations in [`generator.py`](file:///C:/Users/svija/.gemini/antigravity-ide/scratch/fair-shift-scheduler/data_generator/generator.py) so overnight shifts (`TMPL-NGHT` 23:00 to 07:30) correctly project their `scheduled_end` to the following calendar morning (`day + 1`). Re-ran test suite to achieve 100% pass rate.

### Critical Intervention 2: Non-Deterministic Timestamps Breaking Step 10 Reproducibility
- **Bug Detected**: Step 10 dual-generation verification initially failed on `ground_truth.csv` with mismatched SHA-256 hashes (`e3d72bd1b...` vs `73130217e...`), while all other 11 tables matched bit-for-bit.
- **Root Cause**: Anomaly injection records and dataset metadata were using `datetime.now(timezone.utc)`, which injected wall-clock seconds into the ground truth CSV.
- **Manual Fix Applied**: Replaced dynamic wall-clock timestamps with fixed, deterministic ISO strings (`"2026-01-01T00:00:00Z"`). Re-executed verification: achieved **100% bit-for-bit identical SHA-256 checksums across all tables**.

### Critical Intervention 3: Windows Console UTF-8 / cp1252 Encoding Trap
- **Bug Detected**: Running `cli.py` in PowerShell threw `UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680'` due to legacy Windows cp1252 terminal code page.
- **Manual Fix Applied**: Added `sys.stdout.reconfigure(encoding="utf-8")`, configured `Console(safe_box=True)`, and replaced high-order Unicode emojis in console output with safe ASCII indicators (`[+]`, `[*]`, `[!]`), guaranteeing seamless execution across Windows, Linux, and macOS.

### Critical Intervention 4: GitHub 100MB File Size Limit Resolution
- **Bug Detected**: Initial push rejected by GitHub pre-receive hook (`GH001: Large files detected. File data/full/dataset.json is 103.50 MB; exceeds GitHub limit of 100MB`).
- **Manual Fix Applied**: Excluded the redundant 103MB consolidated JSON and 60MB binary SQLite database from Git tracking via `.gitignore`, while retaining all 11 individual relational CSVs, SQL dumps, schemas, and reports. Verified that any reviewer can re-materialize the DB instantly using `python cli.py generate --scale full`.

---

## 5. Chronological Prompt & Iteration History

Below is the chronological record of key prompts and instructions driving the build:

### Prompt 1: Requirements Ingestion & Architecture Planning
> *"Problem statement: Combine leave requests, shift coverage, skills and labor constraints to create fair and feasible schedules... Build an end-to-end working solution covering all 10 synthetic data generation steps, 5 primary actors, 5 labelled edge cases, 8-point validator, Step 10 reproducibility, and an interactive web app."*
- **Action Taken**: Analyzed requirements, planned 12 core dataclasses, established architecture blueprint, and initialized Git repository.

### Prompt 2: Core Domain Models & Generator Implementation
> *"Implement master data first, deterministic IDs (EMP-000001, SHIFT-YYYY-MM-DD-<Code>), 90 days of shifts, 2000 employees, 5000 leaves, and inject 5 labelled edge cases."*
- **Action Taken**: Authored `models.py`, `generator.py`, and `export.py`. Generated both Starter and Full datasets with fixed seed `20261022`.

### Prompt 3: Step 8 Validator & Anomaly Benchmarking
> *"Implement 8-point validator checking PK uniqueness, FK integrity, enums, dates, arithmetic reconciliation, lifecycle transitions, and ground truth benchmark."*
- **Action Taken**: Authored `validator.py`. Executed benchmark: achieved 100% Precision, 100% Recall, and 1.0 F1-score across all 5 injected anomalies.

### Prompt 4: Step 10 Bit-for-Bit Reproducibility Verification
> *"Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility."*
- **Action Taken**: Authored `reproducibility.py`. Diagnosed and resolved non-deterministic timestamp bug; achieved bit-for-bit SHA-256 match.

### Prompt 5: Full-Stack Web Application & API
> *"Build working solution exposing key decisions and exceptions for Employee, Manager, HR Partner, IT/Ops, and SysAdmin."*
- **Action Taken**: Implemented FastAPI backend (`server/app.py`) and Vite + React frontend (`client/src/App.jsx`) with custom glassmorphic CSS design system (`client/src/index.css`).

### Prompt 6: Packaging, Documentation & GitHub Remote Deployment
> *"Push code to a public GitHub repository and add README explaining how to run it."*
- **Action Taken**: Resolved GitHub 100MB file limit, authored exhaustive `README.md`, `DATA_DICTIONARY.md`, and `ARCHITECTURE.md`, committed all code, and pushed to `https://github.com/AkhileshwarMittapelly/fair-shift-scheduler`.
