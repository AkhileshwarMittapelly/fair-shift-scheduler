"""
FastAPI REST API Server for Fair Shift Scheduler.
Connects the backend solver, validator, generator, and operational databases
to the frontend interactive application.

Runtime persistence note:
  All in-memory state (CURRENT_DATASET) lives for the lifetime of the server
  process. Changes made via the API (leave decisions, swap decisions, attendance
  punches) persist in memory across requests but are NOT written to disk unless
  the /api/generator/run endpoint is called, which re-exports to data/<scale>/.
  Restarting the server resets all in-memory state.
"""

from __future__ import annotations
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    AnomalyType,
)
from data_generator.generator import SyntheticDataGenerator, GeneratedDataset
from data_generator.validator import DatasetValidator
from data_generator.scheduler import FairShiftScheduler
from data_generator.reproducibility import verify_reproducibility
from data_generator.export import DatasetExporter

app = FastAPI(
    title="Fair Shift Scheduler API",
    description="End-to-End Workforce Scheduling, Labor Constraint Solving & Compliance System",
    version="1.0.0",
)

# Allowed CORS origins. Never use wildcard with allow_credentials=True as
# that violates the CORS spec and is rejected by browsers.
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# In-memory cached dataset state for snappy UI interactions
CURRENT_DATASET: Optional[GeneratedDataset] = None


def get_or_load_dataset(scale: str = "starter", seed: int = 20261022) -> GeneratedDataset:
    global CURRENT_DATASET
    if CURRENT_DATASET is None:
        gen = SyntheticDataGenerator(seed=seed, scale=scale)
        CURRENT_DATASET = gen.generate()
    return CURRENT_DATASET


# -----------------------------------------------------------------------------
# Pydantic Schemas for API Requests
# -----------------------------------------------------------------------------
class LeaveCreateRequest(BaseModel):
    employee_id: str
    start_date: str
    end_date: str
    leave_type: str
    reason: str


class LeaveDecisionRequest(BaseModel):
    decision: str  # "APPROVED" or "REJECTED"
    decision_by: str
    decision_notes: Optional[str] = None


class SwapCreateRequest(BaseModel):
    requester_assignment_id: str
    target_assignment_id: str


class SwapDecisionRequest(BaseModel):
    decision: str  # "APPROVED", "REJECTED", "APPLIED"
    decision_by: str
    decision_notes: Optional[str] = None


class AttendancePunchRequest(BaseModel):
    employee_id: str
    assignment_id: Optional[str] = None
    event_type: str  # "CLOCK_IN" or "CLOCK_OUT"
    device_id: str = "WEB-TERMINAL-01"


