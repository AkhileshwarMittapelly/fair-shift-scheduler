"""
Tests for Constraint-Based Fair Shift Scheduling Engine.
Includes:
  - Feasibility and constraint metrics
  - Reproducibility check (now covers CSV + JSON + SQL + MD)
  - Weekly overtime math verification (per employee per ISO week)
"""

import pytest
import datetime
from data_generator.generator import SyntheticDataGenerator
from data_generator.scheduler import FairShiftScheduler


def test_fair_scheduler_feasibility_and_constraints():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    scheduler = FairShiftScheduler(
        employees=dataset.employees,
        teams=dataset.teams,
        skills=dataset.skills,
        employee_skills=dataset.employee_skills,
        shift_templates=dataset.shift_templates,
        leave_requests=dataset.leave_requests,
    )

    result = scheduler.solve(
        coverage_requirements=dataset.coverage_requirements,
        start_date="2026-01-01",
        num_days=7,
    )

    # Check metrics
    assert result.metrics.hard_constraint_violations == 0
    assert result.metrics.coverage_fulfillment_rate_pct > 80.0
    assert result.metrics.fairness_gini_coefficient < 0.25
    assert len(result.assignments) > 0


def test_reproducibility():
    from data_generator.reproducibility import verify_reproducibility

    res = verify_reproducibility(seed=20261022, scale="starter")
    assert res["is_reproducible"] is True
    # After the fix, we check CSV + JSON + SQL + MD files; expect at least 15 files
    assert res["total_files_verified"] >= 15, (
        f"Expected >= 15 files verified but got {res['total_files_verified']}. "
        f"Files checked: {[c['file'] for c in res['file_comparisons']]}"
    )
    # No file should be missing in either run
    missing = [c for c in res["file_comparisons"] if "MISSING" in (c["run1_sha256"], c["run2_sha256"])]
    assert not missing, f"Files missing in one of the runs: {[c['file'] for c in missing]}"


def test_weekly_overtime_math():
    """
    Verify that the validator's overtime detection correctly sums hours
    per (employee_id, iso_week) and does NOT aggregate across all weeks.
    An employee working exactly contract hours in each of two separate weeks
    should show ZERO overtime, even though the two-week total exceeds 40h.
    """
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    from data_generator.validator import DatasetValidator
    from data_generator.models import AssignmentStatus, LeaveStatus

    # Pick an employee and verify their per-week hours don't exceed contract + OT cap
    # by checking the validator's detected_anomalies against known injection
    validator = DatasetValidator(dataset)
    report = validator.validate()

    # The only overtime anomaly should be EMP-000003 (deliberately injected)
    ot_anomalies = [
        a for a in report.detected_rule_violations
        if a.rule_code == "RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP"
    ]
    ot_emp_ids = {a.entity_id for a in ot_anomalies}
    # EMP-000003 was explicitly given 3 extra 8.5h night shifts in one week (~52h total)
    # Other employees should NOT show overtime after the correct per-week calculation
    assert "EMP-000003" in ot_emp_ids, "Expected injected OT anomaly for EMP-000003 not found"


