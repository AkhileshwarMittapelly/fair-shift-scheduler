# Fair Shift Scheduler — REST API Specification

Base URL: `http://localhost:8000/api`

---

## 1. System & Health

### `GET /api/health`
Returns service status and UTC timestamp.
```json
{
  "status": "HEALTHY",
  "timestamp": "2026-10-26T16:00:00Z"
}
```

### `GET /api/metrics`
Aggregated workforce and operational KPIs.
```json
{
  "scale": "starter",
  "seed": 20261022,
  "total_employees": 100,
  "total_teams": 10,
  "total_shifts": 613,
  "total_scheduled_hours": 4840.0,
  "total_overtime_hours": 20.0,
  "total_leaves": 150,
  "approved_leaves": 128,
  "total_ground_truth_anomalies": 5,
  "detected_anomalies": 5,
  "detection_precision": 1.0,
  "detection_recall": 1.0,
  "detection_f1_score": 1.0
}
```

---

## 2. Workforce & Master Data

### `GET /api/teams`
Lists all operational squads and department classifications.

### `GET /api/skills`
Lists the catalog of 10 specialized medical and technical skills with minimum proficiency levels.

### `GET /api/employees`
Query Parameters:
- `team_id`: Filter by team.
- `search`: Case-insensitive search on name or ID.
- `limit`: Pagination limit (default: 100).

---

## 3. Rostering & Shift Management

### `GET /api/shifts`
Query Parameters:
- `date`: Filter by calendar date (`YYYY-MM-DD`).
- `team_id`: Filter by team.
- `employee_id`: Filter by employee.

### `GET /api/coverage`
Lists coverage requirements and minimum staffing per shift.

---

## 4. Leaves & Absences

### `GET /api/leaves`
Query Parameters:
- `employee_id`: Filter by employee.
- `status`: `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`.

### `POST /api/leaves/create`
Submits a new employee leave request.
```json
{
  "employee_id": "EMP-000002",
  "start_date": "2026-01-10",
  "end_date": "2026-01-12",
  "leave_type": "ANNUAL",
  "reason": "Family vacation"
}
```

### `POST /api/leaves/{leave_id}/decide`
Processes a leave application (Manager / HR action).
```json
{
  "decision": "APPROVED",
  "decision_by": "EMP-000001",
  "decision_notes": "Approved within squad quota"
}
```

---

## 5. Shift Swaps

### `GET /api/swaps`
Lists all peer-to-peer shift swap transactions.

### `POST /api/swaps/request`
Initiates a peer swap between two shift assignments.
```json
{
  "requester_assignment_id": "SHIFT-2026-01-05-A-000012",
  "target_assignment_id": "SHIFT-2026-01-05-B-000024"
}
```

### `POST /api/swaps/{swap_id}/decide`
Authorizes, rejects, or executes a shift swap.
```json
{
  "decision": "APPLIED",
  "decision_by": "EMP-000001",
  "decision_notes": "Skills and rest constraints verified"
}
```

---

## 6. Optimization & Solver

### `POST /api/scheduler/run`
Executes the heuristic constraint optimizer to schedule unfulfilled requirements and balance hours.
Response includes:
- `is_feasible`: Boolean
- `metrics`: Fulfillment rate, Gini coefficient, night/weekend equity
- `sample_decisions`: Traceability decision logs explaining candidate selections.

---

## 7. Data Quality & Step 10 Verification

### `GET /api/validation/report`
Executes the 8-point validator live and calculates benchmark precision/recall against ground truth.

### `POST /api/generator/run`
Dynamically triggers data generation with scale (`starter` or `full`) and fixed seed.

### `GET /api/reproducibility/verify`
Runs dual generation with identical seed and returns bit-for-bit SHA-256 checksum comparisons across all tables.