class GenerateParamsRequest(BaseModel):
    scale: str = "starter"
    seed: int = 20261022


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/health")
def health_check():
    return {"status": "HEALTHY", "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}


@app.get("/api/metrics")
def get_metrics():
    dataset = get_or_load_dataset()
    validator = DatasetValidator(dataset)
    report = validator.validate()

    total_shifts = len(dataset.shift_assignments)
    total_employees = len(dataset.employees)
    total_teams = len(dataset.teams)
    total_leaves = len(dataset.leave_requests)
    approved_leaves = sum(1 for l in dataset.leave_requests if l.status == LeaveStatus.APPROVED)

    # Compute rough fairness & hours
    tmpl_map = {t.shift_template_id: t.duration_hours for t in dataset.shift_templates}
    total_hours = sum(tmpl_map.get(a.shift_template_id, 8.0) for a in dataset.shift_assignments)

    # Overtime hours — computed correctly per (employee_id, iso_week) not aggregate
    emp_week_hours: Dict[tuple, float] = {}
    for a in dataset.shift_assignments:
        try:
            shift_date = datetime.date.fromisoformat(a.date)
            week_num = shift_date.isocalendar()[1]
        except (ValueError, AttributeError):
            continue
        key = (a.employee_id, week_num)
        emp_week_hours[key] = emp_week_hours.get(key, 0.0) + tmpl_map.get(a.shift_template_id, 8.0)

    emp_map = {e.employee_id: e for e in dataset.employees}
    total_overtime = 0.0
    for (emp_id, _week), week_hrs in emp_week_hours.items():
        emp = emp_map.get(emp_id)
        contract_hrs = emp.contract_hours_per_week if emp else 40.0
        total_overtime += max(0.0, week_hrs - contract_hrs)

    return {
        "scale": dataset.scale,
        "seed": dataset.seed,
        "total_employees": total_employees,
        "total_teams": total_teams,
        "total_shifts": total_shifts,
        "total_scheduled_hours": total_hours,
        "total_overtime_hours": round(total_overtime, 1),
        "total_leaves": total_leaves,
        "approved_leaves": approved_leaves,
        "total_ground_truth_anomalies": len(dataset.ground_truth_anomalies),
        "detected_anomalies": len(report.detected_rule_violations),
        "detection_precision": report.ground_truth_evaluation["precision"],
        "detection_recall": report.ground_truth_evaluation["recall"],
        "detection_f1_score": report.ground_truth_evaluation["f1_score"],
    }


@app.get("/api/teams")
def list_teams():
    dataset = get_or_load_dataset()
    return [t.to_dict() for t in dataset.teams]


@app.get("/api/skills")
def list_skills():
    dataset = get_or_load_dataset()
    return [s.to_dict() for s in dataset.skills]


@app.get("/api/employees")
def list_employees(
    team_id: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    search: Optional[str] = None,
):
    dataset = get_or_load_dataset()
    emps = dataset.employees

    if team_id:
        emps = [e for e in emps if e.team_id == team_id]

    if search:
        s_lower = search.lower()
        emps = [e for e in emps if s_lower in e.first_name.lower() or s_lower in e.last_name.lower() or s_lower in e.employee_id.lower()]

    emp_skills_map: Dict[str, List[str]] = {}
    for es in dataset.employee_skills:
        if es.employee_id not in emp_skills_map:
            emp_skills_map[es.employee_id] = []
        emp_skills_map[es.employee_id].append(es.skill_id)

    results = []
    for e in emps[:limit]:
        d = e.to_dict()
        d["skills"] = emp_skills_map.get(e.employee_id, [])
        results.append(d)

    return results


@app.get("/api/coverage")
def list_coverage(
    date: Optional[str] = None,
    team_id: Optional[str] = None,
    limit: int = Query(default=150, le=500),
):
    dataset = get_or_load_dataset()
    reqs = dataset.coverage_requirements

    if date:
        reqs = [r for r in reqs if r.date == date]
    if team_id:
        reqs = [r for r in reqs if r.team_id == team_id]

    return [r.to_dict() for r in reqs[:limit]]


@app.get("/api/shifts")
def list_shifts(
    date: Optional[str] = None,
    team_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    limit: int = Query(default=200, le=1000),
):
    dataset = get_or_load_dataset()
    shifts = dataset.shift_assignments

    if date:
        shifts = [s for s in shifts if s.date == date]
    if team_id:
        shifts = [s for s in shifts if s.team_id == team_id]
    if employee_id:
        shifts = [s for s in shifts if s.employee_id == employee_id]

    return [s.to_dict() for s in shifts[:limit]]


@app.get("/api/leaves")
def list_leaves(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, le=500),
):
    dataset = get_or_load_dataset()
    leaves = dataset.leave_requests

    if employee_id:
        leaves = [l for l in leaves if l.employee_id == employee_id]
    if status:
        leaves = [l for l in leaves if l.status == status]

    return [l.to_dict() for l in leaves[:limit]]