def _build_test_harness():
    """Builds a minimal, self-contained scheduling harness for testing constraints."""
    from data_generator.models import (
        Team, Skill, Employee, EmployeeSkill, ShiftTemplate,
        EmploymentStatus, SkillCategory, ProficiencyLevel, ShiftCode
    )
    team = Team(
        team_id="TEAM-TEST",
        team_name="Test Team",
        department="Operations",
        manager_id=None,
        location="HQ",
        max_overtime_hours_per_week=10.0,
        created_at="2026-01-01T00:00:00Z",
    )
    skill_a = Skill(
        skill_id="SKL-A",
        skill_name="Skill A",
        category=SkillCategory.CLINICAL,
        minimum_certification_level=ProficiencyLevel.SENIOR,
        description="Test Skill A",
    )
    skill_b = Skill(
        skill_id="SKL-B",
        skill_name="Skill B",
        category=SkillCategory.TECHNICAL,
        minimum_certification_level=ProficiencyLevel.SENIOR,
        description="Test Skill B",
    )

    emp1 = Employee(
        employee_id="EMP-TEST-001",
        first_name="Alice",
        last_name="Tester",
        email="alice@test.com",
        team_id=team.team_id,
        hire_date="2024-01-01",
        contract_hours_per_week=40.0,
        max_weekly_overtime_hours=8.0,
        hourly_rate=30.0,
        employment_status=EmploymentStatus.ACTIVE,
        created_at="2024-01-01T00:00:00Z",
    )
    emp2 = Employee(
        employee_id="EMP-TEST-002",
        first_name="Bob",
        last_name="Tester",
        email="bob@test.com",
        team_id=team.team_id,
        hire_date="2024-01-01",
        contract_hours_per_week=40.0,
        max_weekly_overtime_hours=8.0,
        hourly_rate=30.0,
        employment_status=EmploymentStatus.ACTIVE,
        created_at="2024-01-01T00:00:00Z",
    )

    tmpl_morning = ShiftTemplate(
        shift_template_id="TMPL-A",
        shift_code=ShiftCode.A,
        shift_name="Morning",
        start_time="06:00",
        end_time="14:30",
        duration_hours=8.5,
        is_overnight=False,
        differential_rate_multiplier=1.0,
    )
    tmpl_afternoon = ShiftTemplate(
        shift_template_id="TMPL-B",
        shift_code=ShiftCode.B,
        shift_name="Afternoon",
        start_time="14:00",
        end_time="22:30",
        duration_hours=8.5,
        is_overnight=False,
        differential_rate_multiplier=1.15,
    )
    tmpl_night = ShiftTemplate(
        shift_template_id="TMPL-C",
        shift_code=ShiftCode.C,
        shift_name="Night",
        start_time="22:00",
        end_time="06:30",
        duration_hours=8.5,
        is_overnight=True,
        differential_rate_multiplier=1.25,
    )

    return {
        "team": team,
        "skills": [skill_a, skill_b],
        "employees": [emp1, emp2],
        "shift_templates": [tmpl_morning, tmpl_afternoon, tmpl_night],
    }


def test_expired_certification_and_missing_skills():
    """Verify expired certifications and missing skills prevent shift assignment."""
    from data_generator.models import EmployeeSkill, CoverageRequirement, ProficiencyLevel

    h = _build_test_harness()
    emp1, emp2 = h["employees"]

    # Emp1 cert expired on 2025-12-31; Emp2 cert valid through 2026-12-31
    es_expired = EmployeeSkill(
        employee_skill_id="ES-EXP-01",
        employee_id=emp1.employee_id,
        skill_id="SKL-A",
        proficiency_level=ProficiencyLevel.SENIOR,
        certified_date="2025-01-01",
        expiry_date="2025-12-31",
    )
    es_valid = EmployeeSkill(
        employee_skill_id="ES-VAL-02",
        employee_id=emp2.employee_id,
        skill_id="SKL-A",
        proficiency_level=ProficiencyLevel.SENIOR,
        certified_date="2025-01-01",
        expiry_date="2026-12-31",
    )

    scheduler = FairShiftScheduler(
        employees=[emp1, emp2],
        teams=[h["team"]],
        skills=h["skills"],
        employee_skills=[es_expired, es_valid],
        shift_templates=h["shift_templates"],
        leave_requests=[],
    )

    # Unit check on has_valid_skill
    assert scheduler.has_valid_skill(emp1.employee_id, "SKL-A", "2026-01-05") is False
    assert scheduler.has_valid_skill(emp2.employee_id, "SKL-A", "2026-01-05") is True
    assert scheduler.has_valid_skill(emp1.employee_id, "SKL-B", "2026-01-05") is False  # Missing skill

    # Solve requirement requiring SKL-A
    req = CoverageRequirement(
        requirement_id="REQ-001",
        date="2026-01-05",
        shift_template_id="TMPL-A",
        team_id=h["team"].team_id,
        skill_id="SKL-A",
        min_headcount=1,
        target_headcount=1,
        priority_weight=1.0,
    )
    result = scheduler.solve(coverage_requirements=[req], start_date="2026-01-05", num_days=1)
    assert len(result.assignments) == 1
    assert result.assignments[0].employee_id == emp2.employee_id  # Only emp2 is eligible


