"""
Persistence and Database Integrity Management for Fair Shift Scheduler.
Handles SQLite connections with foreign-key enforcement, state loading across restarts,
atomic transactions, state transition event tracking, and audit logging.
"""

from __future__ import annotations
import sqlite3
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def generate_log_id(prefix: str = "AUD") -> str:
    now_tag = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"{prefix}-{now_tag}-{uuid.uuid4().hex[:8]}"


def generate_event_id(prefix: str) -> str:
    now_tag = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"{prefix}-{now_tag}-{uuid.uuid4().hex[:6]}"

from data_generator.models import (
    EmploymentStatus,
    SkillCategory,
    ProficiencyLevel,
    ShiftCode,
    LeaveType,
    LeaveStatus,
    AssignmentStatus,
    SwapStatus,
    AttendanceEventType,
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
    LeaveStateTransitionEvent,
    SwapStateTransitionEvent,
)
from data_generator.generator import GeneratedDataset, SyntheticDataGenerator
from data_generator.export import DatasetExporter


def get_db_path(scale: str = "starter") -> Path:
    return Path(f"data/{scale.lower()}/scheduler.db")


def get_db_connection(scale: str = "starter") -> sqlite3.Connection:
    """
    Returns an open SQLite connection with foreign keys enabled and row_factory configured.
    Initializes required audit and transition tables if not present.
    """
    db_path = get_db_path(scale)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row

    # Ensure auxiliary audit and state-transition tables exist
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS leave_state_transitions (
        event_id TEXT PRIMARY KEY,
        leave_id TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT NOT NULL,
        changed_by TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (leave_id) REFERENCES leave_requests(leave_id),
        FOREIGN KEY (changed_by) REFERENCES employees(employee_id)
    );

    CREATE TABLE IF NOT EXISTS swap_state_transitions (
        event_id TEXT PRIMARY KEY,
        swap_id TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT NOT NULL,
        changed_by TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (swap_id) REFERENCES swap_requests(swap_id),
        FOREIGN KEY (changed_by) REFERENCES employees(employee_id)
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        action TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        before_state TEXT,
        after_state TEXT,
        notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
    CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_id);
    """)
    conn.commit()
    return conn


def load_dataset_from_db(scale: str = "starter", seed: int = 20261022) -> GeneratedDataset:
    """
    Loads complete dataset from SQLite database scheduler.db, ensuring state survives restart.
    If database does not exist, generates dataset and exports initial SQLite tables.
    """
    db_path = get_db_path(scale)
    if not db_path.exists():
        gen = SyntheticDataGenerator(seed=seed, scale=scale)
        dataset = gen.generate()
        exporter = DatasetExporter(dataset, str(db_path.parent))
        exporter.export_sqlite()
        return dataset

    conn = get_db_connection(scale)
    cur = conn.cursor()

    skills = [
        Skill(
            skill_id=r["skill_id"],
            skill_name=r["skill_name"],
            category=SkillCategory(r["category"]),
            minimum_certification_level=ProficiencyLevel(r["minimum_certification_level"]),
            description=r["description"] or "",
        )
        for r in cur.execute("SELECT * FROM skills ORDER BY skill_id")
    ]

    teams = [
        Team(
            team_id=r["team_id"],
            team_name=r["team_name"],
            department=r["department"],
            manager_id=r["manager_id"],
            location=r["location"],
            max_overtime_hours_per_week=float(r["max_overtime_hours_per_week"]),
            created_at=r["created_at"],
        )
        for r in cur.execute("SELECT * FROM teams ORDER BY team_id")
    ]

    employees = [
        Employee(
            employee_id=r["employee_id"],
            first_name=r["first_name"],
            last_name=r["last_name"],
            email=r["email"],
            team_id=r["team_id"],
            hire_date=r["hire_date"],
            contract_hours_per_week=float(r["contract_hours_per_week"]),
            max_weekly_overtime_hours=float(r["max_weekly_overtime_hours"]),
            hourly_rate=float(r["hourly_rate"]),
            employment_status=EmploymentStatus(r["employment_status"]),
            created_at=r["created_at"],
        )
        for r in cur.execute("SELECT * FROM employees ORDER BY employee_id")
    ]

    employee_skills = [
        EmployeeSkill(
            employee_skill_id=r["employee_skill_id"],
            employee_id=r["employee_id"],
            skill_id=r["skill_id"],
            proficiency_level=ProficiencyLevel(r["proficiency_level"]),
            certified_date=r["certified_date"],
            expiry_date=r["expiry_date"],
        )
        for r in cur.execute("SELECT * FROM employee_skills ORDER BY employee_skill_id")
    ]

    shift_templates = [
        ShiftTemplate(
            shift_template_id=r["shift_template_id"],
            shift_code=ShiftCode(r["shift_code"]),
            shift_name=r["shift_name"],
            start_time=r["start_time"],
            end_time=r["end_time"],
            duration_hours=float(r["duration_hours"]),
            is_overnight=bool(r["is_overnight"]),
            differential_rate_multiplier=float(r["differential_rate_multiplier"]),
        )
        for r in cur.execute("SELECT * FROM shift_templates ORDER BY shift_template_id")
    ]

    holiday_calendar = [
        HolidayCalendar(
            holiday_id=r["holiday_id"],
            holiday_date=r["holiday_date"],
            holiday_name=r["holiday_name"],
            region=r["region"],
            is_mandatory_off=bool(r["is_mandatory_off"]),
        )
        for r in cur.execute("SELECT * FROM holiday_calendar ORDER BY holiday_id")
    ]

    coverage_requirements = [
        CoverageRequirement(
            requirement_id=r["requirement_id"],
            date=r["date"],
            shift_template_id=r["shift_template_id"],
            team_id=r["team_id"],
            skill_id=r["skill_id"],
            min_headcount=int(r["min_headcount"]),
            target_headcount=int(r["target_headcount"]),
            priority_weight=float(r["priority_weight"]),
        )
        for r in cur.execute("SELECT * FROM coverage_requirements ORDER BY requirement_id")
    ]

    leave_requests = [
        LeaveRequest(
            leave_id=r["leave_id"],
            employee_id=r["employee_id"],
            start_date=r["start_date"],
            end_date=r["end_date"],
            leave_type=LeaveType(r["leave_type"]),
            status=LeaveStatus(r["status"]),
            reason=r["reason"],
            decision_by=r["decision_by"],
            decision_timestamp=r["decision_timestamp"],
            decision_notes=r["decision_notes"],
        )
        for r in cur.execute("SELECT * FROM leave_requests ORDER BY rowid DESC")
    ]

    shift_assignments = [
        ShiftAssignment(
            assignment_id=r["assignment_id"],
            date=r["date"],
            shift_template_id=r["shift_template_id"],
            employee_id=r["employee_id"],
            team_id=r["team_id"],
            role_skill_id=r["role_skill_id"],
            scheduled_start=r["scheduled_start"],
            scheduled_end=r["scheduled_end"],
            status=AssignmentStatus(r["status"]),
            created_at=r["created_at"],
            created_by=r["created_by"],
        )
        for r in cur.execute("SELECT * FROM shift_assignments ORDER BY scheduled_start")
    ]

    swap_requests = [
        SwapRequest(
            swap_id=r["swap_id"],
            requester_assignment_id=r["requester_assignment_id"],
            target_assignment_id=r["target_assignment_id"],
            requester_employee_id=r["requester_employee_id"],
            target_employee_id=r["target_employee_id"],
            status=SwapStatus(r["status"]),
            requested_at=r["requested_at"],
            peer_agreed_at=r["peer_agreed_at"],
            manager_decision_by=r["manager_decision_by"],
            manager_decision_at=r["manager_decision_at"],
            decision_notes=r["decision_notes"],
        )
        for r in cur.execute("SELECT * FROM swap_requests ORDER BY rowid DESC")
    ]

    attendance_events = [
        AttendanceEvent(
            attendance_id=r["attendance_id"],
            employee_id=r["employee_id"],
            assignment_id=r["assignment_id"],
            event_type=AttendanceEventType(r["event_type"]),
            event_timestamp=r["event_timestamp"],
            source_device=r["source_device"],
            matched_schedule_diff_minutes=float(r["matched_schedule_diff_minutes"]),
        )
        for r in cur.execute("SELECT * FROM attendance_events ORDER BY event_timestamp DESC")
    ]

    conn.close()

    # Load ground truth anomalies from disk if available
    gt_path = db_path.parent / "ground_truth.json"
    ground_truth_anomalies: List[GroundTruthAnomaly] = []
    if gt_path.exists():
        try:
            with open(gt_path, "r", encoding="utf-8") as f:
                gt_raw = json.load(f)
                for item in gt_raw:
                    ground_truth_anomalies.append(
                        GroundTruthAnomaly(
                            anomaly_id=item["anomaly_id"],
                            anomaly_type=item["anomaly_type"],
                            entity_type=item["entity_type"],
                            primary_entity_id=item["primary_entity_id"],
                            secondary_entity_id=item.get("secondary_entity_id"),
                            description=item["description"],
                            injected_timestamp=item.get("injected_timestamp", ""),
                            severity=item.get("severity", "CRITICAL"),
                            expected_detection_rule=item.get("expected_detection_rule", ""),
                        )
                    )
        except Exception:
            pass

    metadata = {
        "scale": scale,
        "seed": seed,
        "start_date": "2026-01-01",
        "num_days": 14 if scale == "starter" else 90,
    }

    return GeneratedDataset(
        scale=scale,
        seed=seed,
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
        ground_truth_anomalies=ground_truth_anomalies,
        metadata=metadata,
    )


# -----------------------------------------------------------------------------
# Atomic Persistence Operations with Audit Logging
# -----------------------------------------------------------------------------

def persist_leave_created(leave: LeaveRequest, actor_id: str, scale: str = "starter") -> None:
    conn = get_db_connection(scale)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev_id = generate_event_id(f"LSTE-{leave.leave_id}")
    log_id = generate_log_id("AUD")

    with conn:
        conn.execute(
            """
            INSERT INTO leave_requests (
                leave_id, employee_id, start_date, end_date, leave_type,
                status, reason, decision_by, decision_timestamp, decision_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                leave.leave_id,
                leave.employee_id,
                leave.start_date,
                leave.end_date,
                leave.leave_type.value,
                leave.status.value,
                leave.reason,
                leave.decision_by,
                leave.decision_timestamp,
                leave.decision_notes,
            ),
        )
        conn.execute(
            """
            INSERT INTO leave_state_transitions (
                event_id, leave_id, from_status, to_status, changed_by, timestamp, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (ev_id, leave.leave_id, None, leave.status.value, actor_id, now_str, "Initial leave request submission"),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                log_id, entity_type, entity_id, action, actor_id, timestamp, before_state, after_state, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                "LEAVE_REQUEST",
                leave.leave_id,
                "CREATE",
                actor_id,
                now_str,
                None,
                json.dumps(leave.to_dict()),
                leave.reason,
            ),
        )
    conn.close()


def persist_leave_decision(
    leave: LeaveRequest,
    from_status: str,
    actor_id: str,
    scale: str = "starter"
) -> None:
    conn = get_db_connection(scale)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev_id = generate_event_id(f"LSTE-{leave.leave_id}")
    log_id = generate_log_id("AUD")

    with conn:
        conn.execute(
            """
            UPDATE leave_requests
            SET status = ?, decision_by = ?, decision_timestamp = ?, decision_notes = ?
            WHERE leave_id = ?
            """,
            (
                leave.status.value,
                leave.decision_by,
                leave.decision_timestamp,
                leave.decision_notes,
                leave.leave_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO leave_state_transitions (
                event_id, leave_id, from_status, to_status, changed_by, timestamp, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev_id,
                leave.leave_id,
                from_status,
                leave.status.value,
                actor_id,
                now_str,
                leave.decision_notes,
            ),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                log_id, entity_type, entity_id, action, actor_id, timestamp, before_state, after_state, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                "LEAVE_REQUEST",
                leave.leave_id,
                leave.status.value,
                actor_id,
                now_str,
                json.dumps({"status": from_status}),
                json.dumps(leave.to_dict()),
                leave.decision_notes,
            ),
        )
    conn.close()


def persist_swap_created(swap: SwapRequest, actor_id: str, scale: str = "starter") -> None:
    conn = get_db_connection(scale)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev_id = generate_event_id(f"SSTE-{swap.swap_id}")
    log_id = generate_log_id("AUD")

    with conn:
        conn.execute(
            """
            INSERT INTO swap_requests (
                swap_id, requester_assignment_id, target_assignment_id,
                requester_employee_id, target_employee_id, status, requested_at,
                peer_agreed_at, manager_decision_by, manager_decision_at, decision_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                swap.swap_id,
                swap.requester_assignment_id,
                swap.target_assignment_id,
                swap.requester_employee_id,
                swap.target_employee_id,
                swap.status.value,
                swap.requested_at,
                swap.peer_agreed_at,
                swap.manager_decision_by,
                swap.manager_decision_at,
                swap.decision_notes,
            ),
        )
        conn.execute(
            """
            INSERT INTO swap_state_transitions (
                event_id, swap_id, from_status, to_status, changed_by, timestamp, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev_id,
                swap.swap_id,
                None,
                swap.status.value,
                actor_id,
                now_str,
                "Peer swap request initiated",
            ),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                log_id, entity_type, entity_id, action, actor_id, timestamp, before_state, after_state, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                "SWAP_REQUEST",
                swap.swap_id,
                "CREATE",
                actor_id,
                now_str,
                None,
                json.dumps(swap.to_dict()),
                "Shift swap request created",
            ),
        )
    conn.close()


def persist_swap_decision(
    swap: SwapRequest,
    asgn1: Optional[ShiftAssignment],
    asgn2: Optional[ShiftAssignment],
    from_status: str,
    actor_id: str,
    scale: str = "starter",
) -> None:
    conn = get_db_connection(scale)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ev_id = generate_event_id(f"SSTE-{swap.swap_id}")
    log_id = generate_log_id("AUD")

    with conn:
        conn.execute(
            """
            UPDATE swap_requests
            SET status = ?, manager_decision_by = ?, manager_decision_at = ?, decision_notes = ?
            WHERE swap_id = ?
            """,
            (
                swap.status.value,
                swap.manager_decision_by,
                swap.manager_decision_at,
                swap.decision_notes,
                swap.swap_id,
            ),
        )
        if swap.status == SwapStatus.APPLIED and asgn1 and asgn2:
            conn.execute(
                """
                UPDATE shift_assignments
                SET employee_id = ?, status = ?
                WHERE assignment_id = ?
                """,
                (asgn1.employee_id, asgn1.status.value, asgn1.assignment_id),
            )
            conn.execute(
                """
                UPDATE shift_assignments
                SET employee_id = ?, status = ?
                WHERE assignment_id = ?
                """,
                (asgn2.employee_id, asgn2.status.value, asgn2.assignment_id),
            )
        conn.execute(
            """
            INSERT INTO swap_state_transitions (
                event_id, swap_id, from_status, to_status, changed_by, timestamp, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev_id,
                swap.swap_id,
                from_status,
                swap.status.value,
                actor_id,
                now_str,
                swap.decision_notes,
            ),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                log_id, entity_type, entity_id, action, actor_id, timestamp, before_state, after_state, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                "SWAP_REQUEST",
                swap.swap_id,
                swap.status.value,
                actor_id,
                now_str,
                json.dumps({"status": from_status}),
                json.dumps(swap.to_dict()),
                swap.decision_notes,
            ),
        )
    conn.close()


