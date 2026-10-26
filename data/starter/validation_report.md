# Synthetic Data Validation & Anomaly Benchmark Report

- **Scale**: STARTER
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
| `duplicate_checks` | ✅ PASS | Structural consistency verified |

## 2. Ground Truth Anomaly Benchmark (Evaluation Focus)

- **Total Ground Truth Injected**: 5
- **True Positives**: 5
- **False Positives**: 3
- **False Negatives**: 0
- **Precision**: `62.5%`
- **Recall**: `100.0%`
- **F1 Score**: `76.9%`

### Detected Edge Case Anomalies

| Rule Code | Severity | Entity | Entity ID | Issue Message |
| --- | --- | --- | --- | --- |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-A-000001` | Employee EMP-000051 double-booked with 2 shifts on 2026-01-01 (SHIFT-2026-01-01-A-000001, SHIFT-2026-01-01-B-999001) |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-A-000006` | Employee EMP-000002 double-booked with 2 shifts on 2026-01-01 (SHIFT-2026-01-01-A-000006, SHIFT-2026-01-01-A-000007) |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-08-C-000312` | Employee EMP-000003 double-booked with 2 shifts on 2026-01-08 (SHIFT-2026-01-08-C-000312, SHIFT-2026-01-08-C-999003) |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-10-C-000404` | Employee EMP-000003 double-booked with 2 shifts on 2026-01-10 (SHIFT-2026-01-10-C-000404, SHIFT-2026-01-10-C-999005) |
| `RULE_APPROVED_LEAVE_NON_CONFLICT` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-12-A-999002` | Shift SHIFT-2026-01-12-A-999002 scheduled for EMP-000078 during approved leave LVE-2026-000001 on 2026-01-12 |
| `RULE_MANDATORY_ROLE_SKILL_MATCH` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-A-000006` | Shift SHIFT-2026-01-01-A-000006 mandates skill SKILL-01 but assigned employee EMP-000002 lacks credential |
| `RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP` | `ANOMALY_DETECTED` | Employee | `EMP-000003` | Employee EMP-000003 scheduled for 56.0h in week 2, exceeding legal cap of 52.0h |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-999001` | Swap SWP-2026-999001 has APPLIED status but lacks required manager authorization signoff |
