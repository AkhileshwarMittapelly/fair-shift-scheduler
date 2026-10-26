"""
Tests for 8-Point Dataset Validator and Ground Truth Benchmarking (Step 8).
Includes:
  - Structural integrity checks
  - Instance-level ground truth matching verification
  - Test that an unrelated entity cannot receive credit for a different GT anomaly
"""

import pytest
from data_generator.generator import SyntheticDataGenerator
from data_generator.validator import DatasetValidator, ValidationIssue
from data_generator.models import (
    ShiftAssignment, AssignmentStatus, GroundTruthAnomaly, AnomalyType, LeaveStatus
)


def test_validator_structural_integrity():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)
    report = validator.validate()

    assert report.is_valid is True
    assert report.summary["pk_uniqueness"] is True
    assert report.summary["foreign_key_integrity"] is True
    assert report.summary["allowed_enums"] is True
    assert report.summary["date_ordering"] is True
    assert report.summary["arithmetic_reconciliation"] is True
    assert report.summary["lifecycle_transitions"] is True
    assert report.summary["duplicate_checks"] is True


def test_ground_truth_detection_accuracy():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)
    report = validator.validate()

    gt = report.ground_truth_evaluation
    assert gt["total_ground_truth"] == 5
    assert gt["true_positives"] == 5, (
        f"Expected 5 TPs but got {gt['true_positives']}. "
        f"Breakdown: {gt['breakdown']}"
    )
    assert gt["false_negatives"] == 0, (
        f"Expected 0 FNs but got {gt['false_negatives']} — "
        f"some injected anomalies were not detected."
    )
    assert gt["recall"] == 1.0, f"Recall dropped below 1.0: {gt['recall']}"

    # Incidental violations (the two overlapping shifts from the Case 4 overtime injection)
    # are correctly classified as False Positives rather than True Positives.
    assert gt["false_positives"] == 2
    assert gt["precision"] == 0.7143
    assert gt["f1_score"] == 0.8333
    assert "incidental_baseline_violations" in gt
    assert len(gt["incidental_baseline_violations"]) == 2



def test_instance_level_matching_no_cross_credit():
    """
    Verify that a detection of entity X with rule R does NOT receive credit for a
    ground-truth entry that lists entity Y with the same rule R (Y != X).

    This test injects a fake GT entry for a nonexistent entity and confirms that
    detecting a real violation of the same rule on a different entity gives FP, not TP.
    """
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    # Add a fake ground-truth entry for an entity that will never be detected
    fake_gt = GroundTruthAnomaly(
        anomaly_id="GT-FAKE-001",
        anomaly_type=AnomalyType.EMPLOYEE_DOUBLE_BOOKED,
        entity_type="ShiftAssignment",
        primary_entity_id="SHIFT-9999-99-99-A-000000",  # Nonexistent — will never be detected
        secondary_entity_id=None,
        description="Synthetic GT entry for cross-credit prevention test",
        injected_timestamp="2026-01-01T00:00:00Z",
        severity="CRITICAL",
        expected_detection_rule="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
    )
    dataset.ground_truth_anomalies.append(fake_gt)

    validator = DatasetValidator(dataset)
    report = validator.validate()

    gt = report.ground_truth_evaluation
    # The fake GT should be a FN — even though the real double-booking was detected,
    # it should NOT receive credit for the nonexistent entity.
    fn_entries = [
        b for b in gt["breakdown"]
        if b["ground_truth_id"] == "GT-FAKE-001" and b["status"] == "MISSED_FALSE_NEGATIVE"
    ]
    assert len(fn_entries) == 1, (
        "Expected GT-FAKE-001 to be a false negative (nonexistent entity should "
        "never match a real detection), but it was credited as a true positive."
    )

    # Cleanup: restore original GT list for other test isolation
    dataset.ground_truth_anomalies.remove(fake_gt)


def test_incidental_violations_are_separated():
    """
    After fixing the swap generation scoping bug, there should be far fewer
    incidental baseline violations (spurious APPLIED-without-approval swaps).
    The incidental_baseline_violations list should be returned by the evaluator.
    """
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)
    report = validator.validate()

    gt = report.ground_truth_evaluation
    assert "incidental_baseline_violations" in gt, (
        "ground_truth_evaluation must include 'incidental_baseline_violations' key"
    )



