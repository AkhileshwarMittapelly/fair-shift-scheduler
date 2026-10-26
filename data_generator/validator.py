"""
Comprehensive 8-Point Validation Engine & Anomaly Detector.
Implements Step 8 of the specification, reconciling all rules,
verifying FK/PK integrity, date ordering, arithmetic, lifecycle transitions,
and benchmarking against ground truth anomalies (Precision, Recall, F1).
"""

from __future__ import annotations
import datetime
from typing import List, Dict, Any, Set, Tuple
from dataclasses import dataclass, asdict

from .models import (
    EmploymentStatus,
    SkillCategory,
    ProficiencyLevel,
    ShiftCode,
    LeaveType,
    LeaveStatus,
    AssignmentStatus,
    SwapStatus,
    AttendanceEventType,
    AnomalyType,
    Skill,
    Team,
    Employee,
    EmployeeSkill,
    HolidayCalendar,
    ShiftTemplate,
    CoverageRequirement,
    LeaveRequest,
    ShiftAssignment,
    SwapRequest,
    AttendanceEvent,
    GroundTruthAnomaly,
)
from .generator import GeneratedDataset


@dataclass
class ValidationIssue:
    check_name: str
    severity: str  # "ERROR", "WARNING", "ANOMALY_DETECTED"
    entity_type: str
    entity_id: str
    message: str
    rule_code: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    is_valid: bool
    summary: Dict[str, Any]
    structural_integrity: Dict[str, bool]
    detected_rule_violations: List[ValidationIssue]
    ground_truth_evaluation: Dict[str, Any]
    detailed_issues: List[ValidationIssue]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "summary": self.summary,
            "structural_integrity": self.structural_integrity,
            "detected_rule_violations": [v.to_dict() for v in self.detected_rule_violations],
            "ground_truth_evaluation": self.ground_truth_evaluation,
            "detailed_issues": [i.to_dict() for i in self.detailed_issues],
        }


