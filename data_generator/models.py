"""
Core domain models and schema definitions for the Fair Shift Scheduling System.
Complies with Step 1 (Data Dictionary) and Step 3 (Deterministic Nomenclature).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any


class EmploymentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ON_LEAVE = "ON_LEAVE"
    TERMINATED = "TERMINATED"


class SkillCategory(str, Enum):
    CLINICAL = "CLINICAL"
    TECHNICAL = "TECHNICAL"
    OPERATIONAL = "OPERATIONAL"
    SAFETY = "SAFETY"
    MANAGEMENT = "MANAGEMENT"


class ProficiencyLevel(str, Enum):
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD = "LEAD"


class ShiftCode(str, Enum):
    A = "A"  # Morning (07:00 - 15:30)
    B = "B"  # Afternoon / Evening (15:00 - 23:30)
    C = "C"  # Night (23:00 - 07:30)

    def __str__(self) -> str:
        return self.value


class LeaveType(str, Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    BEREAVEMENT = "BEREAVEMENT"
    PARENTAL = "PARENTAL"
    COMPENSATORY = "COMPENSATORY"
    UNPAID = "UNPAID"


class LeaveStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AssignmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    SWAPPED = "SWAPPED"
    ABSENT = "ABSENT"
    CANCELLED = "CANCELLED"


class SwapStatus(str, Enum):
    PENDING_PEER = "PENDING_PEER"
    PENDING_MANAGER = "PENDING_MANAGER"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    CANCELLED = "CANCELLED"


class AttendanceEventType(str, Enum):
    CLOCK_IN = "CLOCK_IN"
    CLOCK_OUT = "CLOCK_OUT"
    BREAK_START = "BREAK_START"
    BREAK_END = "BREAK_END"


class AnomalyType(str, Enum):
    EMPLOYEE_DOUBLE_BOOKED = "EMPLOYEE_DOUBLE_BOOKED"
    APPROVED_LEAVE_OVERLAPS_SHIFT = "APPROVED_LEAVE_OVERLAPS_SHIFT"
    REQUIRED_SKILL_ABSENT = "REQUIRED_SKILL_ABSENT"
    OVERTIME_CAP_EXCEEDED = "OVERTIME_CAP_EXCEEDED"
    SWAP_APPLIED_WITHOUT_APPROVAL = "SWAP_APPLIED_WITHOUT_APPROVAL"


@dataclass
class Skill:
    skill_id: str  # PK: SKILL-01
    skill_name: str
    category: SkillCategory
    minimum_certification_level: ProficiencyLevel
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Team:
    team_id: str  # PK: TEAM-001
    team_name: str
    department: str
    manager_id: Optional[str]  # FK: Employee.employee_id
    location: str
    max_overtime_hours_per_week: float
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Employee:
    employee_id: str  # PK: EMP-000001
    first_name: str
    last_name: str
    email: str
    team_id: str  # FK: Team.team_id
    hire_date: str  # YYYY-MM-DD
    contract_hours_per_week: float  # e.g., 40.0, 32.0, 20.0
    max_weekly_overtime_hours: float  # e.g., 10.0 or 12.0
    hourly_rate: float
    employment_status: EmploymentStatus
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EmployeeSkill:
    employee_skill_id: str  # PK: ES-EMP-000001-SKILL-01
    employee_id: str  # FK: Employee.employee_id
    skill_id: str  # FK: Skill.skill_id
    proficiency_level: ProficiencyLevel
    certified_date: str  # YYYY-MM-DD
    expiry_date: Optional[str]  # YYYY-MM-DD

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HolidayCalendar:
    holiday_id: str  # PK: HOL-2026-001
    holiday_date: str  # YYYY-MM-DD
    holiday_name: str
    region: str
    is_mandatory_off: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShiftTemplate:
    shift_template_id: str  # PK: TMPL-MORN, TMPL-AFTN, TMPL-NGHT
    shift_code: ShiftCode  # A, B, C
    shift_name: str
    start_time: str  # HH:MM e.g. "07:00"
    end_time: str  # HH:MM e.g. "15:30"
    duration_hours: float  # 8.0
    is_overnight: bool
    differential_rate_multiplier: float  # 1.0, 1.15, 1.25

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CoverageRequirement:
    requirement_id: str  # PK: COV-2026-000001
    date: str  # YYYY-MM-DD
    shift_template_id: str  # FK: ShiftTemplate.shift_template_id
    team_id: str  # FK: Team.team_id
    skill_id: Optional[str]  # FK: Skill.skill_id (if skill-specific)
    min_headcount: int
    target_headcount: int
    priority_weight: float  # 1.0 (standard) to 2.0 (critical)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeaveRequest:
    leave_id: str  # PK: LVE-2026-000001
    employee_id: str  # FK: Employee.employee_id
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    leave_type: LeaveType
    status: LeaveStatus
    reason: str
    decision_by: Optional[str]  # FK: Employee.employee_id (Manager/HR)
    decision_timestamp: Optional[str]  # ISO8601
    decision_notes: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShiftAssignment:
    assignment_id: str  # PK: SHIFT-2026-01-01-A-000001 (SHIFT-YYYY-MM-DD-<Code>-<Seq>)
    date: str  # YYYY-MM-DD
    shift_template_id: str  # FK: ShiftTemplate.shift_template_id
    employee_id: str  # FK: Employee.employee_id
    team_id: str  # FK: Team.team_id
    role_skill_id: Optional[str]  # FK: Skill.skill_id
    scheduled_start: str  # ISO8601
    scheduled_end: str  # ISO8601
    status: AssignmentStatus
    created_at: str
    created_by: str  # "SYSTEM_SOLVER" or "MANAGER"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SwapRequest:
    swap_id: str  # PK: SWP-2026-000001
    requester_assignment_id: str  # FK: ShiftAssignment.assignment_id
    target_assignment_id: str  # FK: ShiftAssignment.assignment_id
    requester_employee_id: str  # FK: Employee.employee_id
    target_employee_id: str  # FK: Employee.employee_id
    status: SwapStatus
    requested_at: str  # ISO8601
    peer_agreed_at: Optional[str]  # ISO8601
    manager_decision_by: Optional[str]  # FK: Employee.employee_id
    manager_decision_at: Optional[str]  # ISO8601
    decision_notes: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AttendanceEvent:
    attendance_id: str  # PK: ATT-<employee-id>-<timestamp>
    employee_id: str  # FK: Employee.employee_id
    assignment_id: Optional[str]  # FK: ShiftAssignment.assignment_id
    event_type: AttendanceEventType
    event_timestamp: str  # ISO8601
    source_device: str
    matched_schedule_diff_minutes: float  # early (-), late (+), 0.0 if exact

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GroundTruthAnomaly:
    anomaly_id: str  # GT-000001
    anomaly_type: AnomalyType
    entity_type: str  # "ShiftAssignment", "LeaveRequest", "SwapRequest", "Employee"
    primary_entity_id: str
    secondary_entity_id: Optional[str]
    description: str
    injected_timestamp: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM"
    expected_detection_rule: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeaveStateTransitionEvent:
    event_id: str  # LSTE-2026-000001
    leave_id: str  # FK: LeaveRequest.leave_id
    from_status: Optional[str]
    to_status: str
    changed_by: str  # Employee ID
    timestamp: str  # ISO8601
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SwapStateTransitionEvent:
    event_id: str  # SSTE-2026-000001
    swap_id: str  # FK: SwapRequest.swap_id
    from_status: Optional[str]
    to_status: str
    changed_by: str  # Employee ID
    timestamp: str  # ISO8601
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
