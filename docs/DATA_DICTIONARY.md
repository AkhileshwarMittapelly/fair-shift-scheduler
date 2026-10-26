# Fair Shift Scheduler — Data Dictionary & Entity Catalog
*Comprehensive schema definition for automated workforce scheduling, compliance, and labor optimization.*
*Complies with Step 1 of the Technical Specification.*

---

## 1. Entity Relationship & Cardinality Overview

| Primary Entity | Related Entity | Cardinality | Relationship Nature & FK |
| :--- | :--- | :--- | :--- |
| **Team** | **Employee** | `1 : N` | `Employee.team_id -> Team.team_id` |
| **Team** | **Employee** (Manager) | `1 : 1` (Optional) | `Team.manager_id -> Employee.employee_id` |
| **Employee** | **Skill** | `N : M` | Bridge table: `EmployeeSkill` |
| **ShiftTemplate** | **ShiftAssignment**| `1 : N` | `ShiftAssignment.shift_template_id -> ShiftTemplate.shift_template_id` |
| **Employee** | **ShiftAssignment**| `1 : N` | `ShiftAssignment.employee_id -> Employee.employee_id` |
| **Team** | **CoverageRequirement**| `1 : N` | `CoverageRequirement.team_id -> Team.team_id` |
| **Employee** | **LeaveRequest** | `1 : N` | `LeaveRequest.employee_id -> Employee.employee_id` |
| **Employee** | **LeaveRequest** (Approver)| `1 : N` (Optional) | `LeaveRequest.decision_by -> Employee.employee_id` |
| **ShiftAssignment**| **SwapRequest** | `1 : 1` (Requester) | `SwapRequest.requester_assignment_id -> ShiftAssignment.assignment_id` |
| **ShiftAssignment**| **SwapRequest** | `1 : 1` (Target) | `SwapRequest.target_assignment_id -> ShiftAssignment.assignment_id` |
| **Employee** | **AttendanceEvent**| `1 : N` | `AttendanceEvent.employee_id -> Employee.employee_id` |
| **ShiftAssignment**| **AttendanceEvent**| `1 : N` (Optional) | `AttendanceEvent.assignment_id -> ShiftAssignment.assignment_id` |

---

## 2. Granular Field Specifications

### 2.1. `Team` (Parent Master Entity)
Represents an operational organizational unit (e.g. ICU Squad, Emergency Medicine, DevOps Team).

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `team_id` | `VARCHAR(16)` | Required | Format: `^TEAM-[0-9]{3}$` | Alphanumeric | **PK (Unique)** | Must be immutable, zero-padded 3 digits. |
| `team_name` | `VARCHAR(128)` | Required | Non-empty string | Text | Non-unique | Length between 3 and 128 characters. |
| `department` | `VARCHAR(64)` | Required | Non-empty string | Text | Non-unique | Valid department classification. |
| `manager_id` | `VARCHAR(16)` | Optional | Valid `employee_id` | Alphanumeric | Non-unique | FK to `Employee.employee_id` or `NULL`. |
| `location` | `VARCHAR(128)` | Required | Facility/Hub location | Text | Non-unique | Valid facility site name. |
| `max_overtime_hours_per_week` | `DECIMAL(4,1)` | Required | `0.0` to `24.0` | Hours | Non-unique | Default `12.0`. Must be `>= 0.0`. |
| `created_at` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | Valid ISO 8601 timestamp string. |

---

### 2.2. `Skill` (Parent Master Entity)
Defines specialized medical, technical, or operational qualifications required for shift coverage.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `skill_id` | `VARCHAR(16)` | Required | Format: `^SKILL-[0-9]{2}$` | Alphanumeric | **PK (Unique)** | Must be immutable, zero-padded 2 digits. |
| `skill_name` | `VARCHAR(64)` | Required | Non-empty string | Text | Unique | Standard skill title (e.g. Trauma & Acute Triage). |
| `category` | `ENUM` | Required | `CLINICAL`, `TECHNICAL`, `OPERATIONAL`, `SAFETY`, `MANAGEMENT` | Enum | Non-unique | Must belong to declared enum. |
| `minimum_certification_level` | `ENUM` | Required | `JUNIOR`, `MID`, `SENIOR`, `LEAD` | Enum | Non-unique | Must belong to declared proficiency levels. |
| `description` | `TEXT` | Required | Detailed description | Text | Non-unique | Minimum length 10 characters. |