@app.post("/api/leaves/create")
def create_leave(payload: LeaveCreateRequest):
    dataset = get_or_load_dataset()

    # Input validation
    emp_ids = {e.employee_id for e in dataset.employees}
    if payload.employee_id not in emp_ids:
        raise HTTPException(status_code=400, detail=f"Employee {payload.employee_id!r} not found")
    try:
        start_d = datetime.date.fromisoformat(payload.start_date)
        end_d = datetime.date.fromisoformat(payload.end_date)
        if end_d < start_d:
            raise ValueError("end_date must be >= start_date")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date: {e}")
    try:
        LeaveType(payload.leave_type)
    except ValueError:
        valid = [lt.value for lt in LeaveType]
        raise HTTPException(status_code=400, detail=f"Invalid leave_type. Must be one of: {valid}")

    counter = len(dataset.leave_requests) + 1
    leave_id = f"LVE-2026-{counter:06d}"

    leave = LeaveRequest(
        leave_id=leave_id,
        employee_id=payload.employee_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        leave_type=LeaveType(payload.leave_type),
        status=LeaveStatus.PENDING,
        reason=payload.reason,
        decision_by=None,
        decision_timestamp=None,
        decision_notes=None,
    )
    dataset.leave_requests.insert(0, leave)
    return leave.to_dict()


@app.post("/api/leaves/{leave_id}/decide")
def decide_leave(leave_id: str, payload: LeaveDecisionRequest):
    dataset = get_or_load_dataset()
    for l in dataset.leave_requests:
        if l.leave_id == leave_id:
            l.status = LeaveStatus(payload.decision)
            l.decision_by = payload.decision_by
            l.decision_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            l.decision_notes = payload.decision_notes or f"Leave marked {payload.decision} by {payload.decision_by}"
            return l.to_dict()
    raise HTTPException(status_code=404, detail="Leave request not found")


@app.get("/api/swaps")
def list_swaps():
    dataset = get_or_load_dataset()
    return [s.to_dict() for s in dataset.swap_requests]


@app.post("/api/swaps/request")
def request_swap(payload: SwapCreateRequest):
    dataset = get_or_load_dataset()
    asgn_map = {a.assignment_id: a for a in dataset.shift_assignments}

    if payload.requester_assignment_id not in asgn_map or payload.target_assignment_id not in asgn_map:
        raise HTTPException(status_code=400, detail="Invalid assignment IDs")

    asgn1 = asgn_map[payload.requester_assignment_id]
    asgn2 = asgn_map[payload.target_assignment_id]

    counter = len(dataset.swap_requests) + 1
    swap_id = f"SWP-2026-{counter:06d}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    swap = SwapRequest(
        swap_id=swap_id,
        requester_assignment_id=asgn1.assignment_id,
        target_assignment_id=asgn2.assignment_id,
        requester_employee_id=asgn1.employee_id,
        target_employee_id=asgn2.employee_id,
        status=SwapStatus.PENDING_MANAGER,
        requested_at=now_str,
        peer_agreed_at=now_str,
        manager_decision_by=None,
        manager_decision_at=None,
        decision_notes=None,
    )
    dataset.swap_requests.insert(0, swap)
    return swap.to_dict()


@app.post("/api/swaps/{swap_id}/decide")
def decide_swap(swap_id: str, payload: SwapDecisionRequest):
    dataset = get_or_load_dataset()
    asgn_map = {a.assignment_id: a for a in dataset.shift_assignments}

    # Input validation
    try:
        decision_status = SwapStatus(payload.decision)
    except ValueError:
        valid = [s.value for s in SwapStatus]
        raise HTTPException(status_code=400, detail=f"Invalid decision. Must be one of: {valid}")

    for s in dataset.swap_requests:
        if s.swap_id == swap_id:
            # Feasibility check before applying a swap
            if decision_status == SwapStatus.APPLIED:
                if s.requester_assignment_id not in asgn_map or s.target_assignment_id not in asgn_map:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot apply swap: one or both referenced assignments not found",
                    )
                asgn1 = asgn_map[s.requester_assignment_id]
                asgn2 = asgn_map[s.target_assignment_id]
                if asgn1.employee_id == asgn2.employee_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot apply swap: requester and target are the same employee",
                    )
                # Check requester is not on approved leave on target shift date
                approved_leaves = {
                    (l.employee_id, d)
                    for l in dataset.leave_requests
                    if l.status == LeaveStatus.APPROVED
                    for d in (
                        (datetime.date.fromisoformat(l.start_date)
                         + datetime.timedelta(days=i)).isoformat()
                        for i in range(
                            (datetime.date.fromisoformat(l.end_date)
                             - datetime.date.fromisoformat(l.start_date)).days + 1
                        )
                    )
                }
                if (asgn1.employee_id, asgn2.date) in approved_leaves:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot apply swap: {asgn1.employee_id} has approved leave on {asgn2.date}",
                    )
                if (asgn2.employee_id, asgn1.date) in approved_leaves:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot apply swap: {asgn2.employee_id} has approved leave on {asgn1.date}",
                    )

            s.status = decision_status
            s.manager_decision_by = payload.decision_by
            s.manager_decision_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            s.decision_notes = payload.decision_notes or f"Swap {payload.decision} by manager {payload.decision_by}"

            if decision_status == SwapStatus.APPLIED:
                # Execute the shift exchange
                asgn1 = asgn_map[s.requester_assignment_id]
                asgn2 = asgn_map[s.target_assignment_id]
                # Swap assigned employees
                asgn1.employee_id, asgn2.employee_id = asgn2.employee_id, asgn1.employee_id
                asgn1.status = AssignmentStatus.SWAPPED
                asgn2.status = AssignmentStatus.SWAPPED

            return s.to_dict()

    raise HTTPException(status_code=404, detail="Swap request not found")


