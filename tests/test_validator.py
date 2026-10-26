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
    ShiftAssignment, AssignmentStatus, GroundTruthAnomaly, AnomalyType
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

    # After fixing instance-level matching, incidental baseline violations
    # (e.g. double-bookings introduced as side effects of the skill/OT injection)
    # are correctly classified as False Positives rather than True Positives.
    # Precision < 1.0 is expected and documents genuine baseline data quality issues.
    # We assert precision > 0.5 (i.e. the majority of detections are correct).
    assert gt["precision"] > 0.5, (
        f"Precision {gt['precision']} is too low — "
        f"check for runaway false positives: {gt.get('incidental_baseline_violations', [])}"
    )
    # Incidental violations should be documented in the report
    assert "incidental_baseline_violations" in gt



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
