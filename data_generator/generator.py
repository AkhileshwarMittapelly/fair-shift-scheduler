"""
Deterministic Synthetic Data Generator for Fair Shift Scheduler.
Implements Steps 2, 3, 4, 5, 6, 7 of the specification.
"""

from __future__ import annotations
import random
import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

from .models import (
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
)

# Standard shift time mappings
SHIFT_DEFINITIONS = [
    {
        "template_id": "TMPL-MORN",
        "code": ShiftCode.A,
        "name": "Morning Shift",
        "start": "07:00",
        "end": "15:30",
        "hours": 8.0,
        "overnight": False,
        "mult": 1.0,
    },
    {
        "template_id": "TMPL-AFTN",
        "code": ShiftCode.B,
        "name": "Afternoon Shift",
        "start": "15:00",
        "end": "23:30",
        "hours": 8.0,
        "overnight": False,
        "mult": 1.15,
    },
    {
        "template_id": "TMPL-NGHT",
        "code": ShiftCode.C,
        "name": "Night Shift",
        "start": "23:00",
        "end": "07:30",
        "hours": 8.0,
        "overnight": True,
        "mult": 1.25,
    },
]

SKILL_DEFINITIONS = [
    ("SKILL-01", "Trauma & Acute Triage", SkillCategory.CLINICAL, ProficiencyLevel.SENIOR, "Emergency and critical triage certification"),
    ("SKILL-02", "ICU Patient Care", SkillCategory.CLINICAL, ProficiencyLevel.MID, "Intensive care unit monitoring and life support"),
    ("SKILL-03", "Pediatric Nursing", SkillCategory.CLINICAL, ProficiencyLevel.MID, "Specialized inpatient pediatric care"),
    ("SKILL-04", "Pharmacy Dispensation", SkillCategory.CLINICAL, ProficiencyLevel.LEAD, "Automated medication and infusion management"),
    ("SKILL-05", "DevOps & Infrastructure", SkillCategory.TECHNICAL, ProficiencyLevel.SENIOR, "High-availability site reliability operations"),
    ("SKILL-06", "Cyber Incident Response", SkillCategory.TECHNICAL, ProficiencyLevel.MID, "SOC security event triage and containment"),
    ("SKILL-07", "Database Administration", SkillCategory.TECHNICAL, ProficiencyLevel.SENIOR, "HA clustering, failover and transactional integrity"),
    ("SKILL-08", "Equipment Safety & OSHA", SkillCategory.SAFETY, ProficiencyLevel.MID, "Safety protocol adherence and hazard control"),
    ("SKILL-09", "Operations Dispatch", SkillCategory.OPERATIONAL, ProficiencyLevel.JUNIOR, "Shift dispatch, radio routing and logistics"),
    ("SKILL-10", "Team Leadership & Esc.", SkillCategory.MANAGEMENT, ProficiencyLevel.LEAD, "Incident commander and team escalation authority"),
]

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth",
    "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa", "Edward", "Deborah",
    "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon", "Jeffrey", "Laura", "Ryan", "Cynthia",
    "Jacob", "Kathleen", "Gary", "Amy", "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen",
    "Stephen", "Anna", "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Frank", "Debra", "Alexander", "Rachel",
    "Raymond", "Catherine", "Patrick", "Carolyn", "Jack", "Janet", "Dennis", "Ruth", "Jerry", "Maria",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
    "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes",
    "Stewart", "Morris", "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
    "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza", "Ruiz", "Hughes",
    "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers", "Long", "Ross", "Foster", "Jimenez",
]

DEPARTMENTS = [
    "Emergency Medicine", "Intensive Care Unit", "Surgical Ward", "Pediatrics",
    "IT Systems Operations", "Cyber Security Operations", "Telemetry & Network",
    "Facilities Operations", "Customer Support Center", "Supply Chain Logistics"
]

LOCATIONS = [
    "Metropolitan Campus - Tower A", "Metropolitan Campus - Tower B",
    "Northside Medical Center", "Eastside Regional Clinic",
    "Data Center West", "Operations Command Center Alpha", "Support Hub Central"
]

HOLIDAYS_2026 = [
    ("HOL-2026-001", "2026-01-01", "New Year's Day", "GLOBAL", True),
    ("HOL-2026-002", "2026-01-19", "Martin Luther King Jr. Day", "US", True),
    ("HOL-2026-003", "2026-02-16", "Presidents' Day", "US", False),
    ("HOL-2026-004", "2026-03-31", "Cesar Chavez Day", "US-WEST", False),
]


@dataclass
class GeneratedDataset:
    scale: str
    seed: int
    teams: List[Team]
    skills: List[Skill]
    employees: List[Employee]
    employee_skills: List[EmployeeSkill]
    shift_templates: List[ShiftTemplate]
    holiday_calendar: List[HolidayCalendar]
    coverage_requirements: List[CoverageRequirement]
    leave_requests: List[LeaveRequest]
    shift_assignments: List[ShiftAssignment]
    swap_requests: List[SwapRequest]
    attendance_events: List[AttendanceEvent]
    ground_truth_anomalies: List[GroundTruthAnomaly]
    metadata: Dict[str, Any]


