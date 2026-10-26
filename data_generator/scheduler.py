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
    SwapRequest,
    SwapStatus,
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
        self.emp_skills_detail: Dict[Tuple[str, str], List[EmployeeSkill]] = {}
        for es in self.employee_skills:
            self.emp_skill_map[es.employee_id].add(es.skill_id)
            key = (es.employee_id, es.skill_id)
            if key not in self.emp_skills_detail:
                self.emp_skills_detail[key] = []
            self.emp_skills_detail[key].append(es)

        # Approved leave days: emp_id -> set of date strings
        self.emp_leave_map: Dict[str, Set[str]] = {e.employee_id: set() for e in self.employees}
        for lr in self.leave_requests:
            if lr.status == LeaveStatus.APPROVED:
                cur = datetime.date.fromisoformat(lr.start_date)
                end = datetime.date.fromisoformat(lr.end_date)
                while cur <= end:
                    self.emp_leave_map[lr.employee_id].add(cur.isoformat())
                    cur += datetime.timedelta(days=1)

    def has_valid_skill(self, emp_id: str, skill_id: Optional[str], date_str: str) -> bool:
        """
        Verifies that the employee possesses the required skill with a valid,
        non-expired certification on the specific shift date.
        """
        if not skill_id:
            return True
        records = self.emp_skills_detail.get((emp_id, skill_id), [])
        if not records:
            return False
        for es in records:
            if es.certified_date and es.certified_date > date_str:
                continue
            if es.expiry_date and es.expiry_date < date_str:
                continue
            return True
        return False

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
        emp_assigned_intervals: Dict[str, List[Tuple[datetime.datetime, datetime.datetime]]] = {
            e.employee_id: [] for e in self.employees
        }
        emp_weekly_hours: Dict[Tuple[str, Tuple[int, int]], float] = {}  # (emp_id, (ISO year, ISO week)) -> total hours
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
            iso_calendar = current_date.isocalendar()
            week_key = (iso_calendar.year, iso_calendar.week)
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
                    # Shift start & end times
                    shift_start_dt = datetime.datetime.fromisoformat(f"{date_str}T{tmpl.start_time}:00")
                    if tmpl.is_overnight:
                        shift_end_dt = datetime.datetime.fromisoformat(
                            f"{(current_date + datetime.timedelta(days=1)).isoformat()}T{tmpl.end_time}:00"
                        )
                    else:
                        shift_end_dt = datetime.datetime.fromisoformat(f"{date_str}T{tmpl.end_time}:00")

                    # HARD CONSTRAINT 1: No double booking on same date or overlapping intervals
                    if (emp.employee_id, date_str) in emp_assignments_by_date:
                        continue
                    has_overlap = False
                    for prev_start, prev_end in emp_assigned_intervals[emp.employee_id]:
                        if shift_start_dt < prev_end and prev_start < shift_end_dt:
                            has_overlap = True
                            break
                    if has_overlap:
                        continue

                    # HARD CONSTRAINT 2: No assignment during approved leave (including overnight cross-midnight)
                    if date_str in self.emp_leave_map[emp.employee_id]:
                        continue
                    if tmpl.is_overnight:
                        next_day_str = (current_date + datetime.timedelta(days=1)).isoformat()
                        if next_day_str in self.emp_leave_map[emp.employee_id]:
                            continue

                    # HARD CONSTRAINT 3: Mandatory skill and active non-expired certification matching
                    if req.skill_id and not self.has_valid_skill(emp.employee_id, req.skill_id, date_str):
                        continue

                    # HARD CONSTRAINT 4: Maximum consecutive days
                    if emp_consecutive_days[emp.employee_id] >= self.max_consecutive_days:
                        continue

                    # HARD CONSTRAINT 5: Minimum rest period between shifts
                    violates_rest = False
                    for prev_start, prev_end in emp_assigned_intervals[emp.employee_id]:
                        if shift_start_dt >= prev_end:
                            rest_hours = (shift_start_dt - prev_end).total_seconds() / 3600.0
                            if rest_hours < self.min_rest_hours:
                                violates_rest = True
                                break
                        elif prev_start >= shift_end_dt:
                            rest_hours = (prev_start - shift_end_dt).total_seconds() / 3600.0
                            if rest_hours < self.min_rest_hours:
                                violates_rest = True
                                break
                    if violates_rest:
                        continue

                    # HARD CONSTRAINT 6: Weekly labor and overtime cap
                    current_weekly_hrs = emp_weekly_hours.get((emp.employee_id, week_key), 0.0)
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
                    shift_letter = tmpl.shift_code.value if hasattr(tmpl.shift_code, "value") else str(tmpl.shift_code)
                    asgn_id = f"SHIFT-{date_str}-{shift_letter}-{assignment_seq:06d}"
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
                    emp_assigned_intervals[emp.employee_id].append((s_start, s_end))
                    emp_weekly_hours[(emp.employee_id, week_key)] = (
                        emp_weekly_hours.get((emp.employee_id, week_key), 0.0) + tmpl.duration_hours
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
                            rationale=f"Selected candidate with best equity score {score:.2f} (Weekly Load: {emp_weekly_hours[(emp.employee_id, week_key)]:.1f}h)",
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

        # Compute fairness, coverage metrics, and hard constraint violations
        metrics = self._calculate_metrics(
            coverage_requirements, assignments, coverage_gaps, emp_weekly_hours, emp_night_shifts, emp_weekend_shifts
        )

        return SchedulingResult(
            is_feasible=(len(coverage_gaps) == 0 and metrics.hard_constraint_violations == 0),
            assignments=assignments,
            coverage_gaps=coverage_gaps,
            metrics=metrics,
            decision_logs=decision_logs,
        )

    def _count_hard_constraint_violations(self, assignments: List[ShiftAssignment]) -> int:
        """
        Calculates hard-constraint violations from the actual resulting schedule.
        Checks:
        1. Employee eligibility and non-expired skill certification on shift date.
        2. Shifts scheduled during approved leave (including overnight shifts).
        3. Overlapping shift intervals for the same employee.
        4. Minimum rest period between consecutive shifts (< min_rest_hours).
        5. Weekly contractual hours plus maximum weekly overtime cap.
        6. Maximum consecutive working days (> max_consecutive_days).
        """
        violations = 0
        emp_assignments: Dict[str, List[ShiftAssignment]] = {e.employee_id: [] for e in self.employees}

        for asgn in assignments:
            if asgn.employee_id in emp_assignments:
                emp_assignments[asgn.employee_id].append(asgn)

            # Check 1: Skill eligibility and certification validity on shift date
            if asgn.role_skill_id:
                if not self.has_valid_skill(asgn.employee_id, asgn.role_skill_id, asgn.date):
                    violations += 1

            # Check 2: Shift scheduled during approved leave (including cross-midnight)
            s_start = parse_dt(asgn.scheduled_start)
            s_end = parse_dt(asgn.scheduled_end)
            on_leave = False
            for lr in self.leave_requests:
                if lr.employee_id == asgn.employee_id and lr.status == LeaveStatus.APPROVED:
                    l_start = datetime.datetime.combine(datetime.date.fromisoformat(lr.start_date), datetime.time.min)
                    l_end = datetime.datetime.combine(datetime.date.fromisoformat(lr.end_date) + datetime.timedelta(days=1), datetime.time.min)
                    if s_start < l_end and l_start < s_end:
                        on_leave = True
                        break
            if on_leave:
                violations += 1

        for emp_id, emp_asgns in emp_assignments.items():
            if not emp_asgns:
                continue
            emp = self.emp_map.get(emp_id)
            if not emp:
                continue

            # Sort assignments chronologically
            sorted_asgns = sorted(emp_asgns, key=lambda a: parse_dt(a.scheduled_start))

            # Check 3 & 4: Overlaps and minimum rest periods between consecutive shifts
            for i in range(len(sorted_asgns) - 1):
                cur_end = parse_dt(sorted_asgns[i].scheduled_end)
                next_start = parse_dt(sorted_asgns[i + 1].scheduled_start)

                if next_start < cur_end:
                    # Overlapping shift
                    violations += 1
                else:
                    rest_hrs = (next_start - cur_end).total_seconds() / 3600.0
                    if rest_hrs < self.min_rest_hours:
                        violations += 1

            # Check 5: Weekly contractual working hours and overtime cap
            weekly_hours: Dict[Tuple[int, int], float] = {}
            for asgn in emp_asgns:
                tmpl = self.tmpl_map.get(asgn.shift_template_id)
                dur = tmpl.duration_hours if tmpl else (parse_dt(asgn.scheduled_end) - parse_dt(asgn.scheduled_start)).total_seconds() / 3600.0
                dt = datetime.date.fromisoformat(asgn.date)
                iso_cal = dt.isocalendar()
                w_key = (iso_cal.year, iso_cal.week)
                weekly_hours[w_key] = weekly_hours.get(w_key, 0.0) + dur

            max_allowed = emp.contract_hours_per_week + emp.max_weekly_overtime_hours
            for w_key, tot_hrs in weekly_hours.items():
                if tot_hrs > max_allowed:
                    violations += 1

            # Check 6: Maximum consecutive working days
            work_dates = sorted({datetime.date.fromisoformat(a.date) for a in emp_asgns})
            consecutive = 1
            for i in range(len(work_dates) - 1):
                if work_dates[i + 1] == work_dates[i] + datetime.timedelta(days=1):
                    consecutive += 1
                    if consecutive > self.max_consecutive_days:
                        violations += 1
                else:
                    consecutive = 1

        return violations

    def _calculate_metrics(
        self,
        coverage_requirements: List[CoverageRequirement],
        assignments: List[ShiftAssignment],
        coverage_gaps: List[CoverageRequirement],
        emp_weekly_hours: Dict[Tuple[str, Tuple[int, int]], float],
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

        violations = self._count_hard_constraint_violations(assignments)

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
            hard_constraint_violations=violations,
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


def parse_dt(dt_val: str | datetime.datetime) -> datetime.datetime:
    """Parses a datetime string or datetime object into a naive UTC datetime."""
    if isinstance(dt_val, datetime.datetime):
        dt = dt_val
    else:
        clean = dt_val.replace("Z", "+00:00") if dt_val.endswith("Z") else dt_val
        dt = datetime.datetime.fromisoformat(clean)
    if dt.tzinfo is not None:
        dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt


def validate_shift_swap(
    swap: SwapRequest,
    assignments: List[ShiftAssignment],
    employees: List[Employee],
    skills: List[EmployeeSkill],
    leaves: List[LeaveRequest],
    shift_templates: List[ShiftTemplate],
    min_rest_hours: float = 11.0,
) -> Tuple[bool, Optional[str]]:
    """
    Validates employee eligibility, approved leave, overlapping shifts,
    minimum rest periods, and weekly working-hour limits before applying a swap.
    Returns (True, None) if valid, or (False, error_message) if invalid.
    """
    asgn_map = {a.assignment_id: a for a in assignments}
    if swap.requester_assignment_id not in asgn_map or swap.target_assignment_id not in asgn_map:
        return False, "Cannot apply swap: one or both referenced assignments not found"

    asgn1 = asgn_map[swap.requester_assignment_id]
    asgn2 = asgn_map[swap.target_assignment_id]

    emp1_id = asgn1.employee_id
    emp2_id = asgn2.employee_id

    if emp1_id == emp2_id:
        return False, "Cannot apply swap: requester and target are the same employee"

    emp_map = {e.employee_id: e for e in employees}
    emp1 = emp_map.get(emp1_id)
    emp2 = emp_map.get(emp2_id)
    if not emp1 or not emp2:
        return False, "Cannot apply swap: employee record not found"

    tmpl_map = {st.shift_template_id: st for st in shift_templates}
    tmpl1 = tmpl_map.get(asgn1.shift_template_id)
    tmpl2 = tmpl_map.get(asgn2.shift_template_id)
    if not tmpl1 or not tmpl2:
        return False, "Cannot apply swap: shift template not found"

    # Helper for skill validation
    emp_skills_detail: Dict[Tuple[str, str], List[EmployeeSkill]] = {}
    for es in skills:
        key = (es.employee_id, es.skill_id)
        if key not in emp_skills_detail:
            emp_skills_detail[key] = []
        emp_skills_detail[key].append(es)

    def has_skill_cert(e_id: str, sk_id: Optional[str], d_str: str) -> bool:
        if not sk_id:
            return True
        records = emp_skills_detail.get((e_id, sk_id), [])
        if not records:
            return False
        for es in records:
            if es.certified_date and es.certified_date > d_str:
                continue
            if es.expiry_date and es.expiry_date < d_str:
                continue
            return True
        return False

    # 1. Eligibility: Check required skills and non-expired certifications
    if asgn2.role_skill_id and not has_skill_cert(emp1_id, asgn2.role_skill_id, asgn2.date):
        return False, f"Employee {emp1_id} lacks valid or unexpired certification for required skill {asgn2.role_skill_id} on {asgn2.date}"
    if asgn1.role_skill_id and not has_skill_cert(emp2_id, asgn1.role_skill_id, asgn1.date):
        return False, f"Employee {emp2_id} lacks valid or unexpired certification for required skill {asgn1.role_skill_id} on {asgn1.date}"

    # 2. Approved leave conflicts (including cross-midnight shifts)
    def check_leave_conflict(e_id: str, s_start_dt: datetime.datetime, s_end_dt: datetime.datetime, d_str: str) -> Optional[str]:
        for lr in leaves:
            if lr.employee_id == e_id and lr.status == LeaveStatus.APPROVED:
                l_start = datetime.datetime.combine(datetime.date.fromisoformat(lr.start_date), datetime.time.min)
                l_end = datetime.datetime.combine(datetime.date.fromisoformat(lr.end_date) + datetime.timedelta(days=1), datetime.time.min)
                if s_start_dt < l_end and l_start < s_end_dt:
                    return f"Employee {e_id} has approved leave during proposed shift on {d_str}"
        return None

    s1_start = parse_dt(asgn1.scheduled_start)
    s1_end = parse_dt(asgn1.scheduled_end)
    s2_start = parse_dt(asgn2.scheduled_start)
    s2_end = parse_dt(asgn2.scheduled_end)

    err1 = check_leave_conflict(emp1_id, s2_start, s2_end, asgn2.date)
    if err1:
        return False, err1
    err2 = check_leave_conflict(emp2_id, s1_start, s1_end, asgn1.date)
    if err2:
        return False, err2

    # 3 & 4. Overlapping shifts and minimum rest periods under proposed schedule
    for target_emp, target_id, removed_asgn_id, added_interval, added_dur, added_date in [
        (emp1, emp1_id, asgn1.assignment_id, (s2_start, s2_end), tmpl2.duration_hours, asgn2.date),
        (emp2, emp2_id, asgn2.assignment_id, (s1_start, s1_end), tmpl1.duration_hours, asgn1.date),
    ]:
        other_intervals = [
            (parse_dt(a.scheduled_start), parse_dt(a.scheduled_end))
            for a in assignments
            if a.employee_id == target_id and a.assignment_id != removed_asgn_id
        ]
        other_intervals.append(added_interval)
        other_intervals.sort(key=lambda x: x[0])

        for i in range(len(other_intervals) - 1):
            cur_end = other_intervals[i][1]
            next_start = other_intervals[i + 1][0]
            if next_start < cur_end:
                return False, f"Employee {target_id} would have overlapping shifts ({other_intervals[i][0].isoformat()} and {next_start.isoformat()})"
            rest_hrs = (next_start - cur_end).total_seconds() / 3600.0
            if rest_hrs < min_rest_hours:
                return False, f"Employee {target_id} would have insufficient rest ({rest_hrs:.1f}h < {min_rest_hours}h) between consecutive shifts"

        # 5. Weekly working-hour limits and overtime cap
        weekly_hours: Dict[Tuple[int, int], float] = {}
        for a in assignments:
            if a.employee_id == target_id and a.assignment_id != removed_asgn_id:
                t = tmpl_map.get(a.shift_template_id)
                dur = t.duration_hours if t else (parse_dt(a.scheduled_end) - parse_dt(a.scheduled_start)).total_seconds() / 3600.0
                dt = datetime.date.fromisoformat(a.date)
                iso = dt.isocalendar()
                w_key = (iso.year, iso.week)
                weekly_hours[w_key] = weekly_hours.get(w_key, 0.0) + dur

        add_dt = datetime.date.fromisoformat(added_date)
        add_iso = add_dt.isocalendar()
        add_w_key = (add_iso.year, add_iso.week)
        weekly_hours[add_w_key] = weekly_hours.get(add_w_key, 0.0) + added_dur

        max_allowed = target_emp.contract_hours_per_week + target_emp.max_weekly_overtime_hours
        for w_key, tot_hrs in weekly_hours.items():
            if tot_hrs > max_allowed:
                return False, f"Employee {target_id} would exceed weekly hours limit ({tot_hrs:.1f}h > {max_allowed:.1f}h allowed in week {w_key[1]})"

    return True, None


def apply_shift_swap(
    swap: SwapRequest,
    assignments: List[ShiftAssignment],
    employees: List[Employee],
    skills: List[EmployeeSkill],
    leaves: List[LeaveRequest],
    shift_templates: List[ShiftTemplate],
    min_rest_hours: float = 11.0,
    decision_by: Optional[str] = None,
    decision_notes: Optional[str] = None,
) -> SwapRequest:
    """
    Validates and atomically applies a shift swap.
    Raises ValueError on validation failure without modifying any assignment.
    """
    is_valid, err_msg = validate_shift_swap(
        swap=swap,
        assignments=assignments,
        employees=employees,
        skills=skills,
        leaves=leaves,
        shift_templates=shift_templates,
        min_rest_hours=min_rest_hours,
    )
    if not is_valid:
        raise ValueError(err_msg or "Shift swap validation failed")

    asgn_map = {a.assignment_id: a for a in assignments}
    asgn1 = asgn_map[swap.requester_assignment_id]
    asgn2 = asgn_map[swap.target_assignment_id]

    # Atomically swap assignments and update statuses
    asgn1.employee_id, asgn2.employee_id = asgn2.employee_id, asgn1.employee_id
    asgn1.status = AssignmentStatus.SWAPPED
    asgn2.status = AssignmentStatus.SWAPPED

    swap.status = SwapStatus.APPLIED
    swap.manager_decision_by = decision_by
    swap.manager_decision_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    swap.decision_notes = decision_notes or f"Swap approved and applied by {decision_by}"

    return swap