---

### 2.3. `Employee` (Master Entity)
Core workforce record tracking labor terms, contract hours, and statutory overtime ceilings.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `employee_id` | `VARCHAR(16)` | Required | Format: `^EMP-[0-9]{6}$` | Alphanumeric | **PK (Unique)** | Zero-padded 6 digits (e.g. `EMP-000001`). Immutable. |
| `first_name` | `VARCHAR(64)` | Required | Alpha characters | Text | Non-unique | 1 to 64 letters. |
| `last_name` | `VARCHAR(64)` | Required | Alpha characters | Text | Non-unique | 1 to 64 letters. |
| `email` | `VARCHAR(128)` | Required | Valid RFC 5322 email | Text | **Unique** | Format: `{first}.{last}.{id}@workforce.internal`. |
| `team_id` | `VARCHAR(16)` | Required | Valid `team_id` | Alphanumeric | Non-unique | **FK** -> `Team.team_id`. |
| `hire_date` | `DATE` | Required | `YYYY-MM-DD` | Calendar Date | Non-unique | Past or present date (`<= current_date`). |
| `contract_hours_per_week` | `DECIMAL(4,1)`| Required | `20.0`, `32.0`, `40.0` | Hours/Week | Non-unique | Standard contracted base hours. Must be `> 0`. |
| `max_weekly_overtime_hours` | `DECIMAL(4,1)`| Required | `0.0` to `20.0` | Hours/Week | Non-unique | Statutory maximum overtime cap (Default: `12.0`). |
| `hourly_rate` | `DECIMAL(6,2)`| Required | `15.00` to `150.00` | USD ($) | Non-unique | Positive currency amount. |
| `employment_status` | `ENUM` | Required | `ACTIVE`, `ON_LEAVE`, `TERMINATED` | Enum | Non-unique | Must match valid `EmploymentStatus`. |
| `created_at` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | Standard audit timestamp. |

---

### 2.4. `EmployeeSkill` (Bridge Entity: N to M)
Associates employees with verified skills and tracking certification expiration dates.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `employee_skill_id` | `VARCHAR(48)` | Required | Format: `^ES-EMP-[0-9]{6}-SKILL-[0-9]{2}$` | Alphanumeric | **PK (Unique)** | Derived composite ID. |
| `employee_id` | `VARCHAR(16)` | Required | Valid `employee_id` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. |
| `skill_id` | `VARCHAR(16)` | Required | Valid `skill_id` | Alphanumeric | Non-unique | **FK** -> `Skill.skill_id`. |
| `proficiency_level` | `ENUM` | Required | `JUNIOR`, `MID`, `SENIOR`, `LEAD` | Enum | Non-unique | Must belong to `ProficiencyLevel`. |
| `certified_date` | `DATE` | Required | `YYYY-MM-DD` | Calendar Date | Non-unique | Must be `>= Employee.hire_date`. |
| `expiry_date` | `DATE` | Optional | `YYYY-MM-DD` | Calendar Date | Non-unique | If present, must be `> certified_date`. |

*(Constraint: Composite `(employee_id, skill_id)` must be unique).*

---