class DatasetValidator:
    """
    Validates synthetic datasets across 8 dimensions + evaluates anomaly detection against ground truth.
    """

    def __init__(self, dataset: GeneratedDataset):
        self.dataset = dataset
        self.issues: List[ValidationIssue] = []
        self.detected_anomalies: List[ValidationIssue] = []

    def validate(self) -> ValidationReport:
        """
        Executes all 8 validation checks and compares results with ground truth.
        """
        # 1. Primary Key Uniqueness
        pk_ok = self._check_pk_uniqueness()

        # 2. Foreign Key Integrity
        fk_ok = self._check_foreign_key_integrity()

        # 3. Allowed Enums
        enum_ok = self._check_allowed_enums()

        # 4. Date & Timestamp Ordering
        date_ok = self._check_date_ordering()

        # 5. Arithmetic & Schedule Reconciliation
        arith_ok = self._check_arithmetic_reconciliation()

        # 6. Lifecycle Transitions
        life_ok = self._check_lifecycle_transitions()

        # 7. Duplicate Checks
        dup_ok = self._check_duplicate_relationships()

        # 8. Business Constraint Violations (Edge cases / negative scenarios)
        self._detect_business_rule_violations()

        # Benchmark detected violations vs ground truth
        gt_eval = self._evaluate_ground_truth()

        structural_valid = pk_ok and fk_ok and enum_ok and date_ok and arith_ok and dup_ok

        summary = {
            "pk_uniqueness": pk_ok,
            "foreign_key_integrity": fk_ok,
            "allowed_enums": enum_ok,
            "date_ordering": date_ok,
            "arithmetic_reconciliation": arith_ok,
            "lifecycle_transitions": life_ok,
            "duplicate_checks": dup_ok,
            "total_issues_logged": len(self.issues),
            "total_anomalies_detected": len(self.detected_anomalies),
            "ground_truth_count": len(self.dataset.ground_truth_anomalies),
            "detection_precision": gt_eval["precision"],
            "detection_recall": gt_eval["recall"],
            "detection_f1_score": gt_eval["f1_score"],
        }

        structural_integrity = {
            "pk_uniqueness": pk_ok,
            "foreign_key_integrity": fk_ok,
            "allowed_enums": enum_ok,
            "date_ordering": date_ok,
            "arithmetic_reconciliation": arith_ok,
            "duplicate_checks": dup_ok,
        }

        return ValidationReport(
            is_valid=structural_valid,
            summary=summary,
            structural_integrity=structural_integrity,
            detected_rule_violations=self.detected_anomalies,
            ground_truth_evaluation=gt_eval,
            detailed_issues=self.issues,
        )

    # -------------------------------------------------------------------------
    # Check 1: Primary Key Uniqueness
    # -------------------------------------------------------------------------
    def _check_pk_uniqueness(self) -> bool:
        passed = True
        tables = [
            ("Employee", [e.employee_id for e in self.dataset.employees]),
            ("Team", [t.team_id for t in self.dataset.teams]),
            ("Skill", [s.skill_id for s in self.dataset.skills]),
            ("EmployeeSkill", [es.employee_skill_id for es in self.dataset.employee_skills]),
            ("ShiftTemplate", [st.shift_template_id for st in self.dataset.shift_templates]),
            ("HolidayCalendar", [h.holiday_id for h in self.dataset.holiday_calendar]),
            ("CoverageRequirement", [c.requirement_id for c in self.dataset.coverage_requirements]),
            ("LeaveRequest", [l.leave_id for l in self.dataset.leave_requests]),
            ("ShiftAssignment", [a.assignment_id for a in self.dataset.shift_assignments]),
            ("SwapRequest", [s.swap_id for s in self.dataset.swap_requests]),
            ("AttendanceEvent", [att.attendance_id for att in self.dataset.attendance_events]),
        ]

        for table_name, ids in tables:
            seen = set()
            duplicates = set()
            for x in ids:
                if x in seen:
                    duplicates.add(x)
                seen.add(x)

            if duplicates:
                passed = False
                for d in list(duplicates)[:5]:
                    self.issues.append(
                        ValidationIssue(
                            check_name="PK_UNIQUENESS",
                            severity="ERROR",
                            entity_type=table_name,
                            entity_id=d,
                            message=f"Duplicate Primary Key detected in {table_name}: {d}",
                            rule_code="RULE_PK_UNIQUENESS",
                        )
                    )
        return passed

    # -------------------------------------------------------------------------
    # Check 2: Foreign Key Referential Integrity
    # -------------------------------------------------------------------------
    def _check_foreign_key_integrity(self) -> bool:
        passed = True
        emp_ids = {e.employee_id for e in self.dataset.employees}
        team_ids = {t.team_id for t in self.dataset.teams}
        skill_ids = {s.skill_id for s in self.dataset.skills}
        tmpl_ids = {st.shift_template_id for st in self.dataset.shift_templates}
        asgn_ids = {a.assignment_id for a in self.dataset.shift_assignments}

        # Employee -> Team
        for emp in self.dataset.employees:
            if emp.team_id not in team_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="Employee",
                        entity_id=emp.employee_id,
                        message=f"Foreign key violation: team_id {emp.team_id} does not exist in Team",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        # Team -> Manager (Employee)
        for team in self.dataset.teams:
            if team.manager_id and team.manager_id not in emp_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="Team",
                        entity_id=team.team_id,
                        message=f"Foreign key violation: manager_id {team.manager_id} does not exist in Employee",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        # EmployeeSkill -> Employee & Skill
        for es in self.dataset.employee_skills:
            if es.employee_id not in emp_ids or es.skill_id not in skill_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="EmployeeSkill",
                        entity_id=es.employee_skill_id,
                        message=f"Foreign key violation in EmployeeSkill {es.employee_skill_id}",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        # CoverageRequirement -> Team, ShiftTemplate, Skill
        for req in self.dataset.coverage_requirements:
            if req.team_id not in team_ids or req.shift_template_id not in tmpl_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="CoverageRequirement",
                        entity_id=req.requirement_id,
                        message=f"Foreign key violation in CoverageRequirement {req.requirement_id}",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )
            if req.skill_id and req.skill_id not in skill_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="CoverageRequirement",
                        entity_id=req.requirement_id,
                        message=f"Invalid skill_id in CoverageRequirement {req.requirement_id}",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        # LeaveRequest -> Employee
        for lr in self.dataset.leave_requests:
            if lr.employee_id not in emp_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="LeaveRequest",
                        entity_id=lr.leave_id,
                        message=f"Foreign key violation in LeaveRequest {lr.leave_id}: employee {lr.employee_id} not found",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        # ShiftAssignment -> Employee, Team, ShiftTemplate, Skill
        for asgn in self.dataset.shift_assignments:
            if asgn.employee_id not in emp_ids or asgn.team_id not in team_ids or asgn.shift_template_id not in tmpl_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="ShiftAssignment",
                        entity_id=asgn.assignment_id,
                        message=f"Foreign key violation in ShiftAssignment {asgn.assignment_id}",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )
            if asgn.role_skill_id and asgn.role_skill_id not in skill_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="ShiftAssignment",
                        entity_id=asgn.assignment_id,
                        message=f"Invalid role_skill_id {asgn.role_skill_id} in ShiftAssignment",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        # SwapRequest -> ShiftAssignment & Employee
        for swp in self.dataset.swap_requests:
            if swp.requester_assignment_id not in asgn_ids or swp.target_assignment_id not in asgn_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="SwapRequest",
                        entity_id=swp.swap_id,
                        message=f"Foreign key violation in SwapRequest {swp.swap_id}: assignment not found",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        # AttendanceEvent -> Employee & ShiftAssignment
        for att in self.dataset.attendance_events:
            if att.employee_id not in emp_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="AttendanceEvent",
                        entity_id=att.attendance_id,
                        message=f"Foreign key violation in AttendanceEvent {att.attendance_id}",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )
            if att.assignment_id and att.assignment_id not in asgn_ids:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        check_name="FK_INTEGRITY",
                        severity="ERROR",
                        entity_type="AttendanceEvent",
                        entity_id=att.attendance_id,
                        message=f"Invalid assignment_id {att.assignment_id} in AttendanceEvent",
                        rule_code="RULE_FK_INTEGRITY",
                    )
                )

        return passed

    # -------------------------------------------------------------------------
    # Check 3: Allowed Enum Values
    # -------------------------------------------------------------------------
    def _check_allowed_enums(self) -> bool:
        passed = True
        for emp in self.dataset.employees:
            if emp.employment_status not in EmploymentStatus.__members__.values():
                passed = False
                self.issues.append(ValidationIssue("ENUM_VALIDATION", "ERROR", "Employee", emp.employee_id, f"Invalid status: {emp.employment_status}", "RULE_ENUM_VALIDATION"))

        for lr in self.dataset.leave_requests:
            if lr.leave_type not in LeaveType.__members__.values() or lr.status not in LeaveStatus.__members__.values():
                passed = False
                self.issues.append(ValidationIssue("ENUM_VALIDATION", "ERROR", "LeaveRequest", lr.leave_id, f"Invalid leave enum", "RULE_ENUM_VALIDATION"))

        for sa in self.dataset.shift_assignments:
            if sa.status not in AssignmentStatus.__members__.values():
                passed = False
                self.issues.append(ValidationIssue("ENUM_VALIDATION", "ERROR", "ShiftAssignment", sa.assignment_id, f"Invalid assignment status: {sa.status}", "RULE_ENUM_VALIDATION"))

        for sw in self.dataset.swap_requests:
            if sw.status not in SwapStatus.__members__.values():
                passed = False
                self.issues.append(ValidationIssue("ENUM_VALIDATION", "ERROR", "SwapRequest", sw.swap_id, f"Invalid swap status: {sw.status}", "RULE_ENUM_VALIDATION"))

        return passed

    # -------------------------------------------------------------------------
    # Check 4: Date & Timestamp Ordering
    # -------------------------------------------------------------------------
    def _check_date_ordering(self) -> bool:
        passed = True
        for lr in self.dataset.leave_requests:
            try:
                sd = datetime.date.fromisoformat(lr.start_date)
                ed = datetime.date.fromisoformat(lr.end_date)
                if sd > ed:
                    passed = False
                    self.issues.append(
                        ValidationIssue(
                            "DATE_ORDERING", "ERROR", "LeaveRequest", lr.leave_id,
                            f"start_date {lr.start_date} is after end_date {lr.end_date}", "RULE_DATE_CHRONOLOGY"
                        )
                    )
            except ValueError as e:
                passed = False
                self.issues.append(ValidationIssue("DATE_FORMAT", "ERROR", "LeaveRequest", lr.leave_id, str(e), "RULE_DATE_FORMAT"))

        for sa in self.dataset.shift_assignments:
            try:
                st = datetime.datetime.fromisoformat(sa.scheduled_start.replace("Z", "+00:00"))
                et = datetime.datetime.fromisoformat(sa.scheduled_end.replace("Z", "+00:00"))
                if st >= et:
                    passed = False
                    self.issues.append(
                        ValidationIssue(
                            "TIMESTAMP_ORDERING", "ERROR", "ShiftAssignment", sa.assignment_id,
                            f"scheduled_start {sa.scheduled_start} not earlier than scheduled_end {sa.scheduled_end}", "RULE_DATE_CHRONOLOGY"
                        )
                    )
            except ValueError as e:
                passed = False
                self.issues.append(ValidationIssue("DATE_FORMAT", "ERROR", "ShiftAssignment", sa.assignment_id, str(e), "RULE_DATE_FORMAT"))

        return passed

    # -------------------------------------------------------------------------
    # Check 5: Arithmetic & Schedule Reconciliation
    # -------------------------------------------------------------------------
    def _check_arithmetic_reconciliation(self) -> bool:
        passed = True
        tmpl_map = {t.shift_template_id: t for t in self.dataset.shift_templates}
        asgn_map = {a.assignment_id: a for a in self.dataset.shift_assignments}

        # Check that shift templates specify 8.0h duration
        for tmpl in self.dataset.shift_templates:
            if tmpl.duration_hours <= 0:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        "ARITHMETIC_RECONCILIATION", "ERROR", "ShiftTemplate", tmpl.shift_template_id,
                        f"Non-positive duration: {tmpl.duration_hours}", "RULE_ARITHMETIC"
                    )
                )

        # Check attendance reconciliation with scheduled times
        for att in self.dataset.attendance_events:
            if att.assignment_id and att.assignment_id in asgn_map:
                asgn = asgn_map[att.assignment_id]
                ref_time_str = asgn.scheduled_start if att.event_type == AttendanceEventType.CLOCK_IN else asgn.scheduled_end
                ref_dt = datetime.datetime.fromisoformat(ref_time_str.replace("Z", "+00:00"))
                actual_dt = datetime.datetime.fromisoformat(att.event_timestamp.replace("Z", "+00:00"))
                diff_minutes = (actual_dt - ref_dt).total_seconds() / 60.0

                # Check if recorded matched_schedule_diff_minutes agrees within 1 minute precision
                if abs(diff_minutes - att.matched_schedule_diff_minutes) > 1.0:
                    passed = False
                    self.issues.append(
                        ValidationIssue(
                            "ARITHMETIC_RECONCILIATION", "ERROR", "AttendanceEvent", att.attendance_id,
                            f"Discrepancy in recorded punch variance: recorded {att.matched_schedule_diff_minutes} vs calculated {diff_minutes:.1f}",
                            "RULE_ARITHMETIC"
                        )
                    )

        return passed

    # -------------------------------------------------------------------------
    # Check 6: Lifecycle Transitions
    # -------------------------------------------------------------------------
    def _check_lifecycle_transitions(self) -> bool:
        passed = True
        for lr in self.dataset.leave_requests:
            if lr.status == LeaveStatus.PENDING and lr.decision_by is not None:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        "LIFECYCLE_TRANSITION", "ERROR", "LeaveRequest", lr.leave_id,
                        "Pending leave has decision_by populated prematurely", "RULE_LIFECYCLE"
                    )
                )
            if lr.status in (LeaveStatus.APPROVED, LeaveStatus.REJECTED) and not lr.decision_by:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        "LIFECYCLE_TRANSITION", "ERROR", "LeaveRequest", lr.leave_id,
                        f"Finalized leave {lr.leave_id} is missing decision_by authorizer", "RULE_LIFECYCLE"
                    )
                )

        return passed

    # -------------------------------------------------------------------------
    # Check 7: Duplicate Relationships
    # -------------------------------------------------------------------------
    def _check_duplicate_relationships(self) -> bool:
        passed = True
        es_pairs = set()
        for es in self.dataset.employee_skills:
            pair = (es.employee_id, es.skill_id)
            if pair in es_pairs:
                passed = False
                self.issues.append(
                    ValidationIssue(
                        "DUPLICATE_RELATIONSHIP", "ERROR", "EmployeeSkill", es.employee_skill_id,
                        f"Duplicate employee skill pair: {pair}", "RULE_DUPLICATE_CHECK"
                    )
                )
            es_pairs.add(pair)
        return passed

    # -------------------------------------------------------------------------
    # Check 8: Business Rule & Constraint Violation Detector
    # (Detects the 5 injected edge cases and flags any constraint anomalies)
    # -------------------------------------------------------------------------
    def _detect_business_rule_violations(self):
        """
        Detects:
        1. Employee Double-Booked
        2. Approved Leave Overlaps Assigned Shift
        3. Required Skill Absent
        4. Overtime Cap Exceeded
        5. Swap Applied Without Approval
        """
        emp_skill_set: Set[Tuple[str, str]] = {
            (es.employee_id, es.skill_id) for es in self.dataset.employee_skills
        }
        emp_map = {e.employee_id: e for e in self.dataset.employees}

        # 1. Detect Double Bookings
        emp_date_shifts: Dict[Tuple[str, str], List[ShiftAssignment]] = {}
        for sa in self.dataset.shift_assignments:
            if sa.status in (AssignmentStatus.SCHEDULED, AssignmentStatus.COMPLETED):
                key = (sa.employee_id, sa.date)
                if key not in emp_date_shifts:
                    emp_date_shifts[key] = []
                emp_date_shifts[key].append(sa)

        for (emp_id, date), shifts in emp_date_shifts.items():
            if len(shifts) > 1:
                # Double-booked!
                primary_id = shifts[0].assignment_id
                sec_id = shifts[1].assignment_id
                self.detected_anomalies.append(
                    ValidationIssue(
                        check_name="DOUBLE_BOOKING_DETECTION",
                        severity="ANOMALY_DETECTED",
                        entity_type="ShiftAssignment",
                        entity_id=primary_id,
                        message=f"Employee {emp_id} double-booked with {len(shifts)} shifts on {date} ({primary_id}, {sec_id})",
                        rule_code="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
                    )
                )

        # 2. Detect Approved Leave Overlapping Shift
        approved_leaves = [l for l in self.dataset.leave_requests if l.status == LeaveStatus.APPROVED]
        emp_leave_spans: Dict[str, List[Tuple[datetime.date, datetime.date, str]]] = {}
        for l in approved_leaves:
            if l.employee_id not in emp_leave_spans:
                emp_leave_spans[l.employee_id] = []
            emp_leave_spans[l.employee_id].append((
                datetime.date.fromisoformat(l.start_date),
                datetime.date.fromisoformat(l.end_date),
                l.leave_id
            ))

        for sa in self.dataset.shift_assignments:
            if sa.status in (AssignmentStatus.SCHEDULED, AssignmentStatus.COMPLETED):
                if sa.employee_id in emp_leave_spans:
                    shift_d = datetime.date.fromisoformat(sa.date)
                    for start_d, end_d, leave_id in emp_leave_spans[sa.employee_id]:
                        if start_d <= shift_d <= end_d:
                            self.detected_anomalies.append(
                                ValidationIssue(
                                    check_name="LEAVE_OVERLAP_DETECTION",
                                    severity="ANOMALY_DETECTED",
                                    entity_type="ShiftAssignment",
                                    entity_id=sa.assignment_id,
                                    message=f"Shift {sa.assignment_id} scheduled for {sa.employee_id} during approved leave {leave_id} on {sa.date}",
                                    rule_code="RULE_APPROVED_LEAVE_NON_CONFLICT",
                                )
                            )

        # 3. Detect Required Skill Absent
        for sa in self.dataset.shift_assignments:
            if sa.role_skill_id:
                if (sa.employee_id, sa.role_skill_id) not in emp_skill_set:
                    self.detected_anomalies.append(
                        ValidationIssue(
                            check_name="SKILL_ABSENCE_DETECTION",
                            severity="ANOMALY_DETECTED",
                            entity_type="ShiftAssignment",
                            entity_id=sa.assignment_id,
                            message=f"Shift {sa.assignment_id} mandates skill {sa.role_skill_id} but assigned employee {sa.employee_id} lacks credential",
                            rule_code="RULE_MANDATORY_ROLE_SKILL_MATCH",
                        )
                    )

        # 4. Detect Overtime Cap Exceeded
        emp_week_hours: Dict[Tuple[str, int], float] = {}
        tmpl_map = {t.shift_template_id: t for t in self.dataset.shift_templates}
        for sa in self.dataset.shift_assignments:
            if sa.status in (AssignmentStatus.SCHEDULED, AssignmentStatus.COMPLETED):
                shift_dt = datetime.date.fromisoformat(sa.date)
                week_num = shift_dt.isocalendar()[1]
                duration = tmpl_map[sa.shift_template_id].duration_hours if sa.shift_template_id in tmpl_map else 8.0
                key = (sa.employee_id, week_num)
                emp_week_hours[key] = emp_week_hours.get(key, 0.0) + duration

        for (emp_id, week_num), total_hrs in emp_week_hours.items():
            emp = emp_map.get(emp_id)
            if emp:
                max_allowed = emp.contract_hours_per_week + emp.max_weekly_overtime_hours
                if total_hrs > max_allowed:
                    self.detected_anomalies.append(
                        ValidationIssue(
                            check_name="OVERTIME_CAP_EXCEEDED_DETECTION",
                            severity="ANOMALY_DETECTED",
                            entity_type="Employee",
                            entity_id=emp_id,
                            message=f"Employee {emp_id} scheduled for {total_hrs:.1f}h in week {week_num}, exceeding legal cap of {max_allowed:.1f}h",
                            rule_code="RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP",
                        )
                    )

        # 5. Detect Swap Applied Without Approval
        for swp in self.dataset.swap_requests:
            if swp.status == SwapStatus.APPLIED:
                if not swp.manager_decision_by or not swp.manager_decision_at:
                    self.detected_anomalies.append(
                        ValidationIssue(
                            check_name="UNAPPROVED_SWAP_DETECTION",
                            severity="ANOMALY_DETECTED",
                            entity_type="SwapRequest",
                            entity_id=swp.swap_id,
                            message=f"Swap {swp.swap_id} has APPLIED status but lacks required manager authorization signoff",
                            rule_code="RULE_SWAP_REQUIRES_MANAGER_APPROVAL",
                        )
                    )

    # -------------------------------------------------------------------------
    # Evaluation Matrix Against Ground Truth
    # -------------------------------------------------------------------------
    def _evaluate_ground_truth(self) -> Dict[str, Any]:
        """
        Benchmarks detected anomalies against ground_truth_anomalies.
        Calculates True Positives, False Positives, False Negatives, Precision, Recall, F1.
        """
        gt_list = self.dataset.ground_truth_anomalies
        gt_rule_map: Dict[str, GroundTruthAnomaly] = {
            gt.expected_detection_rule: gt for gt in gt_list
        }

        detected_rule_codes = {d.rule_code for d in self.detected_anomalies}

        tp = 0
        fn = 0
        fp = 0

        matched_details = []

        for gt in gt_list:
            if gt.expected_detection_rule in detected_rule_codes:
                tp += 1
                matched_details.append({
                    "ground_truth_id": gt.anomaly_id,
                    "rule": gt.expected_detection_rule,
                    "status": "DETECTED_TRUE_POSITIVE",
                    "entity_id": gt.primary_entity_id,
                })
            else:
                fn += 1
                matched_details.append({
                    "ground_truth_id": gt.anomaly_id,
                    "rule": gt.expected_detection_rule,
                    "status": "MISSED_FALSE_NEGATIVE",
                    "entity_id": gt.primary_entity_id,
                })

        for det in self.detected_anomalies:
            if det.rule_code not in gt_rule_map:
                fp += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

        return {
            "total_ground_truth": len(gt_list),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "breakdown": matched_details,
        }