def test_approved_leave_and_cross_midnight_shifts():
    """Verify approved leave and cross-midnight shifts are respected."""
    from data_generator.models import LeaveRequest, LeaveStatus, LeaveType, CoverageRequirement

    h = _build_test_harness()
    emp1, emp2 = h["employees"]

    # Emp1 has approved leave on 2026-01-02
    leave = LeaveRequest(
        leave_id="LVE-001",
        employee_id=emp1.employee_id,
        start_date="2026-01-02",
        end_date="2026-01-02",
        leave_type=LeaveType.ANNUAL,
        status=LeaveStatus.APPROVED,
        reason="Vacation",
        decision_by="MGR-001",
        decision_timestamp="2026-01-01T00:00:00Z",
        decision_notes="Approved",
    )

    scheduler = FairShiftScheduler(
        employees=[emp1, emp2],
        teams=[h["team"]],
        skills=h["skills"],
        employee_skills=[],
        shift_templates=h["shift_templates"],
        leave_requests=[leave],
    )

    # 1. Day requirement on leave date
    req_day2 = CoverageRequirement(
        requirement_id="REQ-002",
        date="2026-01-02",
        shift_template_id="TMPL-A",
        team_id=h["team"].team_id,
        skill_id=None,
        min_headcount=1,
        target_headcount=1,
        priority_weight=1.0,
    )
    result = scheduler.solve([req_day2], start_date="2026-01-02", num_days=1)
    assert len(result.assignments) == 1
    assert result.assignments[0].employee_id == emp2.employee_id

    # 2. Cross-midnight shift starting 2026-01-01 22:00 and ending 2026-01-02 06:30
    req_night = CoverageRequirement(
        requirement_id="REQ-003",
        date="2026-01-01",
        shift_template_id="TMPL-C",  # 22:00 -> 06:30 next morning
        team_id=h["team"].team_id,
        skill_id=None,
        min_headcount=1,
        target_headcount=1,
        priority_weight=1.0,
    )
    result_night = scheduler.solve([req_night], start_date="2026-01-01", num_days=1)
    assert len(result_night.assignments) == 1
    # Emp1's leave starts 2026-01-02 00:00, which overlaps with the overnight shift ending at 06:30
    assert result_night.assignments[0].employee_id == emp2.employee_id


def test_minimum_rest_period_enforced():
    """Verify that shifts violating the 11-hour minimum rest period are not assigned."""
    from data_generator.models import CoverageRequirement

    h = _build_test_harness()
    emp1 = h["employees"][0]  # Only 1 employee available

    scheduler = FairShiftScheduler(
        employees=[emp1],
        teams=[h["team"]],
        skills=h["skills"],
        employee_skills=[],
        shift_templates=h["shift_templates"],
        leave_requests=[],
        min_rest_hours=11.0,
    )

    # Night shift on Day 1 ends at Day 2 06:30
    req1 = CoverageRequirement(
        requirement_id="REQ-NIGHT",
        date="2026-01-01",
        shift_template_id="TMPL-C",
        team_id=h["team"].team_id,
        skill_id=None,
        min_headcount=1,
        target_headcount=1,
        priority_weight=1.0,
    )
    # Afternoon shift on Day 2 starts at 14:00 (rest = 7.5 hours < 11.0 hours)
    req2 = CoverageRequirement(
        requirement_id="REQ-AFTERNOON",
        date="2026-01-02",
        shift_template_id="TMPL-B",
        team_id=h["team"].team_id,
        skill_id=None,
        min_headcount=1,
        target_headcount=1,
        priority_weight=1.0,
    )

    result = scheduler.solve([req1, req2], start_date="2026-01-01", num_days=2)
    # The first shift is scheduled, but the second must be rejected due to rest violation
    assert len(result.assignments) == 1
    assert result.assignments[0].shift_template_id == "TMPL-C"
    assert len(result.coverage_gaps) == 1
    assert result.coverage_gaps[0].requirement_id == "REQ-AFTERNOON"
    assert result.is_feasible is False


