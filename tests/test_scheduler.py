"""
Tests for Constraint-Based Fair Shift Scheduling Engine.
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
    assert res["total_files_verified"] >= 10
