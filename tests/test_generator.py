"""
Tests for Synthetic Data Generator (Steps 2 - 7).
Includes:
  - Entity count assertions
  - Deterministic ID format validation (regex checks)
  - Injected edge case type coverage
  - No ShiftCode enum leak in IDs
"""

import re
import pytest
from data_generator.generator import SyntheticDataGenerator
from data_generator.models import ShiftCode, LeaveStatus, AssignmentStatus


def test_starter_generation():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    assert len(dataset.employees) == 100
    assert len(dataset.teams) == 10
    assert len(dataset.skills) == 10
    assert len(dataset.shift_templates) == 3
    assert len(dataset.holiday_calendar) == 4
    assert len(dataset.coverage_requirements) > 0
    assert len(dataset.leave_requests) > 0
    assert len(dataset.shift_assignments) > 0
    assert len(dataset.attendance_events) > 0
    assert len(dataset.ground_truth_anomalies) == 5


def test_deterministic_id_conventions():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    # Employee ID: EMP-000001
    assert dataset.employees[0].employee_id == "EMP-000001"
    assert dataset.employees[-1].employee_id == "EMP-000100"

    # Team ID: TEAM-001
    assert dataset.teams[0].team_id == "TEAM-001"

    # Shift Assignment: SHIFT-YYYY-MM-DD-<Code>-<Seq>
    assert dataset.shift_assignments[0].assignment_id.startswith("SHIFT-2026-")

    # Leave Request: LVE-2026-000001
    assert dataset.leave_requests[0].leave_id == "LVE-2026-000001"

    # Attendance: ATT-<employee-id>-<timestamp>
    assert dataset.attendance_events[0].attendance_id.startswith("ATT-EMP-")


def test_injected_edge_cases():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    gt_types = {gt.anomaly_type.value for gt in dataset.ground_truth_anomalies}
    expected = {
        "EMPLOYEE_DOUBLE_BOOKED",
        "APPROVED_LEAVE_OVERLAPS_SHIFT",
        "REQUIRED_SKILL_ABSENT",
        "OVERTIME_CAP_EXCEEDED",
        "SWAP_APPLIED_WITHOUT_APPROVAL",
    }
    assert gt_types == expected


# ---------------------------------------------------------------------------
# ID Format Regex Tests
# ---------------------------------------------------------------------------
ID_PATTERNS = {
    "employee_id": (r"^EMP-\d{6}$", lambda ds: [e.employee_id for e in ds.employees]),
    "team_id": (r"^TEAM-\d{3}$", lambda ds: [t.team_id for t in ds.teams]),
    "skill_id": (r"^SKILL-\d{2}$", lambda ds: [s.skill_id for s in ds.skills]),
    "shift_template_id": (r"^TMPL-[A-Z]+$", lambda ds: [st.shift_template_id for st in ds.shift_templates]),
    "leave_id": (r"^LVE-\d{4}-\d{6}$", lambda ds: [l.leave_id for l in ds.leave_requests]),
    "swap_id": (r"^SWP-\d{4}-\d{6}$", lambda ds: [s.swap_id for s in ds.swap_requests]),
    "attendance_id": (r"^ATT-EMP-\d{6}-\d{8}T\d{6}$", lambda ds: [a.attendance_id for a in ds.attendance_events]),
    "ground_truth_id": (r"^GT-\d{6}$", lambda ds: [g.anomaly_id for g in ds.ground_truth_anomalies]),
}


@pytest.mark.parametrize("id_field,pattern_and_extractor", list(ID_PATTERNS.items()))
def test_id_format_regex(id_field, pattern_and_extractor):
    pattern, extractor = pattern_and_extractor
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    ids = extractor(dataset)
    assert ids, f"No IDs found for {id_field}"
    bad = [id_ for id_ in ids if not re.match(pattern, id_)]
    assert not bad, (
        f"{id_field}: {len(bad)} IDs don't match pattern {pattern!r}. "
        f"Examples: {bad[:5]}"
    )


def test_shift_assignment_ids_no_shiftcode_leak():
    """No shift assignment ID should contain 'ShiftCode.' — i.e. the enum
    string representation must use the .value ('A', 'B', 'C') not the class name."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    bad_ids = [
        a.assignment_id for a in dataset.shift_assignments
        if "ShiftCode." in a.assignment_id
    ]
    assert not bad_ids, (
        f"Found {len(bad_ids)} shift assignment IDs containing 'ShiftCode.': {bad_ids[:5]}"
    )


def test_shift_assignment_id_format():
    """All shift IDs must match SHIFT-YYYY-MM-DD-<A|B|C>-<6digits>."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    pattern = re.compile(r"^SHIFT-\d{4}-\d{2}-\d{2}-[ABC]-\d{6}$")
    bad = [
        a.assignment_id for a in dataset.shift_assignments
        if not pattern.match(a.assignment_id)
    ]
    assert not bad, (
        f"Found {len(bad)} shift assignment IDs with bad format: {bad[:5]}"
    )