class SyntheticDataGenerator:
    """
    Produces deterministic, relational, consistent datasets meeting all specs.
    """

    def __init__(self, seed: int = 20261022, scale: str = "starter"):
        """
        :param seed: Fixed integer seed (default 20261022)
        :param scale: 'starter' (100 emp, 10 teams, 14 days) or 'full' (2000 emp, 100 teams, 90 days)
        """
        self.seed = seed
        self.scale = scale.lower()
        self.rng = random.Random(seed)

        if self.scale == "full":
            self.num_employees = 2000
            self.num_teams = 100
            self.num_days = 90
            self.target_leave_requests = 5000
            self.start_date = datetime.date(2026, 1, 1)
        else:
            # Starter scale
            self.num_employees = 100
            self.num_teams = 10
            self.num_days = 14
            self.target_leave_requests = 150
            self.start_date = datetime.date(2026, 1, 1)

    def generate(self) -> GeneratedDataset:
        """
        Executes end-to-end generation following Steps 2 through 7.
        """
        # Step 2: Parent/master tables first
        skills = self._generate_skills()
        teams = self._generate_teams()
        employees, employee_skills = self._generate_employees_and_skills(teams, skills)
        self._assign_team_managers(teams, employees)
        shift_templates = self._generate_shift_templates()
        holiday_calendar = self._generate_holidays()

        # Dependent transactional / operational planning tables
        coverage_requirements = self._generate_coverage_requirements(teams, shift_templates, skills)
        leave_requests = self._generate_leave_requests(employees)

        # Baseline shift assignments adhering to coverage, leaves, skills
        shift_assignments = self._generate_baseline_schedules(
            employees, employee_skills, teams, shift_templates, coverage_requirements, leave_requests
        )

        # Generate swaps with manager approvals
        swap_requests = self._generate_swap_requests(shift_assignments, employees, employee_skills)

        # Generate attendance events reconciling with schedules
        attendance_events = self._generate_attendance_events(shift_assignments)

        # Step 5: Inject 5 labelled edge cases into baseline records
        ground_truth_anomalies = self._inject_labelled_edge_cases(
            employees, shift_assignments, leave_requests, swap_requests, employee_skills
        )

        metadata = {
            "scale": self.scale,
            "seed": self.seed,
            "start_date": self.start_date.isoformat(),
            "num_days": self.num_days,
            "total_employees": len(employees),
            "total_teams": len(teams),
            "total_skills": len(skills),
            "total_employee_skills": len(employee_skills),
            "total_shift_templates": len(shift_templates),
            "total_coverage_requirements": len(coverage_requirements),
            "total_leave_requests": len(leave_requests),
            "total_shift_assignments": len(shift_assignments),
            "total_swap_requests": len(swap_requests),
            "total_attendance_events": len(attendance_events),
            "total_ground_truth_anomalies": len(ground_truth_anomalies),
            "generated_at": "2026-01-01T00:00:00Z",
        }

        return GeneratedDataset(
            scale=self.scale,
            seed=self.seed,
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

    # -------------------------------------------------------------------------
    # Master Table Generators
    # -------------------------------------------------------------------------
    def _generate_skills(self) -> List[Skill]:
        skills = []
        for s_id, name, cat, min_prof, desc in SKILL_DEFINITIONS:
            skills.append(
                Skill(
                    skill_id=s_id,
                    skill_name=name,
                    category=cat,
                    minimum_certification_level=min_prof,
                    description=desc,
                )
            )
        return skills

    def _generate_teams(self) -> List[Team]:
        teams = []
        for i in range(1, self.num_teams + 1):
            team_id = f"TEAM-{i:03d}"
            dept = DEPARTMENTS[(i - 1) % len(DEPARTMENTS)]
            loc = LOCATIONS[(i - 1) % len(LOCATIONS)]
            teams.append(
                Team(
                    team_id=team_id,
                    team_name=f"{dept} Squad {i:02d}",
                    department=dept,
                    manager_id=None,  # Assigned after employees generated
                    location=loc,
                    max_overtime_hours_per_week=12.0,
                    created_at="2025-10-01T08:00:00Z",
                )
            )
        return teams

    def _generate_employees_and_skills(
        self, teams: List[Team], skills: List[Skill]
    ) -> Tuple[List[Employee], List[EmployeeSkill]]:
        employees = []
        employee_skills = []
        num_teams = len(teams)
        skill_ids = [s.skill_id for s in skills]

        prof_levels = [
            ProficiencyLevel.JUNIOR,
            ProficiencyLevel.MID,
            ProficiencyLevel.SENIOR,
            ProficiencyLevel.LEAD,
        ]

        for i in range(1, self.num_employees + 1):
            emp_id = f"EMP-{i:06d}"
            first_name = self.rng.choice(FIRST_NAMES)
            last_name = self.rng.choice(LAST_NAMES)
            email = f"{first_name.lower()}.{last_name.lower()}.{i:04d}@workforce.internal"
            team_id = teams[(i - 1) % num_teams].team_id

            # Contract hours distribution: 80% 40h, 15% 32h, 5% 20h
            rand_contract = self.rng.random()
            if rand_contract < 0.80:
                contract_hours = 40.0
            elif rand_contract < 0.95:
                contract_hours = 32.0
            else:
                contract_hours = 20.0

            # Hourly rate based on seniority
            hourly_rate = round(self.rng.uniform(28.0, 68.0), 2)

            hire_year = self.rng.randint(2018, 2025)
            hire_month = self.rng.randint(1, 12)
            hire_day = self.rng.randint(1, 28)
            hire_date = f"{hire_year:04d}-{hire_month:02d}-{hire_day:02d}"

            emp = Employee(
                employee_id=emp_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                team_id=team_id,
                hire_date=hire_date,
                contract_hours_per_week=contract_hours,
                max_weekly_overtime_hours=12.0,
                hourly_rate=hourly_rate,
                employment_status=EmploymentStatus.ACTIVE,
                created_at="2025-11-01T00:00:00Z",
            )
            employees.append(emp)

            # Assign 1 to 3 skills per employee
            assigned_skills = self.rng.sample(skill_ids, k=self.rng.randint(1, 3))
            for s_id in assigned_skills:
                es_id = f"ES-{emp_id}-{s_id}"
                prof = self.rng.choice(prof_levels)
                certified_year = max(hire_year, 2022)
                certified_date = f"{certified_year}-01-15"
                employee_skills.append(
                    EmployeeSkill(
                        employee_skill_id=es_id,
                        employee_id=emp_id,
                        skill_id=s_id,
                        proficiency_level=prof,
                        certified_date=certified_date,
                        expiry_date=f"{certified_year + 3}-01-15",
                    )
                )

        return employees, employee_skills

    def _assign_team_managers(self, teams: List[Team], employees: List[Employee]):
        # Assign first employee of each team as team manager
        team_emp_map: Dict[str, List[Employee]] = {t.team_id: [] for t in teams}
        for emp in employees:
            team_emp_map[emp.team_id].append(emp)

        for t in teams:
            team_emps = team_emp_map.get(t.team_id, [])
            if team_emps:
                t.manager_id = team_emps[0].employee_id

    def _generate_shift_templates(self) -> List[ShiftTemplate]:
        templates = []
        for s in SHIFT_DEFINITIONS:
            templates.append(
                ShiftTemplate(
                    shift_template_id=s["template_id"],
                    shift_code=s["code"],
                    shift_name=s["name"],
                    start_time=s["start"],
                    end_time=s["end"],
                    duration_hours=s["hours"],
                    is_overnight=s["overnight"],
                    differential_rate_multiplier=s["mult"],
                )
            )
        return templates

    def _generate_holidays(self) -> List[HolidayCalendar]:
        return [
            HolidayCalendar(
                holiday_id=h[0],
                holiday_date=h[1],
                holiday_name=h[2],
                region=h[3],
                is_mandatory_off=h[4],
            )
            for h in HOLIDAYS_2026
        ]

    # -------------------------------------------------------------------------
    # Operational & Transactional Generators
    # -------------------------------------------------------------------------
    def _generate_coverage_requirements(
        self, teams: List[Team], shift_templates: List[ShiftTemplate], skills: List[Skill]
    ) -> List[CoverageRequirement]:
        requirements = []
        counter = 1
        skill_ids = [s.skill_id for s in skills]

        # For each day, each team, each shift template
        for day_offset in range(self.num_days):
            current_date = self.start_date + datetime.timedelta(days=day_offset)
            date_str = current_date.isoformat()
            is_weekend = current_date.weekday() >= 5

            for team in teams:
                for tmpl in shift_templates:
                    # Scale headcounts: weekend slightly lighter, night slightly lighter
                    if tmpl.shift_code == ShiftCode.C:  # Night
                        min_hc = 1 if is_weekend else 2
                        target_hc = 2 if is_weekend else 3
                    elif tmpl.shift_code == ShiftCode.B:  # Afternoon
                        min_hc = 2 if is_weekend else 3
                        target_hc = 3 if is_weekend else 4
                    else:  # Morning
                        min_hc = 2 if is_weekend else 3
                        target_hc = 3 if is_weekend else 4

                    # If starter scale, keep minimum headcount modest so everyone gets covered
                    if self.scale == "starter":
                        min_hc = 1
                        target_hc = 2

                    # General coverage requirement
                    req_id = f"COV-2026-{counter:06d}"
                    counter += 1
                    requirements.append(
                        CoverageRequirement(
                            requirement_id=req_id,
                            date=date_str,
                            shift_template_id=tmpl.shift_template_id,
                            team_id=team.team_id,
                            skill_id=None,  # General team headcount
                            min_headcount=min_hc,
                            target_headcount=target_hc,
                            priority_weight=1.0,
                        )
                    )

                    # For critical shifts (Morning & Night), require 1 specific critical skill
                    if tmpl.shift_code in (ShiftCode.A, ShiftCode.C):
                        req_id_skill = f"COV-2026-{counter:06d}"
                        counter += 1
                        # Pick a deterministic skill based on team index
                        team_num = int(team.team_id.split("-")[1])
                        req_skill = skill_ids[(team_num + day_offset) % len(skill_ids)]
                        requirements.append(
                            CoverageRequirement(
                                requirement_id=req_id_skill,
                                date=date_str,
                                shift_template_id=tmpl.shift_template_id,
                                team_id=team.team_id,
                                skill_id=req_skill,
                                min_headcount=1,
                                target_headcount=1,
                                priority_weight=1.5,
                            )
                        )
        return requirements

    def _generate_leave_requests(self, employees: List[Employee]) -> List[LeaveRequest]:
        leaves = []
        leave_types = [
            LeaveType.ANNUAL,
            LeaveType.SICK,
            LeaveType.BEREAVEMENT,
            LeaveType.PARENTAL,
            LeaveType.COMPENSATORY,
        ]
        reasons = {
            LeaveType.ANNUAL: "Family vacation / personal downtime",
            LeaveType.SICK: "Medical appointment / acute recovery",
            LeaveType.BEREAVEMENT: "Bereavement leave",
            LeaveType.PARENTAL: "Parental bonding leave",
            LeaveType.COMPENSATORY: "Compensatory time off for on-call coverage",
        }

        # Calculate how many leaves to generate
        total_to_gen = min(self.target_leave_requests, self.num_employees * 4)
        emp_indices = list(range(len(employees)))

        for i in range(1, total_to_gen + 1):
            leave_id = f"LVE-2026-{i:06d}"
            emp = employees[self.rng.choice(emp_indices)]
            l_type = self.rng.choice(leave_types)

            # Pick start date within simulation window
            day_offset = self.rng.randint(0, self.num_days - 1)
            duration_days = self.rng.choices([1, 2, 3, 5], weights=[0.5, 0.25, 0.15, 0.1])[0]
            start_d = self.start_date + datetime.timedelta(days=day_offset)
            end_d = start_d + datetime.timedelta(days=duration_days - 1)

            # Approval outcome: 85% APPROVED, 10% REJECTED, 5% PENDING
            outcome_rand = self.rng.random()
            if outcome_rand < 0.85:
                status = LeaveStatus.APPROVED
                dec_by = "EMP-000001"  # Manager
                dec_ts = (start_d - datetime.timedelta(days=self.rng.randint(5, 15))).isoformat() + "T10:00:00Z"
                notes = "Approved in accordance with team leave quota"
            elif outcome_rand < 0.95:
                status = LeaveStatus.REJECTED
                dec_by = "EMP-000001"
                dec_ts = (start_d - datetime.timedelta(days=self.rng.randint(3, 8))).isoformat() + "T14:30:00Z"
                notes = "Rejected: Insufficient staffing during peak shift"
            else:
                status = LeaveStatus.PENDING
                dec_by = None
                dec_ts = None
                notes = None

            leaves.append(
                LeaveRequest(
                    leave_id=leave_id,
                    employee_id=emp.employee_id,
                    start_date=start_d.isoformat(),
                    end_date=end_d.isoformat(),
                    leave_type=l_type,
                    status=status,
                    reason=reasons[l_type],
                    decision_by=dec_by,
                    decision_timestamp=dec_ts,
                    decision_notes=notes,
                )
            )

        return leaves

    def _generate_baseline_schedules(
        self,
        employees: List[Employee],
        employee_skills: List[EmployeeSkill],
        teams: List[Team],
        shift_templates: List[ShiftTemplate],
        coverage_requirements: List[CoverageRequirement],
        leave_requests: List[LeaveRequest],
    ) -> List[ShiftAssignment]:
        """
        Builds a valid, fair baseline schedule adhering to hard labor constraints:
        - Respects approved leaves
        - Respects skills
        - Respects 40h standard week + max 1 shift/day
        """
        assignments: List[ShiftAssignment] = []
        assignment_counter = 1

        # Build quick lookups
        team_employees: Dict[str, List[Employee]] = {t.team_id: [] for t in teams}
        for emp in employees:
            team_employees[emp.team_id].append(emp)

        # Employee skills lookup: emp_id -> set of skill_ids
        emp_skill_map: Dict[str, set] = {e.employee_id: set() for e in employees}
        for es in employee_skills:
            emp_skill_map[es.employee_id].add(es.skill_id)

        # Approved leaves lookup: emp_id -> set of date strings
        emp_leave_dates: Dict[str, set] = {e.employee_id: set() for e in employees}
        for lr in leave_requests:
            if lr.status == LeaveStatus.APPROVED:
                cur = datetime.date.fromisoformat(lr.start_date)
                end = datetime.date.fromisoformat(lr.end_date)
                while cur <= end:
                    emp_leave_dates[lr.employee_id].add(cur.isoformat())
                    cur += datetime.timedelta(days=1)

        # Group requirements by date & team
        req_by_date_team: Dict[Tuple[str, str], List[CoverageRequirement]] = {}
        for req in coverage_requirements:
            key = (req.date, req.team_id)
            if key not in req_by_date_team:
                req_by_date_team[key] = []
            req_by_date_team[key].append(req)

        tmpl_by_id = {t.shift_template_id: t for t in shift_templates}

        # Track weekly hours for employees to maintain fairness and stay within contract limits
        emp_weekly_hours: Dict[Tuple[str, int], float] = {}  # (emp_id, week_num) -> hours
        emp_shift_dates: Dict[str, set] = {e.employee_id: set() for e in employees}
        emp_assigned_intervals: Dict[str, List[Tuple[datetime.datetime, datetime.datetime]]] = {
            e.employee_id: [] for e in employees
        }

        for day_offset in range(self.num_days):
            current_date = self.start_date + datetime.timedelta(days=day_offset)
            date_str = current_date.isoformat()
            week_num = current_date.isocalendar()[1]

            for team in teams:
                team_members = team_employees.get(team.team_id, [])
                if not team_members:
                    continue

                reqs = req_by_date_team.get((date_str, team.team_id), [])

                # Sort requirements by priority (critical skill requirements first)
                sorted_reqs = sorted(reqs, key=lambda r: r.priority_weight, reverse=True)

                for req in sorted_reqs:
                    tmpl = tmpl_by_id[req.shift_template_id]
                    needed = req.min_headcount

                    start_ts = f"{date_str}T{tmpl.start_time}:00Z"
                    if tmpl.is_overnight:
                        next_day = current_date + datetime.timedelta(days=1)
                        end_ts = f"{next_day.isoformat()}T{tmpl.end_time}:00Z"
                        next_day_str = next_day.isoformat()
                    else:
                        end_ts = f"{date_str}T{tmpl.end_time}:00Z"
                        next_day_str = None

                    cand_start = datetime.datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
                    cand_end = datetime.datetime.fromisoformat(end_ts.replace("Z", "+00:00"))

                    # Filter available candidates in this team
                    candidates = []
                    for emp in team_members:
                        # Cannot already have a shift today
                        if date_str in emp_shift_dates[emp.employee_id]:
                            continue
                        # Cannot be on approved leave
                        if date_str in emp_leave_dates[emp.employee_id]:
                            continue
                        # Overnight shift cannot run into an approved leave the following day
                        if next_day_str and next_day_str in emp_leave_dates[emp.employee_id]:
                            continue
                        # If requirement specifies a skill, employee must have it
                        if req.skill_id and req.skill_id not in emp_skill_map[emp.employee_id]:
                            continue
                        # Check hours worked this week (keep below contract + 8h)
                        cur_hours = emp_weekly_hours.get((emp.employee_id, week_num), 0.0)
                        if cur_hours + tmpl.duration_hours > emp.contract_hours_per_week + 8.0:
                            continue

                        # Ensure no timestamp interval overlap with existing assigned shifts [start, end)
                        has_overlap = False
                        for prev_start, prev_end in emp_assigned_intervals[emp.employee_id]:
                            if cand_start < prev_end and prev_start < cand_end:
                                has_overlap = True
                                break
                        if has_overlap:
                            continue

                        candidates.append((cur_hours, emp))

                    # Sort candidates by current weekly hours ascending for fairness
                    candidates.sort(key=lambda x: x[0])

                    assigned_count = 0
                    for _, emp in candidates:
                        if assigned_count >= needed:
                            break

                        # Deterministic assignment ID
                        shift_letter = tmpl.shift_code.value if hasattr(tmpl.shift_code, "value") else str(tmpl.shift_code)
                        asgn_id = f"SHIFT-{date_str}-{shift_letter}-{assignment_counter:06d}"
                        assignment_counter += 1

                        asgn = ShiftAssignment(
                            assignment_id=asgn_id,
                            date=date_str,
                            shift_template_id=tmpl.shift_template_id,
                            employee_id=emp.employee_id,
                            team_id=team.team_id,
                            role_skill_id=req.skill_id,
                            scheduled_start=start_ts,
                            scheduled_end=end_ts,
                            status=AssignmentStatus.SCHEDULED,
                            created_at="2025-12-15T00:00:00Z",
                            created_by="SYSTEM_SOLVER",
                        )
                        assignments.append(asgn)

                        emp_shift_dates[emp.employee_id].add(date_str)
                        emp_assigned_intervals[emp.employee_id].append((cand_start, cand_end))
                        emp_weekly_hours[(emp.employee_id, week_num)] = (
                            emp_weekly_hours.get((emp.employee_id, week_num), 0.0) + tmpl.duration_hours
                        )
                        assigned_count += 1

        return assignments

    def _generate_swap_requests(
        self,
        assignments: List[ShiftAssignment],
        employees: List[Employee],
        employee_skills: List[EmployeeSkill],
    ) -> List[SwapRequest]:
        """
        Creates shift swap transactions with complete manager approval audit trails.
        """
        swaps: List[SwapRequest] = []
        if len(assignments) < 10:
            return swaps

        num_swaps = min(200 if self.scale == "full" else 20, len(assignments) // 4)
        default_manager_id = "EMP-000001"

        # Group assignments by date for easy peer swap finding
        asgn_by_date: Dict[str, List[ShiftAssignment]] = {}
        for a in assignments:
            if a.date not in asgn_by_date:
                asgn_by_date[a.date] = []
            asgn_by_date[a.date].append(a)

        unique_dates = list(asgn_by_date.keys())

        for i in range(1, num_swaps + 1):
            swap_id = f"SWP-2026-{i:06d}"
            date_choice = self.rng.choice(unique_dates)
            shifts_today = asgn_by_date[date_choice]

            if len(shifts_today) < 2:
                continue

            asgn1, asgn2 = self.rng.sample(shifts_today, 2)
            if asgn1.employee_id == asgn2.employee_id:
                continue

            req_time = f"{date_choice}T08:00:00Z"
            peer_time = f"{date_choice}T08:30:00Z"

            # Use iteration-local variables to avoid scoping bug where PENDING_MANAGER
            # overwrites the outer manager_id, affecting all subsequent loop iterations.
            outcome = self.rng.random()
            if outcome < 0.70:
                status = SwapStatus.APPLIED
                cur_manager_id = default_manager_id
                mgr_time: Optional[str] = f"{date_choice}T09:15:00Z"
                asgn1.status = AssignmentStatus.SWAPPED
                asgn2.status = AssignmentStatus.SWAPPED
                notes: Optional[str] = "Swap verified: Skills and working hour constraints satisfied."
            elif outcome < 0.85:
                status = SwapStatus.REJECTED
                cur_manager_id = default_manager_id
                mgr_time = f"{date_choice}T09:15:00Z"
                notes = "Swap rejected: Consecutive rest period violation detected."
            else:
                status = SwapStatus.PENDING_MANAGER
                cur_manager_id = None
                mgr_time = None
                notes = None

            swaps.append(
                SwapRequest(
                    swap_id=swap_id,
                    requester_assignment_id=asgn1.assignment_id,
                    target_assignment_id=asgn2.assignment_id,
                    requester_employee_id=asgn1.employee_id,
                    target_employee_id=asgn2.employee_id,
                    status=status,
                    requested_at=req_time,
                    peer_agreed_at=peer_time,
                    manager_decision_by=cur_manager_id,
                    manager_decision_at=mgr_time,
                    decision_notes=notes,
                )
            )

        return swaps

    def _generate_attendance_events(
        self, assignments: List[ShiftAssignment]
    ) -> List[AttendanceEvent]:
        """
        Creates CLOCK_IN and CLOCK_OUT events that reconcile with schedules.
        Calculates matched_schedule_diff_minutes based on actual punch variance.
        """
        events: List[AttendanceEvent] = []

        for asgn in assignments:
            if asgn.status == AssignmentStatus.CANCELLED:
                continue

            # Deterministic micro-variance: -10 min to +15 min
            clock_in_diff = self.rng.randint(-10, 15)
            clock_out_diff = self.rng.randint(-5, 25)

            sched_start = datetime.datetime.fromisoformat(asgn.scheduled_start.replace("Z", "+00:00"))
            sched_end = datetime.datetime.fromisoformat(asgn.scheduled_end.replace("Z", "+00:00"))

            actual_in = sched_start + datetime.timedelta(minutes=clock_in_diff)
            actual_out = sched_end + datetime.timedelta(minutes=clock_out_diff)

            # Punch in
            in_ts_str = actual_in.strftime("%Y%m%dT%H%M%S")
            att_in_id = f"ATT-{asgn.employee_id}-{in_ts_str}"
            events.append(
                AttendanceEvent(
                    attendance_id=att_in_id,
                    employee_id=asgn.employee_id,
                    assignment_id=asgn.assignment_id,
                    event_type=AttendanceEventType.CLOCK_IN,
                    event_timestamp=actual_in.isoformat(),
                    source_device="TERMINAL-BADGE-READER-04",
                    matched_schedule_diff_minutes=float(clock_in_diff),
                )
            )

            # Punch out
            out_ts_str = actual_out.strftime("%Y%m%dT%H%M%S")
            att_out_id = f"ATT-{asgn.employee_id}-{out_ts_str}"
            events.append(
                AttendanceEvent(
                    attendance_id=att_out_id,
                    employee_id=asgn.employee_id,
                    assignment_id=asgn.assignment_id,
                    event_type=AttendanceEventType.CLOCK_OUT,
                    event_timestamp=actual_out.isoformat(),
                    source_device="TERMINAL-BADGE-READER-04",
                    matched_schedule_diff_minutes=float(clock_out_diff),
                )
            )

        return events

    # -------------------------------------------------------------------------
    # Step 5: Inject Labelled Edge Cases
    # -------------------------------------------------------------------------
    def _inject_labelled_edge_cases(
        self,
        employees: List[Employee],
        assignments: List[ShiftAssignment],
        leave_requests: List[LeaveRequest],
        swap_requests: List[SwapRequest],
        employee_skills: List[EmployeeSkill],
    ) -> List[GroundTruthAnomaly]:
        """
        Injects the 5 required labelled edge cases into the dataset, recording
        them into a separate ground truth collection with precise rule references.
        """
        anomalies: List[GroundTruthAnomaly] = []
        gt_counter = 1

        if len(assignments) < 20 or len(employees) < 10:
            return anomalies

        # ---------------------------------------------------------------------
        # Case 1: Employee Double-Booked
        # Assign an employee to two overlapping shifts on the same day
        # ---------------------------------------------------------------------
        target_emp = employees[1]
        base_asgn = assignments[0]
        # Inject an overlapping second shift on the same date
        dup_asgn_id = f"SHIFT-{base_asgn.date}-B-999001"
        dup_asgn = ShiftAssignment(
            assignment_id=dup_asgn_id,
            date=base_asgn.date,
            shift_template_id="TMPL-AFTN",
            employee_id=base_asgn.employee_id,  # Same employee
            team_id=base_asgn.team_id,
            role_skill_id=None,
            scheduled_start=f"{base_asgn.date}T15:00:00Z",
            scheduled_end=f"{base_asgn.date}T23:30:00Z",
            status=AssignmentStatus.SCHEDULED,
            created_at="2026-01-01T00:00:00Z",
            created_by="ANOMALY_INJECTION",
        )
        assignments.append(dup_asgn)

        anomalies.append(
            GroundTruthAnomaly(
                anomaly_id=f"GT-{gt_counter:06d}",
                anomaly_type=AnomalyType.EMPLOYEE_DOUBLE_BOOKED,
                entity_type="ShiftAssignment",
                primary_entity_id=base_asgn.assignment_id,
                secondary_entity_id=dup_asgn.assignment_id,
                description=f"Employee {base_asgn.employee_id} double-booked across shifts on date {base_asgn.date}",
                injected_timestamp="2026-01-01T00:00:00Z",
                severity="CRITICAL",
                expected_detection_rule="RULE_NO_CONCURRENT_OR_OVERLAPPING_SHIFTS",
            )
        )
        gt_counter += 1

        # ---------------------------------------------------------------------
        # Case 2: Approved Leave Overlaps Assigned Shift
        # Schedule an employee on a date when they have an APPROVED leave
        # ---------------------------------------------------------------------
        approved_leaves = [l for l in leave_requests if l.status == LeaveStatus.APPROVED]
        if approved_leaves:
            target_leave = approved_leaves[0]
            # Create a shift assignment during this employee's approved leave window
            leave_asgn_id = f"SHIFT-{target_leave.start_date}-A-999002"
            leave_asgn = ShiftAssignment(
                assignment_id=leave_asgn_id,
                date=target_leave.start_date,
                shift_template_id="TMPL-MORN",
                employee_id=target_leave.employee_id,
                team_id=employees[0].team_id,
                role_skill_id=None,
                scheduled_start=f"{target_leave.start_date}T07:00:00Z",
                scheduled_end=f"{target_leave.start_date}T15:30:00Z",
                status=AssignmentStatus.SCHEDULED,
                created_at="2026-01-01T00:00:00Z",
                created_by="ANOMALY_INJECTION",
            )
            assignments.append(leave_asgn)

            anomalies.append(
                GroundTruthAnomaly(
                    anomaly_id=f"GT-{gt_counter:06d}",
                    anomaly_type=AnomalyType.APPROVED_LEAVE_OVERLAPS_SHIFT,
                    entity_type="ShiftAssignment",
                    primary_entity_id=leave_asgn.assignment_id,
                    secondary_entity_id=target_leave.leave_id,
                    description=f"Employee {target_leave.employee_id} assigned shift during approved leave {target_leave.leave_id} on {target_leave.start_date}",
                    injected_timestamp="2026-01-01T00:00:00Z",
                    severity="CRITICAL",
                    expected_detection_rule="RULE_APPROVED_LEAVE_NON_CONFLICT",
                )
            )
            gt_counter += 1

        # ---------------------------------------------------------------------
        # Case 3: Required Skill Absent
        # Assign a critical skill requirement to an employee who DOES NOT have it
        # ---------------------------------------------------------------------
        # Find an employee without SKILL-01
        target_emp_for_skill = None
        for emp in employees:
            held_skills = [es.skill_id for es in employee_skills if es.employee_id == emp.employee_id]
            if "SKILL-01" not in held_skills:
                target_emp_for_skill = emp
                break

        if target_emp_for_skill:
            asgn_skill_absent = assignments[5]
            prev_emp_id = asgn_skill_absent.employee_id
            asgn_skill_absent.employee_id = target_emp_for_skill.employee_id
            asgn_skill_absent.role_skill_id = "SKILL-01"  # Requires SKILL-01 which emp lacks

            # Prevent incidental double-booking: if target employee already has a shift on this date,
            # swap the previous employee into that shift.
            for other_asgn in assignments:
                if (
                    other_asgn is not asgn_skill_absent
                    and other_asgn.employee_id == target_emp_for_skill.employee_id
                    and other_asgn.date == asgn_skill_absent.date
                ):
                    other_asgn.employee_id = prev_emp_id
                    break

            anomalies.append(
                GroundTruthAnomaly(
                    anomaly_id=f"GT-{gt_counter:06d}",
                    anomaly_type=AnomalyType.REQUIRED_SKILL_ABSENT,
                    entity_type="ShiftAssignment",
                    primary_entity_id=asgn_skill_absent.assignment_id,
                    secondary_entity_id="SKILL-01",
                    description=f"Shift requires SKILL-01 but assigned employee {target_emp_for_skill.employee_id} lacks certified qualification",
                    injected_timestamp="2026-01-01T00:00:00Z",
                    severity="HIGH",
                    expected_detection_rule="RULE_MANDATORY_ROLE_SKILL_MATCH",
                )
            )
            gt_counter += 1

        # ---------------------------------------------------------------------
        # Case 4: Overtime Cap Exceeded
        # Schedule an employee for excessive hours within a single week (> contract + 12h)
        # ---------------------------------------------------------------------
        ot_emp = employees[2]
        ot_d1 = self.start_date + datetime.timedelta(days=7)
        ot_d2 = self.start_date + datetime.timedelta(days=8)
        ot_d3 = self.start_date + datetime.timedelta(days=9)

        ot_date_1 = ot_d1.isoformat()
        ot_date_2 = ot_d2.isoformat()
        ot_date_3 = ot_d3.isoformat()

        ot_end_1 = (ot_d1 + datetime.timedelta(days=1)).isoformat()
        ot_end_2 = (ot_d2 + datetime.timedelta(days=1)).isoformat()
        ot_end_3 = (ot_d3 + datetime.timedelta(days=1)).isoformat()

        ot_asgn_1 = ShiftAssignment(
            assignment_id=f"SHIFT-{ot_date_1}-C-999003",
            date=ot_date_1,
            shift_template_id="TMPL-NGHT",
            employee_id=ot_emp.employee_id,
            team_id=ot_emp.team_id,
            role_skill_id=None,
            scheduled_start=f"{ot_date_1}T23:00:00Z",
            scheduled_end=f"{ot_end_1}T07:30:00Z",
            status=AssignmentStatus.SCHEDULED,
            created_at="2026-01-01T00:00:00Z",
            created_by="ANOMALY_INJECTION",
        )
        ot_asgn_2 = ShiftAssignment(
            assignment_id=f"SHIFT-{ot_date_2}-C-999004",
            date=ot_date_2,
            shift_template_id="TMPL-NGHT",
            employee_id=ot_emp.employee_id,
            team_id=ot_emp.team_id,
            role_skill_id=None,
            scheduled_start=f"{ot_date_2}T23:00:00Z",
            scheduled_end=f"{ot_end_2}T07:30:00Z",
            status=AssignmentStatus.SCHEDULED,
            created_at="2026-01-01T00:00:00Z",
            created_by="ANOMALY_INJECTION",
        )
        ot_asgn_3 = ShiftAssignment(
            assignment_id=f"SHIFT-{ot_date_3}-C-999005",
            date=ot_date_3,
            shift_template_id="TMPL-NGHT",
            employee_id=ot_emp.employee_id,
            team_id=ot_emp.team_id,
            role_skill_id=None,
            scheduled_start=f"{ot_date_3}T23:00:00Z",
            scheduled_end=f"{ot_end_3}T07:30:00Z",
            status=AssignmentStatus.SCHEDULED,
            created_at="2026-01-01T00:00:00Z",
            created_by="ANOMALY_INJECTION",
        )
        assignments.extend([ot_asgn_1, ot_asgn_2, ot_asgn_3])

        anomalies.append(
            GroundTruthAnomaly(
                anomaly_id=f"GT-{gt_counter:06d}",
                anomaly_type=AnomalyType.OVERTIME_CAP_EXCEEDED,
                entity_type="Employee",
                primary_entity_id=ot_emp.employee_id,
                secondary_entity_id=ot_asgn_1.assignment_id,
                description=f"Employee {ot_emp.employee_id} exceeded maximum statutory weekly overtime limit (scheduled > 52.0h)",
                injected_timestamp="2026-01-01T00:00:00Z",
                severity="HIGH",
                expected_detection_rule="RULE_MAX_WEEKLY_LABOR_AND_OVERTIME_CAP",
            )
        )
        gt_counter += 1

        # ---------------------------------------------------------------------
        # Case 5: Swap Applied Without Approval
        # Swap executed with status APPLIED, but manager_decision_by is NULL
        # ---------------------------------------------------------------------
        illegal_swap = SwapRequest(
            swap_id=f"SWP-2026-{999001:06d}",
            requester_assignment_id=assignments[10].assignment_id,
            target_assignment_id=assignments[11].assignment_id,
            requester_employee_id=assignments[10].employee_id,
            target_employee_id=assignments[11].employee_id,
            status=SwapStatus.APPLIED,  # Marked as applied!
            requested_at="2026-01-05T08:00:00Z",
            peer_agreed_at="2026-01-05T08:15:00Z",
            manager_decision_by=None,  # MISSING MANAGER APPROVAL!
            manager_decision_at=None,
            decision_notes="Bypassed manager signoff via direct swap override",
        )
        swap_requests.append(illegal_swap)

        anomalies.append(
            GroundTruthAnomaly(
                anomaly_id=f"GT-{gt_counter:06d}",
                anomaly_type=AnomalyType.SWAP_APPLIED_WITHOUT_APPROVAL,
                entity_type="SwapRequest",
                primary_entity_id=illegal_swap.swap_id,
                secondary_entity_id=None,
                description=f"Shift swap {illegal_swap.swap_id} executed and APPLIED without required manager authorization",
                injected_timestamp="2026-01-01T00:00:00Z",
                severity="CRITICAL",
                expected_detection_rule="RULE_SWAP_REQUIRES_MANAGER_APPROVAL",
            )
        )
        gt_counter += 1

        return anomalies
