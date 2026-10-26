# Synthetic Data Validation & Anomaly Benchmark Report

- **Scale**: FULL
- **Seed**: `20261022`
- **Overall Structural Integrity**: ✅ PASS

## 1. 8-Point Structural & Relational Verification

| Verification Check | Status | Details |
| --- | --- | --- |
| `pk_uniqueness` | ✅ PASS | Structural consistency verified |
| `foreign_key_integrity` | ✅ PASS | Structural consistency verified |
| `allowed_enums` | ✅ PASS | Structural consistency verified |
| `date_ordering` | ✅ PASS | Structural consistency verified |
| `arithmetic_reconciliation` | ✅ PASS | Structural consistency verified |
| `lifecycle_transitions` | ✅ PASS | Structural consistency verified |
| `duplicate_checks` | ✅ PASS | Structural consistency verified |

## 2. Ground Truth Anomaly Benchmark (Evaluation Focus)

- **Total Ground Truth Injected**: 5
- **True Positives**: 5
- **False Positives**: 2
- **False Negatives**: 0
- **Precision**: `71.4%`
- **Recall**: `100.0%`
- **F1 Score**: `83.3%`

### Detected Edge Case Anomalies

| Rule Code | Severity | Entity | Entity ID | Issue Message |
| --- | --- | --- | --- | --- |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-A-000001` | Employee EMP-000501 has overlapping shifts SHIFT-2026-01-01-A-000001 (2026-01-01T07:00:00Z to 2026-01-01T15:30:00Z) and SHIFT-2026-01-01-B-999001 (2026-01-01T15:00:00Z to 2026-01-01T23:30:00Z) |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-08-C-999003` | Employee EMP-000003 has overlapping shifts SHIFT-2026-01-08-C-999003 (2026-01-08T23:00:00Z to 2026-01-09T07:30:00Z) and SHIFT-2026-01-09-A-007355 (2026-01-09T07:00:00Z to 2026-01-09T15:30:00Z) |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-10-C-999005` | Employee EMP-000003 has overlapping shifts SHIFT-2026-01-10-C-999005 (2026-01-10T23:00:00Z to 2026-01-11T07:30:00Z) and SHIFT-2026-01-11-A-009027 (2026-01-11T07:00:00Z to 2026-01-11T15:30:00Z) |
| `RULE_APPROVED_LEAVE_NON_CONFLICT` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-03-02-A-999002` | Shift SHIFT-2026-03-02-A-999002 scheduled for EMP-001668 during approved leave LVE-2026-000002 on 2026-03-02 |
| `RULE_MANDATORY_ROLE_SKILL_MATCH` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-B-000006` | Shift SHIFT-2026-01-01-B-000006 mandates skill SKILL-01 but assigned employee EMP-000002 lacks credential |
| `RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP` | `ANOMALY_DETECTED` | Employee | `EMP-000003` | Employee EMP-000003 scheduled for 56.0h in week 2, exceeding legal cap of 52.0h |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-999001` | Swap SWP-2026-999001 has APPLIED status but lacks required manager authorization signoff |
