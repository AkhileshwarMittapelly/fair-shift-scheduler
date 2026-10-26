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