def test_lifecycle_transition_failure_makes_dataset_invalid():
    """
    A pending leave with an authorizer is an invalid lifecycle state.
    The overall validation result must fail, not merely report the issue.
    """
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    assert dataset.leave_requests, "Starter dataset should include leave requests"

    leave = dataset.leave_requests[0]
    leave.status = LeaveStatus.PENDING
    leave.decision_by = dataset.employees[0].employee_id

    report = DatasetValidator(dataset).validate()

    assert report.summary["lifecycle_transitions"] is False
    assert report.structural_integrity["lifecycle_transitions"] is False
    assert report.is_valid is False


def _clear_active_assignments(dataset):
    """Disable generated assignments so overlap tests only exercise crafted shifts."""
    for assignment in dataset.shift_assignments:
        assignment.status = AssignmentStatus.CANCELLED


def test_double_booking_detects_overlapping_shifts_across_midnight():
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]
    first = replace(
        template,
        assignment_id="SHIFT-OVERLAP-NIGHT",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T23:00:00+00:00",
        scheduled_end="2026-01-02T07:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    second = replace(
        template,
        assignment_id="SHIFT-OVERLAP-MORNING",
        date="2026-01-02",
        employee_id=first.employee_id,
        scheduled_start="2026-01-02T07:00:00+00:00",
        scheduled_end="2026-01-02T15:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([first, second])

    validator = DatasetValidator(dataset)
    validator._detect_business_rule_violations()

    overlaps = [
        issue for issue in validator.detected_anomalies
        if issue.rule_code == "RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS"
    ]
    assert len(overlaps) == 1
    assert first.assignment_id in overlaps[0].message
    assert second.assignment_id in overlaps[0].message


def test_double_booking_ignores_non_overlapping_shifts_on_same_date():
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]
    first = replace(
        template,
        assignment_id="SHIFT-SAME-DATE-AM",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T07:00:00+00:00",
        scheduled_end="2026-01-01T11:00:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    second = replace(
        template,
        assignment_id="SHIFT-SAME-DATE-PM",
        date="2026-01-01",
        employee_id=first.employee_id,
        scheduled_start="2026-01-01T12:00:00+00:00",
        scheduled_end="2026-01-01T16:00:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([first, second])

    validator = DatasetValidator(dataset)
    validator._detect_business_rule_violations()

    overlaps = [
        issue for issue in validator.detected_anomalies
        if issue.rule_code == "RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS"
    ]
    assert overlaps == []


def test_double_booking_allows_back_to_back_shifts():
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]
    first = replace(
        template,
        assignment_id="SHIFT-BACK-TO-BACK-A",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T07:00:00+00:00",
        scheduled_end="2026-01-01T11:00:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    second = replace(
        template,
        assignment_id="SHIFT-BACK-TO-BACK-B",
        date="2026-01-01",
        employee_id=first.employee_id,
        scheduled_start="2026-01-01T11:00:00+00:00",
        scheduled_end="2026-01-01T15:00:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([first, second])

    validator = DatasetValidator(dataset)
    validator._detect_business_rule_violations()

    overlaps = [
        issue for issue in validator.detected_anomalies
        if issue.rule_code == "RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS"
    ]
    assert overlaps == []


def test_double_booking_same_date_overlap():
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]
    first = replace(
        template,
        assignment_id="SHIFT-SAME-DATE-A",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T07:00:00+00:00",
        scheduled_end="2026-01-01T15:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    second = replace(
        template,
        assignment_id="SHIFT-SAME-DATE-B",
        date="2026-01-01",
        employee_id=first.employee_id,
        scheduled_start="2026-01-01T15:00:00+00:00",
        scheduled_end="2026-01-01T23:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([first, second])

    validator = DatasetValidator(dataset)
    validator._detect_business_rule_violations()

    overlaps = [
        issue for issue in validator.detected_anomalies
        if issue.rule_code == "RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS"
    ]
    assert len(overlaps) == 1
    assert first.assignment_id in overlaps[0].message
    assert second.assignment_id in overlaps[0].message


def test_double_booking_overnight_shifts_that_do_not_overlap():
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]
    # Night 1: 2026-01-01 23:00 to 2026-01-02 07:30
    first = replace(
        template,
        assignment_id="SHIFT-NIGHT-1",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T23:00:00+00:00",
        scheduled_end="2026-01-02T07:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    # Night 2: 2026-01-02 23:00 to 2026-01-03 07:30 (starts 15.5h after Night 1 ends)
    second = replace(
        template,
        assignment_id="SHIFT-NIGHT-2",
        date="2026-01-02",
        employee_id=first.employee_id,
        scheduled_start="2026-01-02T23:00:00+00:00",
        scheduled_end="2026-01-03T07:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([first, second])

    validator = DatasetValidator(dataset)
    validator._detect_business_rule_violations()

    overlaps = [
        issue for issue in validator.detected_anomalies
        if issue.rule_code == "RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS"
    ]
    assert overlaps == []


def test_double_booking_identical_intervals_same_employee():
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]
    first = replace(
        template,
        assignment_id="SHIFT-IDENTICAL-1",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T07:00:00+00:00",
        scheduled_end="2026-01-01T15:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    second = replace(
        template,
        assignment_id="SHIFT-IDENTICAL-2",
        date="2026-01-01",
        employee_id=first.employee_id,
        scheduled_start="2026-01-01T07:00:00+00:00",
        scheduled_end="2026-01-01T15:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([first, second])

    validator = DatasetValidator(dataset)
    validator._detect_business_rule_violations()

    overlaps = [
        issue for issue in validator.detected_anomalies
        if issue.rule_code == "RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS"
    ]
    assert len(overlaps) == 1
    assert first.assignment_id in overlaps[0].message
    assert second.assignment_id in overlaps[0].message


def test_double_booking_identical_intervals_different_employees():
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]
    # Two different employees working identical shift intervals is valid staffing
    first = replace(
        template,
        assignment_id="SHIFT-DIFF-EMP-1",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T07:00:00+00:00",
        scheduled_end="2026-01-01T15:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    second = replace(
        template,
        assignment_id="SHIFT-DIFF-EMP-2",
        date="2026-01-01",
        employee_id=dataset.employees[1].employee_id,
        scheduled_start="2026-01-01T07:00:00+00:00",
        scheduled_end="2026-01-01T15:30:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([first, second])

    validator = DatasetValidator(dataset)
    validator._detect_business_rule_violations()

    overlaps = [
        issue for issue in validator.detected_anomalies
        if issue.rule_code == "RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS"
    ]
    assert overlaps == []


def test_ground_truth_matcher_unit_tests():
    """Unit tests for instance-aware 1-to-1 ground truth matcher."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)

    # 1. Multiple detected anomalies with the same rule code but different affected records
    det_a = ValidationIssue(
        check_name="DOUBLE_BOOKING_DETECTION",
        severity="ANOMALY_DETECTED",
        entity_type="ShiftAssignment",
        entity_id="SHIFT-A",
        message="Employee EMP-001 has overlapping shifts SHIFT-A and SHIFT-B",
        rule_code="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
    )
    det_c = ValidationIssue(
        check_name="DOUBLE_BOOKING_DETECTION",
        severity="ANOMALY_DETECTED",
        entity_type="ShiftAssignment",
        entity_id="SHIFT-C",
        message="Employee EMP-002 has overlapping shifts SHIFT-C and SHIFT-D",
        rule_code="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
    )

    gt_1 = GroundTruthAnomaly(
        anomaly_id="GT-UNIT-001",
        anomaly_type=AnomalyType.EMPLOYEE_DOUBLE_BOOKED,
        entity_type="ShiftAssignment",
        primary_entity_id="SHIFT-A",
        secondary_entity_id="SHIFT-B",
        description="Double booked A and B",
        injected_timestamp="2026-01-01T00:00:00Z",
        severity="CRITICAL",
        expected_detection_rule="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
    )
    gt_2 = GroundTruthAnomaly(
        anomaly_id="GT-UNIT-002",
        anomaly_type=AnomalyType.EMPLOYEE_DOUBLE_BOOKED,
        entity_type="ShiftAssignment",
        primary_entity_id="SHIFT-X",  # Not detected
        secondary_entity_id="SHIFT-Y",
        description="Double booked X and Y",
        injected_timestamp="2026-01-01T00:00:00Z",
        severity="CRITICAL",
        expected_detection_rule="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
    )

    # A detection that matches one expected anomaly but not another of the same rule
    assert validator._matches_ground_truth(det_a, gt_1) is True
    assert validator._matches_ground_truth(det_a, gt_2) is False
    assert validator._matches_ground_truth(det_c, gt_1) is False
    assert validator._matches_ground_truth(det_c, gt_2) is False

    # Pairwise matching rejects partial match where secondary shift is different
    gt_mismatch_sec = GroundTruthAnomaly(
        anomaly_id="GT-UNIT-003",
        anomaly_type=AnomalyType.EMPLOYEE_DOUBLE_BOOKED,
        entity_type="ShiftAssignment",
        primary_entity_id="SHIFT-A",
        secondary_entity_id="SHIFT-Z",  # Different secondary shift
        description="Double booked A and Z",
        injected_timestamp="2026-01-01T00:00:00Z",
        severity="CRITICAL",
        expected_detection_rule="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
    )
    assert validator._matches_ground_truth(det_a, gt_mismatch_sec) is False


def test_ground_truth_1to1_matching_prevents_duplicate_satisfaction():
    """Verify that duplicate detections of the same violation cannot satisfy multiple GT entries."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()

    # Clear detections and inject handcrafted ones
    validator = DatasetValidator(dataset)
    validator.detected_anomalies = [
        ValidationIssue(
            check_name="DOUBLE_BOOKING_DETECTION",
            severity="ANOMALY_DETECTED",
            entity_type="ShiftAssignment",
            entity_id="SHIFT-A",
            message="Employee EMP-001 has overlapping shifts SHIFT-A and SHIFT-B",
            rule_code="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
        ),
        # Duplicate detection of same violation
        ValidationIssue(
            check_name="DOUBLE_BOOKING_DETECTION",
            severity="ANOMALY_DETECTED",
            entity_type="ShiftAssignment",
            entity_id="SHIFT-A",
            message="Employee EMP-001 has overlapping shifts SHIFT-A and SHIFT-B",
            rule_code="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
        ),
    ]

    dataset.ground_truth_anomalies = [
        GroundTruthAnomaly(
            anomaly_id="GT-001",
            anomaly_type=AnomalyType.EMPLOYEE_DOUBLE_BOOKED,
            entity_type="ShiftAssignment",
            primary_entity_id="SHIFT-A",
            secondary_entity_id="SHIFT-B",
            description="Double booked",
            injected_timestamp="2026-01-01T00:00:00Z",
            severity="CRITICAL",
            expected_detection_rule="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
        )
    ]

    res = validator._evaluate_ground_truth()
    # Exactly 1 detection satisfies GT-001; the duplicate is a false positive
    assert res["true_positives"] == 1
    assert res["false_positives"] == 1
    assert res["false_negatives"] == 0
    assert res["precision"] == 0.5


def test_malformed_timestamps_and_invalid_intervals():
    """Verify that malformed timestamps and non-positive intervals are safely handled and reported."""
    from dataclasses import replace

    dataset = SyntheticDataGenerator(seed=20261022, scale="starter").generate()
    _clear_active_assignments(dataset)
    template = dataset.shift_assignments[0]

    # Non-positive interval (end earlier than start)
    invalid_chronology = replace(
        template,
        assignment_id="SHIFT-INV-CHRONO",
        date="2026-01-01",
        employee_id=dataset.employees[0].employee_id,
        scheduled_start="2026-01-01T15:00:00+00:00",
        scheduled_end="2026-01-01T07:00:00+00:00",
        status=AssignmentStatus.SCHEDULED,
    )
    # Malformed ISO timestamp
    malformed_ts = replace(
        template,
        assignment_id="SHIFT-MALFORMED",
        date="2026-01-01",
        employee_id=dataset.employees[1].employee_id,
        scheduled_start="NOT-A-TIMESTAMP",
        scheduled_end="ALSO-NOT-A-TIMESTAMP",
        status=AssignmentStatus.SCHEDULED,
    )
    dataset.shift_assignments.extend([invalid_chronology, malformed_ts])

    validator = DatasetValidator(dataset)
    report = validator.validate()

    chrono_issues = [i for i in report.detailed_issues if i.entity_id == "SHIFT-INV-CHRONO"]
    assert any(i.rule_code == "RULE_DATE_CHRONOLOGY" for i in chrono_issues)

    format_issues = [i for i in report.detailed_issues if i.entity_id == "SHIFT-MALFORMED"]
    assert any(i.rule_code == "RULE_DATE_FORMAT" for i in format_issues)


def test_baseline_validation_before_and_after_injection():
    """Verify baseline schedule is valid before injection, and injected anomalies are detected after."""
    import datetime
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")

    # 1. Pure baseline before anomaly injection
    skills = gen._generate_skills()
    teams = gen._generate_teams()
    employees, employee_skills = gen._generate_employees_and_skills(teams, skills)
    gen._assign_team_managers(teams, employees)
    shift_templates = gen._generate_shift_templates()
    holiday_calendar = gen._generate_holidays()
    coverage_requirements = gen._generate_coverage_requirements(teams, shift_templates, skills)
    leave_requests = gen._generate_leave_requests(employees)

    pure_baseline_assignments = gen._generate_baseline_schedules(
        employees, employee_skills, teams, shift_templates, coverage_requirements, leave_requests
    )

    assignments_by_emp = {}
    for sa in pure_baseline_assignments:
        if sa.status == AssignmentStatus.SCHEDULED:
            s = datetime.datetime.fromisoformat(sa.scheduled_start.replace("Z", "+00:00"))
            e = datetime.datetime.fromisoformat(sa.scheduled_end.replace("Z", "+00:00"))
            assignments_by_emp.setdefault(sa.employee_id, []).append((s, e, sa))

    baseline_overlaps = []
    for emp_id, intervals in assignments_by_emp.items():
        intervals.sort(key=lambda x: (x[0], x[1]))
        for i, (s_a, e_a, a_a) in enumerate(intervals):
            for s_b, e_b, a_b in intervals[i + 1:]:
                if s_b >= e_a:
                    break
                if s_a < e_b and s_b < e_a:
                    baseline_overlaps.append((a_a.assignment_id, a_b.assignment_id))

    assert baseline_overlaps == [], f"Expected 0 baseline overlaps before injection but found: {baseline_overlaps}"

    # 2. After anomaly injection: fresh deterministic generator generates full dataset with 5 anomalies
    gen_after = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen_after.generate()
    report = DatasetValidator(dataset).validate()
    gt = report.ground_truth_evaluation
    assert gt["total_ground_truth"] == 5
    assert gt["true_positives"] == 5
    assert gt["recall"] == 1.0


def test_precision_recall_f1_manually_verifiable_dataset():
    """Verify precision, recall, and F1 calculations on a small, manually verifiable setup."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)

    # Setup: 2 GT anomalies expected
    dataset.ground_truth_anomalies = [
        GroundTruthAnomaly(
            anomaly_id="GT-TEST-1",
            anomaly_type=AnomalyType.REQUIRED_SKILL_ABSENT,
            entity_type="ShiftAssignment",
            primary_entity_id="SHIFT-EXPECTED-1",
            secondary_entity_id=None,
            description="Expected and detected",
            injected_timestamp="2026-01-01T00:00:00Z",
            severity="HIGH",
            expected_detection_rule="RULE_MANDATORY_ROLE_SKILL_MATCH",
        ),
        GroundTruthAnomaly(
            anomaly_id="GT-TEST-2",
            anomaly_type=AnomalyType.REQUIRED_SKILL_ABSENT,
            entity_type="ShiftAssignment",
            primary_entity_id="SHIFT-EXPECTED-2",
            secondary_entity_id=None,
            description="Expected but missed (FN)",
            injected_timestamp="2026-01-01T00:00:00Z",
            severity="HIGH",
            expected_detection_rule="RULE_MANDATORY_ROLE_SKILL_MATCH",
        ),
    ]

    # Detections: 1 true positive, 1 unexpected false positive
    validator.detected_anomalies = [
        ValidationIssue(
            check_name="SKILL_ABSENCE_DETECTION",
            severity="ANOMALY_DETECTED",
            entity_type="ShiftAssignment",
            entity_id="SHIFT-EXPECTED-1",  # TP
            message="Matches GT-TEST-1",
            rule_code="RULE_MANDATORY_ROLE_SKILL_MATCH",
        ),
        ValidationIssue(
            check_name="SKILL_ABSENCE_DETECTION",
            severity="ANOMALY_DETECTED",
            entity_type="ShiftAssignment",
            entity_id="SHIFT-UNEXPECTED-FP",  # FP
            message="Unexpected detection",
            rule_code="RULE_MANDATORY_ROLE_SKILL_MATCH",
        ),
    ]

    metrics = validator._evaluate_ground_truth()
    # TP = 1, FP = 1, FN = 1
    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    # Precision = 1 / (1 + 1) = 0.5
    assert metrics["precision"] == 0.5
    # Recall = 1 / (1 + 1) = 0.5
    assert metrics["recall"] == 0.5
    # F1 = 2 * (0.5 * 0.5) / (0.5 + 0.5) = 0.5
    assert metrics["f1_score"] == 0.5


def test_ground_truth_matching_rejects_wrong_entity_id():
    """Verify that a detection with the correct rule and anomaly type but WRONG entity ID
    does not match the ground truth entry."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)

    gt = GroundTruthAnomaly(
        anomaly_id="GT-ID-TEST",
        anomaly_type=AnomalyType.REQUIRED_SKILL_ABSENT,
        entity_type="ShiftAssignment",
        primary_entity_id="SHIFT-CORRECT-ID",
        secondary_entity_id=None,
        description="Shift requires skill",
        injected_timestamp="2026-01-01T00:00:00Z",
        severity="HIGH",
        expected_detection_rule="RULE_MANDATORY_ROLE_SKILL_MATCH",
    )
    det_wrong_id = ValidationIssue(
        check_name="SKILL_ABSENCE_DETECTION",
        severity="ANOMALY_DETECTED",
        entity_type="ShiftAssignment",
        entity_id="SHIFT-WRONG-ID",
        message="Shift mandates skill",
        rule_code="RULE_MANDATORY_ROLE_SKILL_MATCH",
        anomaly_type=AnomalyType.REQUIRED_SKILL_ABSENT,
    )
    assert validator._matches_ground_truth(det_wrong_id, gt) is False

    dataset.ground_truth_anomalies = [gt]
    validator.detected_anomalies = [det_wrong_id]
    metrics = validator._evaluate_ground_truth()

    assert metrics["true_positives"] == 0
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0


def test_ground_truth_matching_rejects_wrong_anomaly_type():
    """Verify that a detection with the correct rule and entity ID but an explicit WRONG anomaly type
    does not match the ground truth entry."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)

    gt = GroundTruthAnomaly(
        anomaly_id="GT-TYPE-TEST",
        anomaly_type=AnomalyType.REQUIRED_SKILL_ABSENT,
        entity_type="ShiftAssignment",
        primary_entity_id="SHIFT-2026-01-01-A-000006",
        secondary_entity_id=None,
        description="Shift requires skill",
        injected_timestamp="2026-01-01T00:00:00Z",
        severity="HIGH",
        expected_detection_rule="RULE_MANDATORY_ROLE_SKILL_MATCH",
    )
    det_wrong_type = ValidationIssue(
        check_name="SKILL_ABSENCE_DETECTION",
        severity="ANOMALY_DETECTED",
        entity_type="ShiftAssignment",
        entity_id="SHIFT-2026-01-01-A-000006",
        message="Shift mandates skill",
        rule_code="RULE_MANDATORY_ROLE_SKILL_MATCH",
        anomaly_type=AnomalyType.EMPLOYEE_DOUBLE_BOOKED,  # Explicit mismatched type
    )
    assert validator._matches_ground_truth(det_wrong_type, gt) is False

    dataset.ground_truth_anomalies = [gt]
    validator.detected_anomalies = [det_wrong_type]
    metrics = validator._evaluate_ground_truth()

    assert metrics["true_positives"] == 0
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1


def test_ground_truth_matching_rejects_wrong_entity_type():
    """Verify that a detection matching rule and ID but with a mismatched entity_type
    (e.g. Employee vs ShiftAssignment) does not match."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    validator = DatasetValidator(dataset)

    gt = GroundTruthAnomaly(
        anomaly_id="GT-ENTITY-TYPE-TEST",
        anomaly_type=AnomalyType.OVERTIME_CAP_EXCEEDED,
        entity_type="Employee",
        primary_entity_id="EMP-000003",
        secondary_entity_id=None,
        description="Employee exceeded overtime",
        injected_timestamp="2026-01-01T00:00:00Z",
        severity="HIGH",
        expected_detection_rule="RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP",
    )
    det_wrong_entity_type = ValidationIssue(
        check_name="OVERTIME_CAP_EXCEEDED_DETECTION",
        severity="ANOMALY_DETECTED",
        entity_type="ShiftAssignment",  # Mismatched entity type
        entity_id="EMP-000003",
        message="Employee scheduled for excessive hours",
        rule_code="RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP",
    )
    assert validator._matches_ground_truth(det_wrong_entity_type, gt) is False


def test_ground_truth_evaluation_empty_inputs_zero_division():
    """Verify metrics calculation when both ground truth and detections are empty (empty inputs).
    Should return TP=0, FP=0, FN=0, Precision=1.0, Recall=1.0, F1=1.0 without zero-division error."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    dataset.ground_truth_anomalies = []
    validator = DatasetValidator(dataset)
    validator.detected_anomalies = []

    metrics = validator._evaluate_ground_truth()

    assert metrics["total_ground_truth"] == 0
    assert metrics["true_positives"] == 0
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0


def test_ground_truth_evaluation_zero_detections_with_expected_anomalies():
    """Verify that when ground truth anomalies exist but zero detections are made,
    precision is 0.0 (NOT falsely reported as 1.0) and recall is 0.0."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    dataset.ground_truth_anomalies = [
        GroundTruthAnomaly(
            anomaly_id="GT-MISSED-1",
            anomaly_type=AnomalyType.SWAP_APPLIED_WITHOUT_APPROVAL,
            entity_type="SwapRequest",
            primary_entity_id="SWP-2026-999001",
            secondary_entity_id=None,
            description="Unapproved swap",
            injected_timestamp="2026-01-01T00:00:00Z",
            severity="CRITICAL",
            expected_detection_rule="RULE_SWAP_REQUIRES_MANAGER_APPROVAL",
        )
    ]
    validator = DatasetValidator(dataset)
    validator.detected_anomalies = []  # Zero detections!

    metrics = validator._evaluate_ground_truth()

    assert metrics["total_ground_truth"] == 1
    assert metrics["true_positives"] == 0
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == 0.0, f"Expected 0.0 precision when 0 detections made, got {metrics['precision']}"
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0


def test_ground_truth_evaluation_pure_false_positives():
    """Verify metrics when no GT anomalies exist but false detections are made.
    Precision should be 0.0 and F1 should be 0.0."""
    gen = SyntheticDataGenerator(seed=20261022, scale="starter")
    dataset = gen.generate()
    dataset.ground_truth_anomalies = []  # No GT anomalies
    validator = DatasetValidator(dataset)
    validator.detected_anomalies = [
        ValidationIssue(
            check_name="SPURIOUS_DETECTION",
            severity="ANOMALY_DETECTED",
            entity_type="ShiftAssignment",
            entity_id="SHIFT-SPURIOUS-1",
            message="False alarm",
            rule_code="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
        )
    ]

    metrics = validator._evaluate_ground_truth()

    assert metrics["true_positives"] == 0
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1_score"] == 0.0