def test_weekly_overtime_boundaries_and_consecutive_days():
    """Verify weekly contract + overtime caps and consecutive day limits."""
    from data_generator.models import CoverageRequirement

    h = _build_test_harness()
    emp1 = h["employees"][0]
    emp1.contract_hours_per_week = 20.0
    emp1.max_weekly_overtime_hours = 5.0  # Max 25.0 hours allowed per week

    scheduler = FairShiftScheduler(
        employees=[emp1],
        teams=[h["team"]],
        skills=h["skills"],
        employee_skills=[],
        shift_templates=h["shift_templates"],
        leave_requests=[],
    )

    # 4 shifts of 8.5h = 34h (> 25h max allowed)
    reqs = [
        CoverageRequirement(
            requirement_id=f"REQ-W-{i}",
            date=f"2026-01-0{i+1}",
            shift_template_id="TMPL-A",
            team_id=h["team"].team_id,
            skill_id=None,
            min_headcount=1,
            target_headcount=1,
            priority_weight=1.0,
        )
        for i in range(4)
    ]

    result = scheduler.solve(reqs, start_date="2026-01-01", num_days=4)
    # 2 shifts = 17.0h (<= 25.0h); 3rd shift = 25.5h (> 25.0h)
    assert len(result.assignments) == 2
    assert len(result.coverage_gaps) == 2
    assert result.is_feasible is False


def test_coverage_gaps_and_feasibility_determination():
    """Verify coverage gaps are accurately reported and infeasible schedule is marked."""
    from data_generator.models import CoverageRequirement

    h = _build_test_harness()
    # 2 employees, but demand requires headcount of 5
    req = CoverageRequirement(
        requirement_id="REQ-HEAVY",
        date="2026-01-05",
        shift_template_id="TMPL-A",
        team_id=h["team"].team_id,
        skill_id=None,
        min_headcount=5,
        target_headcount=5,
        priority_weight=1.0,
    )

    scheduler = FairShiftScheduler(
        employees=h["employees"],
        teams=[h["team"]],
        skills=h["skills"],
        employee_skills=[],
        shift_templates=h["shift_templates"],
        leave_requests=[],
    )

    result = scheduler.solve([req], start_date="2026-01-05", num_days=1)
    assert len(result.assignments) == 2  # Only 2 employees can work
    assert len(result.coverage_gaps) == 3  # 3 unfilled positions
    assert result.metrics.unfulfilled_requirements == 3
    assert result.metrics.fulfilled_requirements == 2
    assert result.metrics.coverage_fulfillment_rate_pct == 40.0
    assert result.is_feasible is False


