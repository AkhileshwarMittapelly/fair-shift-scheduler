"""
Constraint-Based Fair Shift Scheduling and Optimization Engine.
Solves coverage requirements subject to skills, leaves, labor laws, and fairness metrics.
"""

from __future__ import annotations
import datetime
import math
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass, asdict

from .models import (
    EmploymentStatus,
    SkillCategory,
    ProficiencyLevel,
    ShiftCode,
    LeaveType,
    LeaveStatus,
    AssignmentStatus,
    Skill,
    Team,
    Employee,
    EmployeeSkill,
    ShiftTemplate,
    CoverageRequirement,
    LeaveRequest,
    ShiftAssignment,
)


@dataclass
class SchedulingMetrics:
    total_requirements: int
    fulfilled_requirements: int
    unfulfilled_requirements: int
    coverage_fulfillment_rate_pct: float
    total_scheduled_shifts: int
    total_scheduled_hours: float
    total_overtime_hours: float
    fairness_gini_coefficient: float
    fairness_std_dev_hours: float
    night_shift_equity_score: float  # 0 to 100
    weekend_shift_equity_score: float  # 0 to 100
    hard_constraint_violations: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchedulingDecisionLog:
    decision_id: str
    requirement_id: str
    date: str
    shift_code: str
    assigned_employee_id: Optional[str]
    candidates_evaluated: int
    rationale: str
    selected_rank_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchedulingResult:
    is_feasible: bool
    assignments: List[ShiftAssignment]
    coverage_gaps: List[CoverageRequirement]
    metrics: SchedulingMetrics
    decision_logs: List[SchedulingDecisionLog]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_feasible": self.is_feasible,
            "assignments": [a.to_dict() for a in self.assignments],
            "coverage_gaps": [g.to_dict() for g in self.coverage_gaps],
            "metrics": self.metrics.to_dict(),
            "decision_logs": [d.to_dict() for d in self.decision_logs],
        }