def persist_attendance_punch(event: AttendanceEvent, scale: str = "starter") -> None:
    conn = get_db_connection(scale)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_id = generate_log_id("AUD")

    with conn:
        conn.execute(
            """
            INSERT INTO attendance_events (
                attendance_id, employee_id, assignment_id, event_type,
                event_timestamp, source_device, matched_schedule_diff_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(attendance_id) DO UPDATE SET
                employee_id = excluded.employee_id,
                assignment_id = excluded.assignment_id,
                event_type = excluded.event_type,
                event_timestamp = excluded.event_timestamp,
                source_device = excluded.source_device,
                matched_schedule_diff_minutes = excluded.matched_schedule_diff_minutes
            """,
            (
                event.attendance_id,
                event.employee_id,
                event.assignment_id,
                event.event_type.value,
                event.event_timestamp,
                event.source_device,
                event.matched_schedule_diff_minutes,
            ),
        )
        conn.execute(
            """
            INSERT INTO audit_logs (
                log_id, entity_type, entity_id, action, actor_id, timestamp, before_state, after_state, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                "ATTENDANCE_EVENT",
                event.attendance_id,
                event.event_type.value,
                event.employee_id,
                now_str,
                None,
                json.dumps(event.to_dict()),
                f"Clock punch via {event.source_device} (Variance: {event.matched_schedule_diff_minutes:+.1f}m)",
            ),
        )
    conn.close()


def persist_scheduler_results(
    assignments: List[ShiftAssignment],
    scale: str = "starter",
    actor_id: str = "FAIR_SOLVER_ENGINE"
) -> None:
    conn = get_db_connection(scale)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log_id = generate_log_id("AUD")

    with conn:
        # Upsert assignments to preserve referential integrity with swap_requests and attendance_events
        conn.executemany(
            """
            INSERT INTO shift_assignments (
                assignment_id, date, shift_template_id, employee_id, team_id,
                role_skill_id, scheduled_start, scheduled_end, status, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(assignment_id) DO UPDATE SET
                date = excluded.date,
                shift_template_id = excluded.shift_template_id,
                employee_id = excluded.employee_id,
                team_id = excluded.team_id,
                role_skill_id = excluded.role_skill_id,
                scheduled_start = excluded.scheduled_start,
                scheduled_end = excluded.scheduled_end,
                status = excluded.status,
                created_at = excluded.created_at,
                created_by = excluded.created_by
            """,
            [
                (
                    a.assignment_id,
                    a.date,
                    a.shift_template_id,
                    a.employee_id,
                    a.team_id,
                    a.role_skill_id,
                    a.scheduled_start,
                    a.scheduled_end,
                    a.status.value if hasattr(a.status, "value") else str(a.status),
                    a.created_at,
                    a.created_by,
                )
                for a in assignments
            ],
        )

        new_ids = [a.assignment_id for a in assignments]
        if new_ids:
            placeholders = ",".join("?" for _ in new_ids)
            conn.execute(
                f"""
                DELETE FROM shift_assignments
                WHERE assignment_id NOT IN ({placeholders})
                  AND assignment_id NOT IN (
                      SELECT requester_assignment_id FROM swap_requests
                      UNION
                      SELECT target_assignment_id FROM swap_requests
                      UNION
                      SELECT assignment_id FROM attendance_events WHERE assignment_id IS NOT NULL
                  )
                """,
                new_ids,
            )
        conn.execute(
            """
            INSERT INTO audit_logs (
                log_id, entity_type, entity_id, action, actor_id, timestamp, before_state, after_state, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log_id,
                "SHIFT_ASSIGNMENT",
                "BATCH",
                "OPTIMIZE_SCHEDULE",
                actor_id,
                now_str,
                None,
                json.dumps({"total_shifts": len(assignments)}),
                f"Full scheduler optimization run saved {len(assignments)} shifts",
            ),
        )
    conn.close()


def query_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    limit: int = 100,
    scale: str = "starter",
) -> List[Dict[str, Any]]:
    conn = get_db_connection(scale)
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params: List[Any] = []
    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    if entity_id:
        query += " AND entity_id = ?"
        params.append(entity_id)
    if actor_id:
        query += " AND actor_id = ?"
        params.append(actor_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def run_database_integrity_check(scale: str = "starter") -> Dict[str, Any]:
    """
    Executes SQLite PRAGMA integrity_check and PRAGMA foreign_key_check.
    Returns status and detailed violation reports.
    """
    conn = get_db_connection(scale)
    cur = conn.cursor()

    cur.execute("PRAGMA integrity_check;")
    integrity_rows = cur.fetchall()
    integrity_ok = len(integrity_rows) == 1 and integrity_rows[0][0] == "ok"

    cur.execute("PRAGMA foreign_key_check;")
    fk_rows = cur.fetchall()
    fk_violations = [
        {
            "table": r[0],
            "rowid": r[1],
            "parent_table": r[2],
            "fkid": r[3],
        }
        for r in fk_rows
    ]
    tables = [
        "employees", "teams", "skills", "employee_skills", "shift_templates",
        "holiday_calendar", "coverage_requirements", "leave_requests",
        "shift_assignments", "swap_requests", "attendance_events",
        "leave_state_transitions", "swap_state_transitions", "audit_logs"
    ]
    table_counts = {}
    for tbl in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tbl};")
            table_counts[tbl] = cur.fetchone()[0]
        except Exception:
            pass

    conn.close()

    return {
        "status": "HEALTHY" if (integrity_ok and not fk_violations) else "VIOLATIONS_DETECTED",
        "integrity_check": [r[0] for r in integrity_rows],
        "is_integrity_ok": integrity_ok,
        "foreign_key_violations": fk_violations,
        "foreign_key_violations_count": len(fk_violations),
        "table_counts": table_counts,
    }