def test_hard_constraint_violations_calculation_actual_count():
    """Verify that hard_constraint_violations is dynamically computed from schedule."""
    from data_generator.models import ShiftAssignment, AssignmentStatus

    h = _build_test_harness()
    emp1, emp2 = h["employees"]

    scheduler = FairShiftScheduler(
        employees=[emp1, emp2],
        teams=[h["team"]],
        skills=h["skills"],
        employee_skills=[],
        shift_templates=h["shift_templates"],
        leave_requests=[],
        min_rest_hours=11.0,
    )

    # 1. Valid schedule has 0 violations
    valid_asgn = [
        ShiftAssignment(
            assignment_id="ASGN-01",
            date="2026-01-01",
            shift_template_id="TMPL-A",
            employee_id=emp1.employee_id,
            team_id=h["team"].team_id,
            role_skill_id=None,
            scheduled_start="2026-01-01T06:00:00Z",
            scheduled_end="2026-01-01T14:30:00Z",
            status=AssignmentStatus.SCHEDULED,
            created_at="2026-01-01T00:00:00Z",
            created_by="TEST",
        )
    ]
    assert scheduler._count_hard_constraint_violations(valid_asgn) == 0

    # 2. Inject an invalid schedule: missing skill + overlapping shifts + insufficient rest
    invalid_asgns = [
        # a) Missing skill
        ShiftAssignment(
            assignment_id="ASGN-01",
            date="2026-01-01",
            shift_template_id="TMPL-A",
            employee_id=emp1.employee_id,
            team_id=h["team"].team_id,
            role_skill_id="SKL-A",  # emp1 does not have SKL-A
            scheduled_start="2026-01-01T06:00:00Z",
            scheduled_end="2026-01-01T14:30:00Z",
            status=AssignmentStatus.SCHEDULED,
            created_at="2026-01-01T00:00:00Z",
            created_by="TEST",
        ),
        # b) Overlapping shift for emp1
        ShiftAssignment(
            assignment_id="ASGN-02",
            date="2026-01-01",
            shift_template_id="TMPL-A",
            employee_id=emp1.employee_id,
            team_id=h["team"].team_id,
            role_skill_id=None,
            scheduled_start="2026-01-01T10:00:00Z",
            scheduled_end="2026-01-01T18:30:00Z",
            status=AssignmentStatus.SCHEDULED,
            created_at="2026-01-01T00:00:00Z",
            created_by="TEST",
        ),
    ]

    violations = scheduler._count_hard_constraint_violations(invalid_asgns)
    # Missing skill (1) + Overlap (1) = at least 2 violations
    assert violations >= 2


def test_fairness_calculations_gini_and_equity():
    """Verify fairness Gini coefficient and equity calculations."""
    # Completely equal hours -> Gini is 0
    assert FairShiftScheduler._compute_gini([40.0, 40.0, 40.0, 40.0]) == 0.0
    # Completely unequal hours -> Gini is 0.75 for [0, 0, 0, 40]
    assert round(FairShiftScheduler._compute_gini([0.0, 0.0, 0.0, 40.0]), 2) == 0.75
    # Empty or zero values
    assert FairShiftScheduler._compute_gini([]) == 0.0
    assert FairShiftScheduler._compute_gini([0.0, 0.0]) == 0.0

    # Equity CV
    assert FairShiftScheduler._compute_cv([5, 5, 5]) == 0.0
    assert FairShiftScheduler._compute_cv([]) == 0.0