class FairShiftScheduler:
    """
    Intelligent heuristic and constraint optimization solver that produces
    fair, legal, and feasible schedules.
    """

    def __init__(
        self,
        employees: List[Employee],
        teams: List[Team],
        skills: List[Skill],
        employee_skills: List[EmployeeSkill],
        shift_templates: List[ShiftTemplate],
        leave_requests: List[LeaveRequest],
        min_rest_hours: float = 11.0,
        max_consecutive_days: int = 6,
    ):
        self.employees = employees
        self.teams = teams
        self.skills = skills
        self.employee_skills = employee_skills
        self.shift_templates = shift_templates
        self.leave_requests = leave_requests
        self.min_rest_hours = min_rest_hours
        self.max_consecutive_days = max_consecutive_days

        # Precompute lookups
        self.emp_map = {e.employee_id: e for e in self.employees}
        self.team_map = {t.team_id: t for t in self.teams}
        self.tmpl_map = {st.shift_template_id: st for st in self.shift_templates}
        self.skill_map = {s.skill_id: s for s in self.skills}

        # Skills held by employee: emp_id -> set of skill_ids
        self.emp_skill_map: Dict[str, Set[str]] = {e.employee_id: set() for e in self.employees}
        for es in self.employee_skills:
            self.emp_skill_map[es.employee_id].add(es.skill_id)

        # Approved leave days: emp_id -> set of date strings
        self.emp_leave_map: Dict[str, Set[str]] = {e.employee_id: set() for e in self.employees}
        for lr in self.leave_requests:
            if lr.status == LeaveStatus.APPROVED:
                cur = datetime.date.fromisoformat(lr.start_date)
                end = datetime.date.fromisoformat(lr.end_date)
                while cur <= end:
                    self.emp_leave_map[lr.employee_id].add(cur.isoformat())
                    cur += datetime.timedelta(days=1)

    def solve(
        self,
        coverage_requirements: List[CoverageRequirement],
        start_date: datetime.date | str,
        num_days: int,
    ) -> SchedulingResult:
        """
        Runs the optimization solver across the designated scheduling window.
        """
        if isinstance(start_date, str):
            start_date = datetime.date.fromisoformat(start_date)
        assignments: List[ShiftAssignment] = []
        coverage_gaps: List[CoverageRequirement] = []
        decision_logs: List[SchedulingDecisionLog] = []

        # State tracking structures
        emp_assignments_by_date: Dict[Tuple[str, str], ShiftAssignment] = {}  # (emp_id, date) -> ShiftAssignment
        emp_weekly_hours: Dict[Tuple[str, int], float] = {}  # (emp_id, week_num) -> total hours
        emp_night_shifts: Dict[str, int] = {e.employee_id: 0 for e in self.employees}
        emp_weekend_shifts: Dict[str, int] = {e.employee_id: 0 for e in self.employees}
        emp_consecutive_days: Dict[str, int] = {e.employee_id: 0 for e in self.employees}
        emp_last_shift_end: Dict[str, datetime.datetime] = {}

        # Group requirements by date
        reqs_by_date: Dict[str, List[CoverageRequirement]] = {}
        for req in coverage_requirements:
            if req.date not in reqs_by_date:
                reqs_by_date[req.date] = []
            reqs_by_date[req.date].append(req)

        # Team employee mapping
        team_emps: Dict[str, List[Employee]] = {t.team_id: [] for t in self.teams}
        for emp in self.employees:
            if emp.employment_status == EmploymentStatus.ACTIVE:
                team_emps[emp.team_id].append(emp)

        assignment_seq = 1
        decision_seq = 1

        # Iterate through calendar chronologically
        for day_offset in range(num_days):
            current_date = start_date + datetime.timedelta(days=day_offset)
            date_str = current_date.isoformat()
            week_num = current_date.isocalendar()[1]
            is_weekend = current_date.weekday() >= 5

            day_reqs = reqs_by_date.get(date_str, [])
            # Prioritize: Critical/Skill requirements first, then general headcount
            sorted_reqs = sorted(day_reqs, key=lambda r: (r.priority_weight, 1 if r.skill_id else 0), reverse=True)

            # Reset consecutive days if employee wasn't scheduled yesterday
            yesterday_str = (current_date - datetime.timedelta(days=1)).isoformat()
            for emp in self.employees:
                if (emp.employee_id, yesterday_str) not in emp_assignments_by_date:
                    emp_consecutive_days[emp.employee_id] = 0

            for req in sorted_reqs:
                tmpl = self.tmpl_map.get(req.shift_template_id)
                if not tmpl:
                    continue

                needed = req.min_headcount
                assigned_for_req = 0

                # Candidates within the target team
                candidates = team_emps.get(req.team_id, [])

                # Score each candidate against hard & soft constraints
                evaluated_candidates = []
                for emp in candidates:
                    # HARD CONSTRAINT 1: No double booking on the same date
                    if (emp.employee_id, date_str) in emp_assignments_by_date:
                        continue

                    # HARD CONSTRAINT 2: No assignment during approved leave
                    if date_str in self.emp_leave_map[emp.employee_id]:
                        continue

                    # HARD CONSTRAINT 3: Mandatory skill matching
                    if req.skill_id and req.skill_id not in self.emp_skill_map[emp.employee_id]:
                        continue

                    # HARD CONSTRAINT 4: Maximum consecutive days
                    if emp_consecutive_days[emp.employee_id] >= self.max_consecutive_days:
                        continue

                    # Shift start & end times
                    shift_start_dt = datetime.datetime.fromisoformat(f"{date_str}T{tmpl.start_time}:00")
                    if tmpl.is_overnight:
                        shift_end_dt = datetime.datetime.fromisoformat(
                            f"{(current_date + datetime.timedelta(days=1)).isoformat()}T{tmpl.end_time}:00"
                        )
                    else:
                        shift_end_dt = datetime.datetime.fromisoformat(f"{date_str}T{tmpl.end_time}:00")

                    # HARD CONSTRAINT 5: Minimum rest period between shifts
                    last_end = emp_last_shift_end.get(emp.employee_id)
                    if last_end:
                        rest_hours = (shift_start_dt - last_end).total_seconds() / 3600.0
                        if rest_hours < self.min_rest_hours:
                            continue

                    # HARD CONSTRAINT 6: Weekly labor and overtime cap
                    current_weekly_hrs = emp_weekly_hours.get((emp.employee_id, week_num), 0.0)
                    max_allowed_hrs = emp.contract_hours_per_week + emp.max_weekly_overtime_hours
                    if current_weekly_hrs + tmpl.duration_hours > max_allowed_hrs:
                        continue

                    # SOFT CONSTRAINT / FAIRNESS SCORING
                    # Lower score = higher preference to assign
                    # 1. Total weekly hours load (favor employees below contract hours)
                    hours_score = current_weekly_hrs / (emp.contract_hours_per_week or 40.0)

                    # 2. Night shift balance
                    night_penalty = emp_night_shifts[emp.employee_id] * 2.0 if tmpl.shift_code == ShiftCode.C else 0.0

                    # 3. Weekend shift balance
                    weekend_penalty = emp_weekend_shifts[emp.employee_id] * 1.5 if is_weekend else 0.0

                    # 4. Consecutive days fatigue penalty
                    fatigue_penalty = emp_consecutive_days[emp.employee_id] * 0.8

                    composite_rank_score = hours_score + night_penalty + weekend_penalty + fatigue_penalty

                    evaluated_candidates.append((composite_rank_score, emp, shift_start_dt, shift_end_dt))

                # Sort by fairness composite rank score ascending
                evaluated_candidates.sort(key=lambda x: x[0])

                for score, emp, s_start, s_end in evaluated_candidates:
                    if assigned_for_req >= needed:
                        break

                    # Create assignment
                    asgn_id = f"SHIFT-{date_str}-{tmpl.shift_code}-{assignment_seq:06d}"
                    assignment_seq += 1

                    asgn = ShiftAssignment(
                        assignment_id=asgn_id,
                        date=date_str,
                        shift_template_id=tmpl.shift_template_id,
                        employee_id=emp.employee_id,
                        team_id=req.team_id,
                        role_skill_id=req.skill_id,
                        scheduled_start=s_start.isoformat() + "Z",
                        scheduled_end=s_end.isoformat() + "Z",
                        status=AssignmentStatus.SCHEDULED,
                        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        created_by="FAIR_SOLVER_ENGINE",
                    )
                    assignments.append(asgn)

                    # Update solver state
                    emp_assignments_by_date[(emp.employee_id, date_str)] = asgn
                    emp_weekly_hours[(emp.employee_id, week_num)] = (
                        emp_weekly_hours.get((emp.employee_id, week_num), 0.0) + tmpl.duration_hours
                    )
                    emp_last_shift_end[emp.employee_id] = s_end
                    emp_consecutive_days[emp.employee_id] += 1
                    if tmpl.shift_code == ShiftCode.C:
                        emp_night_shifts[emp.employee_id] += 1
                    if is_weekend:
                        emp_weekend_shifts[emp.employee_id] += 1

                    assigned_for_req += 1

                    decision_logs.append(
                        SchedulingDecisionLog(
                            decision_id=f"DEC-{decision_seq:06d}",
                            requirement_id=req.requirement_id,
                            date=date_str,
                            shift_code=tmpl.shift_code.value,
                            assigned_employee_id=emp.employee_id,
                            candidates_evaluated=len(evaluated_candidates),
                            rationale=f"Selected candidate with best equity score {score:.2f} (Weekly Load: {emp_weekly_hours[(emp.employee_id, week_num)]:.1f}h)",
                            selected_rank_score=round(score, 4),
                        )
                    )
                    decision_seq += 1

                # If requirements could not be fulfilled, record coverage gap
                if assigned_for_req < needed:
                    unfulfilled_count = needed - assigned_for_req
                    for _ in range(unfulfilled_count):
                        coverage_gaps.append(req)
                    decision_logs.append(
                        SchedulingDecisionLog(
                            decision_id=f"DEC-{decision_seq:06d}",
                            requirement_id=req.requirement_id,
                            date=date_str,
                            shift_code=tmpl.shift_code.value,
                            assigned_employee_id=None,
                            candidates_evaluated=len(evaluated_candidates),
                            rationale=f"COVERAGE GAP: Only {assigned_for_req}/{needed} staffing met. Constraints precluded further assignments.",
                            selected_rank_score=999.0,
                        )
                    )
                    decision_seq += 1

        # Compute fairness and coverage metrics
        metrics = self._calculate_metrics(
            coverage_requirements, assignments, coverage_gaps, emp_weekly_hours, emp_night_shifts, emp_weekend_shifts
        )

        return SchedulingResult(
            is_feasible=(len(coverage_gaps) == 0),
            assignments=assignments,
            coverage_gaps=coverage_gaps,
            metrics=metrics,
            decision_logs=decision_logs,
        )

    def _calculate_metrics(
        self,
        coverage_requirements: List[CoverageRequirement],
        assignments: List[ShiftAssignment],
        coverage_gaps: List[CoverageRequirement],
        emp_weekly_hours: Dict[Tuple[str, int], float],
        emp_night_shifts: Dict[str, int],
        emp_weekend_shifts: Dict[str, int],
    ) -> SchedulingMetrics:
        total_reqs = sum(r.min_headcount for r in coverage_requirements)
        unfulfilled = len(coverage_gaps)
        fulfilled = max(0, total_reqs - unfulfilled)
        fulfillment_pct = round((fulfilled / total_reqs * 100.0) if total_reqs > 0 else 100.0, 2)

        total_hours = sum(self.tmpl_map[a.shift_template_id].duration_hours for a in assignments if a.shift_template_id in self.tmpl_map)

        # Overtime calculation
        total_ot = 0.0
        for (emp_id, _), week_hrs in emp_weekly_hours.items():
            emp = self.emp_map.get(emp_id)
            contract = emp.contract_hours_per_week if emp else 40.0
            if week_hrs > contract:
                total_ot += (week_hrs - contract)

        # Calculate Gini coefficient of hours worked across active employees
        emp_total_hours: Dict[str, float] = {e.employee_id: 0.0 for e in self.employees}
        for (emp_id, _), hrs in emp_weekly_hours.items():
            emp_total_hours[emp_id] += hrs

        hours_values = list(emp_total_hours.values())
        gini = self._compute_gini(hours_values)
        std_dev = self._compute_std_dev(hours_values)

        # Equity scores (100 - coefficient of variation)
        night_vals = list(emp_night_shifts.values())
        night_equity = max(0.0, min(100.0, 100.0 - self._compute_cv(night_vals) * 50.0))

        weekend_vals = list(emp_weekend_shifts.values())
        weekend_equity = max(0.0, min(100.0, 100.0 - self._compute_cv(weekend_vals) * 50.0))

        return SchedulingMetrics(
            total_requirements=total_reqs,
            fulfilled_requirements=fulfilled,
            unfulfilled_requirements=unfulfilled,
            coverage_fulfillment_rate_pct=fulfillment_pct,
            total_scheduled_shifts=len(assignments),
            total_scheduled_hours=round(total_hours, 1),
            total_overtime_hours=round(total_ot, 1),
            fairness_gini_coefficient=round(gini, 4),
            fairness_std_dev_hours=round(std_dev, 2),
            night_shift_equity_score=round(night_equity, 1),
            weekend_shift_equity_score=round(weekend_equity, 1),
            hard_constraint_violations=0,  # Strict solver guarantees 0 violations
        )

    @staticmethod
    def _compute_gini(values: List[float]) -> float:
        if not values or all(v == 0 for v in values):
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mean_val = sum(sorted_vals) / n
        if mean_val == 0:
            return 0.0
        diff_sum = sum(abs(x - y) for x in sorted_vals for y in sorted_vals)
        return diff_sum / (2.0 * n * n * mean_val)

    @staticmethod
    def _compute_std_dev(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)

    @staticmethod
    def _compute_cv(values: List[int]) -> float:
        if len(values) < 2 or sum(values) == 0:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance) / mean
