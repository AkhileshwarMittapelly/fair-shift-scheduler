"""Comprehensive tests for API correctness, persistence, database integrity, audit history, and attendance.
"""
from __future__ import annotations

import sqlite3
import pytest
from fastapi.testclient import TestClient

from server.app import app, get_or_load_dataset, get_authorized_managers
from server.persistence import (
    get_db_connection,
    run_database_integrity_check,
    load_dataset_from_db,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Provides a TestClient initialized with starter dataset."""
    with TestClient(app) as test_client:
        # Preload starter dataset and verify health
        resp = test_client.get("/api/health")
        assert resp.status_code == 200
        yield test_client


def test_database_integrity_endpoint(client: TestClient) -> None:
    """Verifies that the database integrity check returns HEALTHY with zero foreign key violations."""
    resp = client.get("/api/database/integrity?scale=starter")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert data["is_integrity_ok"] is True
    assert data["foreign_key_violations"] == []
    assert data["table_counts"]["employees"] > 0
    assert data["table_counts"]["shift_assignments"] > 0


def test_sqlite_foreign_key_enforcement() -> None:
    """Directly verifies that SQLite foreign key enforcement prevents invalid references."""
    conn = get_db_connection("starter")
    try:
        # Verify foreign keys are enabled
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1

        # Attempt to insert a shift_assignment with non-existent employee_id
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO shift_assignments (
                    assignment_id, date, shift_template_id, employee_id, team_id,
                    role_skill_id, scheduled_start, scheduled_end, status, created_at, created_by
                ) VALUES (
                    'TEST-INVALID-FK-001', '2026-01-01', 'TMPL-MORN', 'EMP-NONEXISTENT', 'TEAM-OPS-1',
                    NULL, '2026-01-01T07:00:00Z', '2026-01-01T15:30:00Z', 'SCHEDULED', '2026-01-01T00:00:00Z', 'SCHEDULER'
                )
                """
            )
            conn.commit()

        # Attempt to insert duplicate primary key into employees
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO employees (
                    employee_id, first_name, last_name, email, team_id,
                    hire_date, contract_hours_per_week, max_weekly_overtime_hours,
                    hourly_rate, employment_status, created_at
                ) VALUES (
                    'EMP-001', 'Dup', 'Emp', 'dup@example.com', 'TEAM-OPS-1',
                    '2026-01-01', 40.0, 10.0, 25.0, 'ACTIVE', '2026-01-01T00:00:00Z'
                )
                """
            )
            conn.commit()
    finally:
        conn.close()


def test_leave_request_lifecycle_validation_and_persistence(client: TestClient) -> None:
    """Tests validation, authorization, self-approval prevention, persistence, and audit logging for leave."""
    dataset = get_or_load_dataset("starter")
    emp = dataset.employees[0]

    # Find an authorized manager who is distinct from emp
    auth_managers = get_authorized_managers(dataset)
    assert len(auth_managers) > 0
    chosen_manager = None
    for m_id in auth_managers:
        if m_id != emp.employee_id:
            chosen_manager = m_id
            break
    if not chosen_manager:
        chosen_manager = list(auth_managers)[0]

    # 1. Invalid employee -> 400
    bad_emp_resp = client.post(
        "/api/leaves/create?scale=starter",
        json={
            "employee_id": "EMP-DOES-NOT-EXIST",
            "start_date": "2026-01-10",
            "end_date": "2026-01-12",
            "leave_type": "VACATION",
            "reason": "Test trip",
        },
    )
    assert bad_emp_resp.status_code == 400
    assert "not found" in bad_emp_resp.json()["detail"].lower()

    # 2. Invalid date ordering -> 400
    bad_date_resp = client.post(
        "/api/leaves/create?scale=starter",
        json={
            "employee_id": emp.employee_id,
            "start_date": "2026-01-12",
            "end_date": "2026-01-10",
            "leave_type": "VACATION",
            "reason": "Test trip",
        },
    )
    assert bad_date_resp.status_code == 400
    assert "end_date must be >= start_date" in bad_date_resp.json()["detail"]

    # 3. Invalid leave type -> 400
    bad_type_resp = client.post(
        "/api/leaves/create?scale=starter",
        json={
            "employee_id": emp.employee_id,
            "start_date": "2026-01-10",
            "end_date": "2026-01-12",
            "leave_type": "PARTY_TIME",
            "reason": "Test trip",
        },
    )
    assert bad_type_resp.status_code == 400
    assert "invalid leave_type" in bad_type_resp.json()["detail"].lower()

    # 4. Valid leave request creation
    create_resp = client.post(
        "/api/leaves/create?scale=starter",
        json={
            "employee_id": emp.employee_id,
            "start_date": "2026-01-15",
            "end_date": "2026-01-17",
            "leave_type": "ANNUAL",
            "reason": "Family vacation",
        },
    )
    assert create_resp.status_code == 200
    created_data = create_resp.json()
    assert created_data["success"] is True
    assert created_data["persisted"] is True
    leave_id = created_data["leave_id"]
    assert leave_id.startswith("LVE-")

    # 5a. Non-existent manager decision -> 400
    nonexist_resp = client.post(
        f"/api/leaves/{leave_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": "NOT-AN-EMPLOYEE",
            "decision_notes": "Nonexistent attempt",
        },
    )
    assert nonexist_resp.status_code == 400
    assert "does not exist" in nonexist_resp.json()["detail"].lower()

    # 5b. Unauthorized existing employee decision -> 403
    unauth_emp = next(e.employee_id for e in dataset.employees if e.employee_id not in auth_managers and e.employee_id != emp.employee_id)
    unauth_resp = client.post(
        f"/api/leaves/{leave_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": unauth_emp,
            "decision_notes": "Unauthorized attempt",
        },
    )
    assert unauth_resp.status_code == 403
    assert "not authorized" in unauth_resp.json()["detail"].lower()

    # 6. Self-approval prevention -> 403
    self_approve_resp = client.post(
        f"/api/leaves/{leave_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": emp.employee_id,
            "decision_notes": "Self approval attempt",
        },
    )
    assert self_approve_resp.status_code == 403
    assert "cannot approve their own leave" in self_approve_resp.json()["detail"].lower()

    # 7. Valid manager decision -> 200, persisted
    valid_dec_resp = client.post(
        f"/api/leaves/{leave_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": chosen_manager,
            "decision_notes": "Approved for vacation",
        },
    )
    assert valid_dec_resp.status_code == 200
    dec_data = valid_dec_resp.json()
    assert dec_data["success"] is True
    assert dec_data["persisted"] is True
    assert dec_data["status"] == "APPROVED"

    # 8. Attempting to overwrite a finalized leave -> 400
    overwrite_resp = client.post(
        f"/api/leaves/{leave_id}/decide?scale=starter",
        json={
            "decision": "REJECTED",
            "decision_by": chosen_manager,
            "decision_notes": "Attempt to overwrite finalized status",
        },
    )
    assert overwrite_resp.status_code == 400
    assert "already finalized" in overwrite_resp.json()["detail"].lower()

    # 9. Verify persistence across simulated restart
    reloaded_dataset = get_or_load_dataset("starter", reload=True)
    reloaded_leave = next((l for l in reloaded_dataset.leave_requests if l.leave_id == leave_id), None)
    assert reloaded_leave is not None
    assert reloaded_leave.status.value == "APPROVED"
    assert reloaded_leave.decision_by == chosen_manager

    # Verify audit logs and state transitions exist in SQLite
    conn = get_db_connection("starter")
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM leave_state_transitions WHERE leave_id = ?",
            (leave_id,),
        )
        assert cur.fetchone()[0] >= 1

        cur.execute(
            "SELECT count(*) FROM audit_logs WHERE entity_type = 'LEAVE_REQUEST' AND entity_id = ?",
            (leave_id,),
        )
        assert cur.fetchone()[0] >= 1
    finally:
        conn.close()


def test_shift_swap_lifecycle_validation_and_persistence(client: TestClient) -> None:
    """Tests validation, authorization, self-approval prevention, business rules, and persistence for shift swaps."""
    dataset = get_or_load_dataset("starter")
    auth_managers = get_authorized_managers(dataset)
    assert len(auth_managers) > 0

    # Pick two assignments from different employees
    a1 = dataset.shift_assignments[0]
    a2 = None
    for a in dataset.shift_assignments[1:]:
        if a.employee_id != a1.employee_id:
            a2 = a
            break
    assert a2 is not None

    chosen_manager = None
    for m_id in auth_managers:
        if m_id not in {a1.employee_id, a2.employee_id}:
            chosen_manager = m_id
            break
    if not chosen_manager:
        chosen_manager = list(auth_managers)[0]

    # 1. Invalid assignment -> 400
    bad_asgn_resp = client.post(
        "/api/swaps/request?scale=starter",
        json={
            "requester_assignment_id": "ASGN-NONEXISTENT",
            "target_assignment_id": a2.assignment_id,
        },
    )
    assert bad_asgn_resp.status_code == 400

    # 2. Same employee assignment swap -> 400
    same_emp_a2 = next(a for a in dataset.shift_assignments if a.employee_id == a1.employee_id and a.assignment_id != a1.assignment_id)
    same_emp_resp = client.post(
        "/api/swaps/request?scale=starter",
        json={
            "requester_assignment_id": a1.assignment_id,
            "target_assignment_id": same_emp_a2.assignment_id,
        },
    )
    assert same_emp_resp.status_code == 400
    assert "same employee" in same_emp_resp.json()["detail"].lower()

    # 3. Valid swap creation
    swap_resp = client.post(
        "/api/swaps/request?scale=starter",
        json={
            "requester_assignment_id": a1.assignment_id,
            "target_assignment_id": a2.assignment_id,
        },
    )
    assert swap_resp.status_code == 200
    swap_data = swap_resp.json()
    assert swap_data["success"] is True
    assert swap_data["persisted"] is True
    swap_id = swap_data["swap_id"]

    # 4a. Non-existent manager -> 400
    nonexist_resp = client.post(
        f"/api/swaps/{swap_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": "FAKE-EMPLOYEE",
            "decision_notes": "Attempting nonexistent swap decision",
        },
    )
    assert nonexist_resp.status_code == 400

    # 4b. Unauthorized existing employee -> 403
    unauth_swap_emp = next(
        e.employee_id
        for e in dataset.employees
        if e.employee_id not in auth_managers and e.employee_id not in {a1.employee_id, a2.employee_id}
    )
    unauth_resp = client.post(
        f"/api/swaps/{swap_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": unauth_swap_emp,
            "decision_notes": "Attempting unauth swap decision",
        },
    )
    assert unauth_resp.status_code == 403

    # 5. Self approval attempt -> 403
    self_approve_resp = client.post(
        f"/api/swaps/{swap_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": a1.employee_id,
            "decision_notes": "Self approval swap attempt",
        },
    )
    assert self_approve_resp.status_code == 403

    # 6. Authorized manager rejection -> 200, persisted
    dec_resp = client.post(
        f"/api/swaps/{swap_id}/decide?scale=starter",
        json={
            "decision": "REJECTED",
            "decision_by": chosen_manager,
            "decision_notes": "Rejected due to coverage requirements",
        },
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["persisted"] is True
    assert dec_resp.json()["status"] == "REJECTED"

    # 7. Attempting to overwrite a finalized swap -> 400
    overwrite_resp = client.post(
        f"/api/swaps/{swap_id}/decide?scale=starter",
        json={
            "decision": "APPROVED",
            "decision_by": chosen_manager,
            "decision_notes": "Overwriting rejected swap",
        },
    )
    assert overwrite_resp.status_code == 400
    assert "finalized" in overwrite_resp.json()["detail"].lower()

    # 8. Verify swap state transition and audit logging in DB
    conn = get_db_connection("starter")
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM swap_state_transitions WHERE swap_id = ?", (swap_id,))
        assert cur.fetchone()[0] >= 1

        cur.execute(
            "SELECT count(*) FROM audit_logs WHERE entity_type = 'SWAP_REQUEST' AND entity_id = ?",
            (swap_id,),
        )
        assert cur.fetchone()[0] >= 1
    finally:
        conn.close()


def test_attendance_punch_validation_and_variance(client: TestClient) -> None:
    """Tests attendance punch validation, duplicate debounce, schedule variance computation, and persistence."""
    dataset = get_or_load_dataset("starter")
    assignment = dataset.shift_assignments[0]

    # Shift scheduled_start is e.g. "2026-01-01T07:00:00Z"
    # Punch in 5 minutes late: +5 mins from scheduled start
    start_dt_str = assignment.scheduled_start.replace("Z", "")
    base_date = start_dt_str.split("T")[0]
    # Craft punch 5 mins after scheduled start
    start_time_part = start_dt_str.split("T")[1]
    hr, mn, sc = [int(p) for p in start_time_part.split(":")[:3]]
    punch_in_iso = f"{base_date}T{hr:02d}:{mn+5:02d}:{sc:02d}Z"

    # 1. Non-existent employee -> 400
    bad_emp_resp = client.post(
        "/api/attendance/punch?scale=starter",
        json={
            "employee_id": "EMP-DOES-NOT-EXIST",
            "assignment_id": assignment.assignment_id,
            "event_type": "CLOCK_IN",
            "event_timestamp": punch_in_iso,
        },
    )
    assert bad_emp_resp.status_code == 400

    # 2. Assignment not assigned to employee -> 400
    other_emp = next(e for e in dataset.employees if e.employee_id != assignment.employee_id)
    mismatch_resp = client.post(
        "/api/attendance/punch?scale=starter",
        json={
            "employee_id": other_emp.employee_id,
            "assignment_id": assignment.assignment_id,
            "event_type": "CLOCK_IN",
            "event_timestamp": punch_in_iso,
        },
    )
    assert mismatch_resp.status_code == 400
    assert "is assigned to" in mismatch_resp.json()["detail"]

    # 3. Out-of-range punch (>12h away) -> 400
    out_of_range_resp = client.post(
        "/api/attendance/punch?scale=starter",
        json={
            "employee_id": assignment.employee_id,
            "assignment_id": assignment.assignment_id,
            "event_type": "CLOCK_IN",
            "event_timestamp": "2026-06-01T07:00:00Z",  # Months away
        },
    )
    assert out_of_range_resp.status_code == 400
    assert "out of range" in out_of_range_resp.json()["detail"].lower()

    # 4. Valid punch in -> 200, checks calculated schedule difference
    punch_resp = client.post(
        "/api/attendance/punch?scale=starter",
        json={
            "employee_id": assignment.employee_id,
            "assignment_id": assignment.assignment_id,
            "event_type": "CLOCK_IN",
            "event_timestamp": punch_in_iso,
        },
    )
    assert punch_resp.status_code == 200
    pdata = punch_resp.json()
    assert pdata["success"] is True
    assert pdata["persisted"] is True
    assert pdata["attendance_id"].startswith("ATT-")
    # Verified schedule variance calculation: scheduled start + 5 min -> diff = +5.0 min
    assert pdata["matched_schedule_diff_minutes"] == pytest.approx(5.0, abs=0.1)

    # 5. Duplicate punch on same assignment -> 400
    dup_resp = client.post(
        "/api/attendance/punch?scale=starter",
        json={
            "employee_id": assignment.employee_id,
            "assignment_id": assignment.assignment_id,
            "event_type": "CLOCK_IN",
            "event_timestamp": punch_in_iso,
        },
    )
    assert dup_resp.status_code == 400
    assert "duplicate punch detected" in dup_resp.json()["detail"].lower()

    # 6. Verify punch persistence across reload
    reloaded_dataset = get_or_load_dataset("starter", reload=True)
    persisted_punch = next(
        (p for p in reloaded_dataset.attendance_events if p.attendance_id == pdata["attendance_id"]),
        None,
    )
    assert persisted_punch is not None
    assert persisted_punch.matched_schedule_diff_minutes == pytest.approx(5.0, abs=0.1)


def test_scheduler_engine_persistence_flags(client: TestClient) -> None:
    """Verifies that the scheduler run endpoint respects save_results flag and reports persisted state."""
    # 1. Run without saving
    resp_nosave = client.post(
        "/api/scheduler/run?save_results=false"
    )
    assert resp_nosave.status_code == 200
    data_nosave = resp_nosave.json()
    assert data_nosave["persisted"] is False
    assert data_nosave["total_scheduled_shifts"] > 0

    # 2. Run with saving
    resp_save = client.post(
        "/api/scheduler/run?save_results=true"
    )
    assert resp_save.status_code == 200
    data_save = resp_save.json()
    assert data_save["persisted"] is True


def test_audit_logs_query(client: TestClient) -> None:
    """Verifies the audit log query endpoint returns structured logs."""
    # Ensure at least one audit record is present by performing a request
    client.post(
        "/api/leaves/create?scale=starter",
        json={
            "employee_id": "EMP-001",
            "start_date": "2026-02-01",
            "end_date": "2026-02-02",
            "leave_type": "VACATION",
            "reason": "Audit verification leave",
        },
    )
    resp = client.get("/api/audit/logs?scale=starter&limit=50")
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    first_log = logs[0]
    assert "entity_type" in first_log
    assert "entity_id" in first_log
    assert "actor_id" in first_log
    assert "timestamp" in first_log