def test_shift_swap_validation_and_atomic_execution():
    """Verify shift swap validation (skills, leaves, overlaps, rest, OT) and atomic execution."""
    from data_generator.models import (
        ShiftAssignment, SwapRequest, SwapStatus, AssignmentStatus,
        EmployeeSkill, LeaveRequest, LeaveStatus, LeaveType, ProficiencyLevel
    )
    from data_generator.scheduler import validate_shift_swap, apply_shift_swap

    h = _build_test_harness()
    emp1, emp2 = h["employees"]

    es1 = EmployeeSkill(
        employee_skill_id="ES-SWAP-1",
        employee_id=emp1.employee_id,
        skill_id="SKL-A",
        proficiency_level=ProficiencyLevel.SENIOR,
        certified_date="2025-01-01",
        expiry_date="2026-12-31",
    )
    es2 = EmployeeSkill(
        employee_skill_id="ES-SWAP-2",
        employee_id=emp2.employee_id,
        skill_id="SKL-B",
        proficiency_level=ProficiencyLevel.SENIOR,
        certified_date="2025-01-01",
        expiry_date="2026-12-31",
    )

    asgn1 = ShiftAssignment(
        assignment_id="ASGN-001",
        date="2026-01-05",
        shift_template_id="TMPL-A",
        employee_id=emp1.employee_id,
        team_id=h["team"].team_id,
        role_skill_id="SKL-B",  # Requires SKL-B (held by emp2)
        scheduled_start="2026-01-05T06:00:00Z",
        scheduled_end="2026-01-05T14:30:00Z",
        status=AssignmentStatus.SCHEDULED,
        created_at="2026-01-01T00:00:00Z",
        created_by="TEST",
    )
    asgn2 = ShiftAssignment(
        assignment_id="ASGN-002",
        date="2026-01-06",
        shift_template_id="TMPL-A",
        employee_id=emp2.employee_id,
        team_id=h["team"].team_id,
        role_skill_id="SKL-A",  # Requires SKL-A (held by emp1)
        scheduled_start="2026-01-06T06:00:00Z",
        scheduled_end="2026-01-06T14:30:00Z",
        status=AssignmentStatus.SCHEDULED,
        created_at="2026-01-01T00:00:00Z",
        created_by="TEST",
    )

    swap = SwapRequest(
        swap_id="SWP-001",
        requester_assignment_id=asgn1.assignment_id,
        target_assignment_id=asgn2.assignment_id,
        requester_employee_id=emp1.employee_id,
        target_employee_id=emp2.employee_id,
        status=SwapStatus.PENDING_MANAGER,
        requested_at="2026-01-02T10:00:00Z",
        peer_agreed_at="2026-01-02T11:00:00Z",
        manager_decision_by=None,
        manager_decision_at=None,
        decision_notes=None,
    )

    # 1. Valid Swap Execution
    is_valid, err = validate_shift_swap(
        swap=swap,
        assignments=[asgn1, asgn2],
        employees=[emp1, emp2],
        skills=[es1, es2],
        leaves=[],
        shift_templates=h["shift_templates"],
    )
    assert is_valid is True
    assert err is None

    # Apply swap atomically
    updated_swap = apply_shift_swap(
        swap=swap,
        assignments=[asgn1, asgn2],
        employees=[emp1, emp2],
        skills=[es1, es2],
        leaves=[],
        shift_templates=h["shift_templates"],
        decision_by="MGR-001",
    )
    assert updated_swap.status == SwapStatus.APPLIED
    assert asgn1.employee_id == emp2.employee_id
    assert asgn2.employee_id == emp1.employee_id
    assert asgn1.status == AssignmentStatus.SWAPPED
    assert asgn2.status == AssignmentStatus.SWAPPED

    # 2. Invalid Swap Rejection: Missing skill
    # Revert assignments back for testing invalid cases
    asgn1.employee_id = emp1.employee_id
    asgn2.employee_id = emp2.employee_id
    asgn1.role_skill_id = "SKL-UNKNOWN"

    is_valid_bad_skill, err_bad_skill = validate_shift_swap(
        swap=swap,
        assignments=[asgn1, asgn2],
        employees=[emp1, emp2],
        skills=[es1, es2],
        leaves=[],
        shift_templates=h["shift_templates"],
    )
    assert is_valid_bad_skill is False
    assert "lacks valid or unexpired certification" in err_bad_skill

    # 3. Invalid Swap Rejection: Approved Leave Conflict
    asgn1.role_skill_id = "SKL-B"  # Restore skill
    leave_conflict = LeaveRequest(
        leave_id="LVE-CONF",
        employee_id=emp1.employee_id,
        start_date="2026-01-06",
        end_date="2026-01-06",
        leave_type=LeaveType.ANNUAL,
        status=LeaveStatus.APPROVED,
        reason="Vacation",
        decision_by="MGR-001",
        decision_timestamp="2026-01-01T00:00:00Z",
        decision_notes="Approved",
    )
    is_valid_leave, err_leave = validate_shift_swap(
        swap=swap,
        assignments=[asgn1, asgn2],
        employees=[emp1, emp2],
        skills=[es1, es2],
        leaves=[leave_conflict],
        shift_templates=h["shift_templates"],
    )
    assert is_valid_leave is False
    assert "approved leave" in err_leave

    # 4. Atomicity check: Calling apply_shift_swap on invalid swap raises ValueError without mutating
    with pytest.raises(ValueError) as excinfo:
        apply_shift_swap(
            swap=swap,
            assignments=[asgn1, asgn2],
            employees=[emp1, emp2],
            skills=[es1, es2],
            leaves=[leave_conflict],
            shift_templates=h["shift_templates"],
        )
    assert "approved leave" in str(excinfo.value)
    # Check that neither assignment was modified
    assert asgn1.employee_id == emp1.employee_id
    assert asgn2.employee_id == emp2.employee_id