### 2.5. `ShiftTemplate` (Master Entity)
Defines recurring operational shifts with differential pay multipliers and overnight flags.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shift_template_id` | `VARCHAR(16)` | Required | `TMPL-MORN`, `TMPL-AFTN`, `TMPL-NGHT` | Alphanumeric | **PK (Unique)** | Standard template code identifier. |
| `shift_code` | `ENUM` | Required | `A` (Morning), `B` (Afternoon), `C` (Night) | Enum | **Unique** | Conforms to single-letter code convention. |
| `shift_name` | `VARCHAR(64)` | Required | Non-empty string | Text | Unique | Descriptive shift title. |
| `start_time` | `VARCHAR(5)` | Required | `HH:MM` (e.g. `07:00`, `15:00`, `23:00`) | 24-hr Time | Non-unique | Standard 24-hour military format. |
| `end_time` | `VARCHAR(5)` | Required | `HH:MM` (e.g. `15:30`, `23:30`, `07:30`) | 24-hr Time | Non-unique | Standard 24-hour military format. |
| `duration_hours` | `DECIMAL(3,1)`| Required | `8.0` | Hours | Non-unique | Must equal `(end_time - start_time)`. |
| `is_overnight` | `BOOLEAN` | Required | `TRUE`, `FALSE` | Boolean | Non-unique | `TRUE` if end time is on following calendar day. |
| `differential_rate_multiplier` | `DECIMAL(3,2)` | Required | `1.00`, `1.15`, `1.25` | Multiplier | Non-unique | Must be `>= 1.00`. |

---

### 2.6. `HolidayCalendar` (Master Reference Entity)
Designates statutory regional and mandatory public holidays.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `holiday_id` | `VARCHAR(16)` | Required | Format: `^HOL-[0-9]{4}-[0-9]{3}$` | Alphanumeric | **PK (Unique)** | Zero-padded sequence (e.g. `HOL-2026-001`). |
| `holiday_date` | `DATE` | Required | `YYYY-MM-DD` | Calendar Date | Non-unique | Valid calendar date. |
| `holiday_name` | `VARCHAR(64)` | Required | Non-empty string | Text | Non-unique | Statutory holiday title. |
| `region` | `VARCHAR(32)` | Required | `GLOBAL`, `US`, `US-WEST`, `EU` | Text | Non-unique | Geographic operational jurisdiction. |
| `is_mandatory_off` | `BOOLEAN` | Required | `TRUE`, `FALSE` | Boolean | Non-unique | If `TRUE`, non-emergency staffing minimized. |

---

### 2.7. `CoverageRequirement` (Operational Planning Entity)
Establishes minimum and target staffing demand per date, shift, team, and specialized skill.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `requirement_id` | `VARCHAR(20)` | Required | Format: `^COV-[0-9]{4}-[0-9]{6}$` | Alphanumeric | **PK (Unique)** | Deterministic sequential code. |
| `date` | `DATE` | Required | `YYYY-MM-DD` | Calendar Date | Non-unique | Within scheduling operational horizon. |
| `shift_template_id` | `VARCHAR(16)` | Required | Valid `shift_template_id` | Alphanumeric | Non-unique | **FK** -> `ShiftTemplate.shift_template_id`. |
| `team_id` | `VARCHAR(16)` | Required | Valid `team_id` | Alphanumeric | Non-unique | **FK** -> `Team.team_id`. |
| `skill_id` | `VARCHAR(16)` | Optional | Valid `skill_id` or `NULL` | Alphanumeric | Non-unique | **FK** -> `Skill.skill_id` (if skill-specific). |
| `min_headcount` | `INTEGER` | Required | `1` to `20` | Headcount | Non-unique | Mandatory floor. Must be `>= 1`. |
| `target_headcount` | `INTEGER` | Required | `1` to `25` | Headcount | Non-unique | Must satisfy `target_headcount >= min_headcount`. |
| `priority_weight` | `DECIMAL(3,1)`| Required | `1.0` (standard) to `2.0` (critical) | Scalar Weight | Non-unique | Soft optimizer penalty multiplier. |

---

### 2.8. `LeaveRequest` (Transaction Entity)
Represents employee PTO, acute sick, parental, or bereavement leave with approval lifecycle states.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `leave_id` | `VARCHAR(20)` | Required | Format: `^LVE-[0-9]{4}-[0-9]{6}$` | Alphanumeric | **PK (Unique)** | Immutable zero-padded ID (e.g. `LVE-2026-000001`). |
| `employee_id` | `VARCHAR(16)` | Required | Valid `employee_id` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. |
| `start_date` | `DATE` | Required | `YYYY-MM-DD` | Calendar Date | Non-unique | Chronological date. |
| `end_date` | `DATE` | Required | `YYYY-MM-DD` | Calendar Date | Non-unique | Must satisfy `end_date >= start_date`. |
| `leave_type` | `ENUM` | Required | `ANNUAL`, `SICK`, `BEREAVEMENT`, `PARENTAL`, `COMPENSATORY`, `UNPAID` | Enum | Non-unique | Valid `LeaveType` enum. |
| `status` | `ENUM` | Required | `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED` | Enum | Non-unique | Valid `LeaveStatus` lifecycle state. |
| `reason` | `VARCHAR(255)`| Required | Non-empty string | Text | Non-unique | Justification text. |
| `decision_by` | `VARCHAR(16)` | Optional | Valid `employee_id` or `NULL` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. Required if `APPROVED` or `REJECTED`. |
| `decision_timestamp`| `TIMESTAMP` | Optional | ISO 8601 UTC or `NULL` | UTC Timestamp | Non-unique | Populated upon approval/rejection. |
| `decision_notes` | `TEXT` | Optional | Manager/HR comments | Text | Non-unique | Explanatory note for decision auditability. |

---

### 2.9. `ShiftAssignment` (Core Transaction / Operational Entity)
Represents an individual rostered shift for an employee meeting coverage constraints.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assignment_id` | `VARCHAR(32)` | Required | Format: `^SHIFT-[0-9]{4}-[0-9]{2}-[0-9]{2}-[A-C]-[0-9]{6}$` | Alphanumeric | **PK (Unique)** | Conforms to `SHIFT-YYYY-MM-DD-<Code>-<Seq>` convention. |
| `date` | `DATE` | Required | `YYYY-MM-DD` | Calendar Date | Non-unique | Must match date component of `assignment_id`. |
| `shift_template_id` | `VARCHAR(16)` | Required | Valid `shift_template_id` | Alphanumeric | Non-unique | **FK** -> `ShiftTemplate.shift_template_id`. |
| `employee_id` | `VARCHAR(16)` | Required | Valid `employee_id` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. |
| `team_id` | `VARCHAR(16)` | Required | Valid `team_id` | Alphanumeric | Non-unique | **FK** -> `Team.team_id`. |
| `role_skill_id` | `VARCHAR(16)` | Optional | Valid `skill_id` or `NULL` | Alphanumeric | Non-unique | **FK** -> `Skill.skill_id`. |
| `scheduled_start` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | Start timestamp. |
| `scheduled_end` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | End timestamp. Must be `> scheduled_start`. |
| `status` | `ENUM` | Required | `SCHEDULED`, `COMPLETED`, `SWAPPED`, `ABSENT`, `CANCELLED` | Enum | Non-unique | Valid `AssignmentStatus` enum. |
| `created_at` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | Creation audit timestamp. |
| `created_by` | `VARCHAR(32)` | Required | `SYSTEM_SOLVER`, `MANAGER`, `ANOMALY_INJECTION` | Text | Non-unique | Provenance origin tag. |