def test_applied_swaps_have_manager_approval():
    """APPLIED swaps must all have manager_decision_by populated — baseline generator
    had a scoping bug that zeroed out manager_id for all swaps after the first
    PENDING_MANAGER swap was created."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    from data_generator.models import SwapStatus
    bad_swaps = [
        s.swap_id for s in dataset.swap_requests
        if s.status == SwapStatus.APPLIED and not s.manager_decision_by
        and not s.swap_id.endswith("999001")  # Exclude the deliberately injected anomaly
    ]
    assert not bad_swaps, (
        f"Found {len(bad_swaps)} APPLIED swaps without manager approval "
        f"(should only be the injected anomaly SWP-2026-999001): {bad_swaps}"
    )


def test_baseline_satisfies_business_rules_before_anomaly_injection():
    """Verify that baseline data satisfies all documented business rules
    BEFORE any intentional anomalies are injected."""
    from data_generator.validator import DatasetValidator
    from data_generator.generator import GeneratedDataset

    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    skills = gen._generate_skills()
    teams = gen._generate_teams()
    employees, employee_skills = gen._generate_employees_and_skills(teams, skills)
    gen._assign_team_managers(teams, employees)
    shift_templates = gen._generate_shift_templates()
    holiday_calendar = gen._generate_holidays()
    coverage_requirements = gen._generate_coverage_requirements(teams, shift_templates, skills)
    leave_requests = gen._generate_leave_requests(employees)

    shift_assignments = gen._generate_baseline_schedules(
        employees, employee_skills, teams, shift_templates, coverage_requirements, leave_requests
    )
    swap_requests = gen._generate_swap_requests(shift_assignments, employees, employee_skills)
    attendance_events = gen._generate_attendance_events(shift_assignments)

    baseline_dataset = GeneratedDataset(
        scale="starter",
        seed=20261022,
        teams=teams,
        skills=skills,
        employees=employees,
        employee_skills=employee_skills,
        shift_templates=shift_templates,
        holiday_calendar=holiday_calendar,
        coverage_requirements=coverage_requirements,
        leave_requests=leave_requests,
        shift_assignments=shift_assignments,
        swap_requests=swap_requests,
        attendance_events=attendance_events,
        ground_truth_anomalies=[],
        metadata={},
    )

    validator = DatasetValidator(baseline_dataset)
    report = validator.validate()

    assert report.is_valid is True
    assert len(report.detected_rule_violations) == 0, (
        f"Baseline data had {len(report.detected_rule_violations)} violations before injection: "
        f"{[(v.rule_code, v.entity_id, v.message) for v in report.detected_rule_violations]}"
    )


def test_scheduler_solver_shift_id_format_and_uniqueness():
    """Verify that FairShiftScheduler produces unique shift IDs adhering to
    the SHIFT-YYYY-MM-DD-<ShiftLetter>-<Seq> convention without enum leak."""
    from data_generator.scheduler import FairShiftScheduler

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

    pattern = re.compile(r"^SHIFT-\d{4}-\d{2}-\d{2}-[ABC]-\d{6}$")
    shift_ids = [a.assignment_id for a in result.assignments]

    assert len(shift_ids) > 0, "Scheduler produced no assignments"
    assert len(shift_ids) == len(set(shift_ids)), "Scheduler produced duplicate assignment IDs"

    bad_format = [sid for sid in shift_ids if not pattern.match(sid)]
    assert not bad_format, f"Scheduler produced invalid shift IDs: {bad_format[:5]}"

    bad_enum = [sid for sid in shift_ids if "ShiftCode." in sid]
    assert not bad_enum, f"Scheduler leaked ShiftCode enum: {bad_enum[:5]}"


def test_case3_skill_injection_does_not_double_book():
    """Verify that Case 3 (skill injection) does not produce an unintended
    double-booking on the target employee."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    # Find the target employee for Case 3 from ground truth
    case3_gt = next(
        (gt for gt in dataset.ground_truth_anomalies if gt.anomaly_id == "GT-000003"),
        None,
    )
    assert case3_gt is not None, "GT-000003 not found in ground truth"

    # Find the assignment
    asgn3 = next(
        (a for a in dataset.shift_assignments if a.assignment_id == case3_gt.primary_entity_id),
        None,
    )
    assert asgn3 is not None, f"Assignment {case3_gt.primary_entity_id} not found"

    # Verify that this employee has exactly one shift on that date
    same_date_shifts = [
        a for a in dataset.shift_assignments
        if a.employee_id == asgn3.employee_id and a.date == asgn3.date
    ]
    assert len(same_date_shifts) == 1, (
        f"Employee {asgn3.employee_id} has {len(same_date_shifts)} shifts on {asgn3.date}: "
        f"{[s.assignment_id for s in same_date_shifts]}"
    )
