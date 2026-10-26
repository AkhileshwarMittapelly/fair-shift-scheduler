"""
Tests for Synthetic Data Generator (Steps 2 - 7).
"""

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