---

### 2.10. `SwapRequest` (Transactional Event Entity)
Peer-to-peer shift exchange transaction preserving lifecycle audit trail and manager authorization.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `swap_id` | `VARCHAR(20)` | Required | Format: `^SWP-[0-9]{4}-[0-9]{6}$` | Alphanumeric | **PK (Unique)** | Deterministic zero-padded sequence. |
| `requester_assignment_id`| `VARCHAR(32)`| Required | Valid `assignment_id` | Alphanumeric | Non-unique | **FK** -> `ShiftAssignment.assignment_id`. |
| `target_assignment_id` | `VARCHAR(32)`| Required | Valid `assignment_id` | Alphanumeric | Non-unique | **FK** -> `ShiftAssignment.assignment_id`. Must `!= requester_assignment_id`. |
| `requester_employee_id` | `VARCHAR(16)`| Required | Valid `employee_id` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. |
| `target_employee_id` | `VARCHAR(16)`| Required | Valid `employee_id` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. Must `!= requester_employee_id`. |
| `status` | `ENUM` | Required | `PENDING_PEER`, `PENDING_MANAGER`, `APPROVED`, `REJECTED`, `APPLIED`, `CANCELLED` | Enum | Non-unique | Valid `SwapStatus` lifecycle state. |
| `requested_at` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | Submission timestamp. |
| `peer_agreed_at` | `TIMESTAMP` | Optional | ISO 8601 UTC or `NULL` | UTC Timestamp | Non-unique | If populated, must be `>= requested_at`. |
| `manager_decision_by` | `VARCHAR(16)` | Optional | Valid `employee_id` or `NULL` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. Mandatory for `APPLIED` status. |
| `manager_decision_at` | `TIMESTAMP` | Optional | ISO 8601 UTC or `NULL` | UTC Timestamp | Non-unique | If populated, must be `>= peer_agreed_at`. |
| `decision_notes` | `TEXT` | Optional | Authorization or rejection note | Text | Non-unique | Audit log comments. |