@app.get("/api/attendance")
def list_attendance(limit: int = Query(default=150, le=500)):
    dataset = get_or_load_dataset()
    return [ae.to_dict() for ae in dataset.attendance_events[:limit]]


@app.post("/api/attendance/punch")
def punch_attendance(payload: AttendancePunchRequest):
    dataset = get_or_load_dataset()
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    ts_str = now_dt.strftime("%Y%m%dT%H%M%S")
    att_id = f"ATT-{payload.employee_id}-{ts_str}"

    event = AttendanceEvent(
        attendance_id=att_id,
        employee_id=payload.employee_id,
        assignment_id=payload.assignment_id,
        event_type=AttendanceEventType(payload.event_type),
        event_timestamp=now_dt.isoformat(),
        source_device=payload.device_id,
        matched_schedule_diff_minutes=0.0,
    )
    dataset.attendance_events.insert(0, event)
    return event.to_dict()


@app.post("/api/scheduler/run")
def run_scheduler_engine():
    dataset = get_or_load_dataset()
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
        start_date=dataset.metadata.get("start_date", "2026-01-01"),
        num_days=dataset.metadata.get("num_days", 14),
    )

    return {
        "is_feasible": result.is_feasible,
        "metrics": result.metrics.to_dict(),
        "total_scheduled_shifts": len(result.assignments),
        "total_gaps": len(result.coverage_gaps),
        "sample_decisions": [d.to_dict() for d in result.decision_logs[:20]],
    }


@app.get("/api/validation/report")
def run_live_validation():
    dataset = get_or_load_dataset()
    validator = DatasetValidator(dataset)
    report = validator.validate()
    return report.to_dict()


@app.post("/api/generator/run")
def run_generator(payload: GenerateParamsRequest):
    global CURRENT_DATASET
    gen = SyntheticDataGenerator(seed=payload.seed, scale=payload.scale)
    CURRENT_DATASET = gen.generate()

    # Automatically export to disk
    out_dir = f"data/{payload.scale}"
    validator = DatasetValidator(CURRENT_DATASET)
    report = validator.validate()
    exporter = DatasetExporter(CURRENT_DATASET, out_dir)
    exported = exporter.export_all(report)

    return {
        "message": f"Successfully generated {payload.scale} dataset with seed {payload.seed}",
        "metadata": CURRENT_DATASET.metadata,
        "validation_summary": report.summary,
    }


@app.get("/api/reproducibility/verify")
def run_reproducibility_check(scale: str = "starter", seed: int = 20261022):
    res = verify_reproducibility(seed=seed, scale=scale)
    return res


# Mount frontend build static directory if present
client_dist = Path(__file__).parent.parent / "client" / "dist"
if client_dist.exists():
    app.mount("/", StaticFiles(directory=str(client_dist), html=True), name="static")
