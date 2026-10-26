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
| `duplicate_checks` | ✅ PASS | Structural consistency verified |

## 2. Ground Truth Anomaly Benchmark (Evaluation Focus)

- **Total Ground Truth Injected**: 5
- **True Positives**: 5
- **False Positives**: 0
- **False Negatives**: 0
- **Precision**: `100.0%`
- **Recall**: `100.0%`
- **F1 Score**: `100.0%`

### Detected Edge Case Anomalies

| Rule Code | Severity | Entity | Entity ID | Issue Message |
| --- | --- | --- | --- | --- |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-ShiftCode.A-000001` | Employee EMP-000501 double-booked with 2 shifts on 2026-01-01 (SHIFT-2026-01-01-ShiftCode.A-000001, SHIFT-2026-01-01-B-999001) |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-ShiftCode.B-000006` | Employee EMP-000002 double-booked with 2 shifts on 2026-01-01 (SHIFT-2026-01-01-ShiftCode.B-000006, SHIFT-2026-01-01-ShiftCode.A-000013) |
| `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-09-ShiftCode.A-007361` | Employee EMP-000003 double-booked with 2 shifts on 2026-01-09 (SHIFT-2026-01-09-ShiftCode.A-007361, SHIFT-2026-01-09-C-999004) |
| `RULE_APPROVED_LEAVE_NON_CONFLICT` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-03-02-A-999002` | Shift SHIFT-2026-03-02-A-999002 scheduled for EMP-001668 during approved leave LVE-2026-000002 on 2026-03-02 |
| `RULE_MANDATORY_ROLE_SKILL_MATCH` | `ANOMALY_DETECTED` | ShiftAssignment | `SHIFT-2026-01-01-ShiftCode.B-000006` | Shift SHIFT-2026-01-01-ShiftCode.B-000006 mandates skill SKILL-01 but assigned employee EMP-000002 lacks credential |
| `RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP` | `ANOMALY_DETECTED` | Employee | `EMP-000003` | Employee EMP-000003 scheduled for 56.0h in week 2, exceeding legal cap of 52.0h |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000013` | Swap SWP-2026-000013 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000014` | Swap SWP-2026-000014 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000017` | Swap SWP-2026-000017 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000018` | Swap SWP-2026-000018 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000019` | Swap SWP-2026-000019 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000020` | Swap SWP-2026-000020 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000021` | Swap SWP-2026-000021 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000022` | Swap SWP-2026-000022 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000023` | Swap SWP-2026-000023 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000025` | Swap SWP-2026-000025 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000026` | Swap SWP-2026-000026 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000027` | Swap SWP-2026-000027 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000028` | Swap SWP-2026-000028 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000029` | Swap SWP-2026-000029 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000030` | Swap SWP-2026-000030 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000031` | Swap SWP-2026-000031 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000032` | Swap SWP-2026-000032 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000033` | Swap SWP-2026-000033 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000036` | Swap SWP-2026-000036 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000037` | Swap SWP-2026-000037 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000038` | Swap SWP-2026-000038 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000040` | Swap SWP-2026-000040 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000041` | Swap SWP-2026-000041 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000044` | Swap SWP-2026-000044 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000045` | Swap SWP-2026-000045 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000046` | Swap SWP-2026-000046 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000047` | Swap SWP-2026-000047 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000048` | Swap SWP-2026-000048 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000049` | Swap SWP-2026-000049 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000051` | Swap SWP-2026-000051 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000052` | Swap SWP-2026-000052 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000053` | Swap SWP-2026-000053 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000054` | Swap SWP-2026-000054 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000058` | Swap SWP-2026-000058 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000059` | Swap SWP-2026-000059 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000061` | Swap SWP-2026-000061 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000062` | Swap SWP-2026-000062 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000064` | Swap SWP-2026-000064 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000065` | Swap SWP-2026-000065 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000066` | Swap SWP-2026-000066 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000067` | Swap SWP-2026-000067 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000068` | Swap SWP-2026-000068 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000071` | Swap SWP-2026-000071 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000072` | Swap SWP-2026-000072 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000073` | Swap SWP-2026-000073 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000074` | Swap SWP-2026-000074 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000075` | Swap SWP-2026-000075 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000076` | Swap SWP-2026-000076 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000077` | Swap SWP-2026-000077 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000078` | Swap SWP-2026-000078 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000079` | Swap SWP-2026-000079 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000080` | Swap SWP-2026-000080 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000081` | Swap SWP-2026-000081 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000082` | Swap SWP-2026-000082 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000083` | Swap SWP-2026-000083 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000085` | Swap SWP-2026-000085 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000086` | Swap SWP-2026-000086 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000087` | Swap SWP-2026-000087 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000088` | Swap SWP-2026-000088 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000089` | Swap SWP-2026-000089 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000091` | Swap SWP-2026-000091 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000093` | Swap SWP-2026-000093 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000094` | Swap SWP-2026-000094 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000095` | Swap SWP-2026-000095 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000097` | Swap SWP-2026-000097 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000098` | Swap SWP-2026-000098 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000102` | Swap SWP-2026-000102 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000103` | Swap SWP-2026-000103 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000104` | Swap SWP-2026-000104 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000105` | Swap SWP-2026-000105 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000106` | Swap SWP-2026-000106 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000108` | Swap SWP-2026-000108 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000109` | Swap SWP-2026-000109 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000112` | Swap SWP-2026-000112 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000113` | Swap SWP-2026-000113 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000115` | Swap SWP-2026-000115 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000116` | Swap SWP-2026-000116 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000117` | Swap SWP-2026-000117 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000118` | Swap SWP-2026-000118 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000119` | Swap SWP-2026-000119 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000121` | Swap SWP-2026-000121 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000124` | Swap SWP-2026-000124 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000126` | Swap SWP-2026-000126 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000127` | Swap SWP-2026-000127 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000128` | Swap SWP-2026-000128 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000129` | Swap SWP-2026-000129 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000130` | Swap SWP-2026-000130 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000131` | Swap SWP-2026-000131 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000132` | Swap SWP-2026-000132 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000134` | Swap SWP-2026-000134 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000135` | Swap SWP-2026-000135 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000136` | Swap SWP-2026-000136 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000138` | Swap SWP-2026-000138 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000140` | Swap SWP-2026-000140 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000142` | Swap SWP-2026-000142 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000144` | Swap SWP-2026-000144 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000147` | Swap SWP-2026-000147 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000150` | Swap SWP-2026-000150 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000151` | Swap SWP-2026-000151 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000152` | Swap SWP-2026-000152 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000153` | Swap SWP-2026-000153 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000154` | Swap SWP-2026-000154 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000155` | Swap SWP-2026-000155 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000156` | Swap SWP-2026-000156 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000157` | Swap SWP-2026-000157 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000160` | Swap SWP-2026-000160 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000161` | Swap SWP-2026-000161 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000162` | Swap SWP-2026-000162 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000164` | Swap SWP-2026-000164 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000166` | Swap SWP-2026-000166 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000167` | Swap SWP-2026-000167 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000168` | Swap SWP-2026-000168 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000169` | Swap SWP-2026-000169 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000170` | Swap SWP-2026-000170 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000171` | Swap SWP-2026-000171 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000173` | Swap SWP-2026-000173 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000174` | Swap SWP-2026-000174 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000175` | Swap SWP-2026-000175 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000176` | Swap SWP-2026-000176 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000177` | Swap SWP-2026-000177 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000179` | Swap SWP-2026-000179 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000180` | Swap SWP-2026-000180 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000182` | Swap SWP-2026-000182 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000185` | Swap SWP-2026-000185 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000186` | Swap SWP-2026-000186 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000187` | Swap SWP-2026-000187 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000189` | Swap SWP-2026-000189 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000191` | Swap SWP-2026-000191 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000192` | Swap SWP-2026-000192 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000193` | Swap SWP-2026-000193 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000195` | Swap SWP-2026-000195 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000196` | Swap SWP-2026-000196 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000197` | Swap SWP-2026-000197 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000198` | Swap SWP-2026-000198 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-000200` | Swap SWP-2026-000200 has APPLIED status but lacks required manager authorization signoff |
| `RULE_SWAP_REQUIRES_MANAGER_APPROVAL` | `ANOMALY_DETECTED` | SwapRequest | `SWP-2026-999001` | Swap SWP-2026-999001 has APPLIED status but lacks required manager authorization signoff |