---

### 2.11. `AttendanceEvent` (Telemetry / Physical Punch Entity)
Time-and-attendance punch events capturing clock-in, clock-out, and reconciliation diffs.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `attendance_id` | `VARCHAR(64)` | Required | Format: `^ATT-EMP-[0-9]{6}-[0-9]{8}T[0-9]{6}$` | Alphanumeric | **PK (Unique)** | Conforms to `ATT-<employee-id>-<timestamp>` convention. |
| `employee_id` | `VARCHAR(16)` | Required | Valid `employee_id` | Alphanumeric | Non-unique | **FK** -> `Employee.employee_id`. |
| `assignment_id` | `VARCHAR(32)` | Optional | Valid `assignment_id` or `NULL` | Alphanumeric | Non-unique | **FK** -> `ShiftAssignment.assignment_id`. |
| `event_type` | `ENUM` | Required | `CLOCK_IN`, `CLOCK_OUT`, `BREAK_START`, `BREAK_END` | Enum | Non-unique | Valid `AttendanceEventType`. |
| `event_timestamp` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | Actual terminal punch timestamp. |
| `source_device` | `VARCHAR(64)` | Required | Device identifier | Text | Non-unique | Physical terminal / badge reader ID. |
| `matched_schedule_diff_minutes`| `DECIMAL(5,1)`| Required | `-120.0` to `+240.0` | Minutes | Non-unique | Derived variance: `actual_timestamp - scheduled_time`. |

---

### 2.12. `GroundTruthAnomaly` (Evaluation / Oracle Entity)
Isolated evaluation ground truth catalogue recording deliberate edge cases and expected violations.

| Field Name | Type | Req/Opt | Allowed Values | Units | Uniqueness | Validation Rule |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `anomaly_id` | `VARCHAR(16)` | Required | Format: `^GT-[0-9]{6}$` | Alphanumeric | **PK (Unique)** | Deterministic oracle identifier. |
| `anomaly_type` | `ENUM` | Required | `EMPLOYEE_DOUBLE_BOOKED`, `APPROVED_LEAVE_OVERLAPS_SHIFT`, `REQUIRED_SKILL_ABSENT`, `OVERTIME_CAP_EXCEEDED`, `SWAP_APPLIED_WITHOUT_APPROVAL` | Enum | Non-unique | Must belong to `AnomalyType`. |
| `entity_type` | `VARCHAR(32)` | Required | Entity table name | Text | Non-unique | Name of impacted table. |
| `primary_entity_id` | `VARCHAR(32)` | Required | Impacted PK | Alphanumeric | Non-unique | Exact ID of corrupted or anomalous record. |
| `secondary_entity_id`| `VARCHAR(32)`| Optional | Conflicting PK or `NULL` | Alphanumeric | Non-unique | Related record creating conflict. |
| `description` | `TEXT` | Required | Plain English description | Text | Non-unique | Detailed anomaly narrative. |
| `injected_timestamp` | `TIMESTAMP` | Required | ISO 8601 UTC | UTC Timestamp | Non-unique | Deterministic benchmark timestamp. |
| `severity` | `ENUM` | Required | `CRITICAL`, `HIGH`, `MEDIUM` | Enum | Non-unique | Risk rating. |
| `expected_detection_rule`| `VARCHAR(64)`| Required | Machine rule code | Text | Non-unique | E.g. `RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS`. |
