"""
Tests for 8-Point Dataset Validator and Ground Truth Benchmarking (Step 8).
"""

import pytest
from data_generator.generator import SyntheticDataGenerator
from data_generator.validator import DatasetValidator


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
    assert gt["true_positives"] == 5
    assert gt["false_negatives"] == 0
    assert gt["false_positives"] == 0
    assert gt["precision"] == 1.0
    assert gt["recall"] == 1.0
    assert gt["f1_score"] == 1.0
