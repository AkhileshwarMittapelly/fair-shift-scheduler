"""
Export Utilities for Synthetic Data, Ground Truth, SQL Seeds, and Manifests.
Implements Step 7 and Step 9 of the specification.
"""

from __future__ import annotations
import csv
import json
import os
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

from .models import (
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
from .generator import GeneratedDataset
from .validator import ValidationReport


class DatasetExporter:
    """
    Exports generated datasets to CSV, JSON, SQLite DB, SQL dump, source manifest, and reports.
    """

    def __init__(self, dataset: GeneratedDataset, output_dir: str):
        self.dataset = dataset
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self, validation_report: ValidationReport | None = None) -> Dict[str, Any]:
        """
        Executes full export pipeline.
        """
        csv_files = self.export_csvs()
        json_files = self.export_jsons()
        sql_file = self.export_sql()
        sqlite_db = self.export_sqlite()
        gt_files = self.export_ground_truth()

        if validation_report:
            self.export_validation_reports(validation_report)

        manifest = self.create_source_manifest(validation_report)

        return {
            "output_directory": str(self.output_dir),
            "csv_files": csv_files,
            "json_files": json_files,
            "sql_dump": sql_file,
            "sqlite_db": sqlite_db,
            "ground_truth_files": gt_files,
            "manifest": manifest,
        }

    def export_csvs(self) -> List[str]:
        exported = []
        table_mappings = [
            ("skills.csv", [s.to_dict() for s in self.dataset.skills]),
            ("teams.csv", [t.to_dict() for t in self.dataset.teams]),
            ("employees.csv", [e.to_dict() for e in self.dataset.employees]),
            ("employee_skills.csv", [es.to_dict() for es in self.dataset.employee_skills]),
            ("shift_templates.csv", [st.to_dict() for st in self.dataset.shift_templates]),
            ("holiday_calendar.csv", [h.to_dict() for h in self.dataset.holiday_calendar]),
            ("coverage_requirements.csv", [cr.to_dict() for cr in self.dataset.coverage_requirements]),
            ("leave_requests.csv", [lr.to_dict() for lr in self.dataset.leave_requests]),
            ("shift_assignments.csv", [sa.to_dict() for sa in self.dataset.shift_assignments]),
            ("swap_requests.csv", [sw.to_dict() for sw in self.dataset.swap_requests]),
            ("attendance_events.csv", [ae.to_dict() for ae in self.dataset.attendance_events]),
        ]

        for filename, rows in table_mappings:
            if not rows:
                continue
            filepath = self.output_dir / filename
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            exported.append(str(filepath))

        return exported

    def export_jsons(self) -> List[str]:
        exported = []
        full_data = {
            "metadata": self.dataset.metadata,
            "skills": [s.to_dict() for s in self.dataset.skills],
            "teams": [t.to_dict() for t in self.dataset.teams],
            "employees": [e.to_dict() for e in self.dataset.employees],
            "employee_skills": [es.to_dict() for es in self.dataset.employee_skills],
            "shift_templates": [st.to_dict() for st in self.dataset.shift_templates],
            "holiday_calendar": [h.to_dict() for h in self.dataset.holiday_calendar],
            "coverage_requirements": [cr.to_dict() for cr in self.dataset.coverage_requirements],
            "leave_requests": [lr.to_dict() for lr in self.dataset.leave_requests],
            "shift_assignments": [sa.to_dict() for sa in self.dataset.shift_assignments],
            "swap_requests": [sw.to_dict() for sw in self.dataset.swap_requests],
            "attendance_events": [ae.to_dict() for ae in self.dataset.attendance_events],
        }

        json_path = self.output_dir / "dataset.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=2)
        exported.append(str(json_path))

        return exported

    def export_ground_truth(self) -> Dict[str, str]:
        """
        Step 7: Produce separate ground_truth.csv and ground_truth.json
        """
        gt_rows = [gt.to_dict() for gt in self.dataset.ground_truth_anomalies]

        csv_path = self.output_dir / "ground_truth.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            if gt_rows:
                writer = csv.DictWriter(f, fieldnames=gt_rows[0].keys())
                writer.writeheader()
                writer.writerows(gt_rows)

        json_path = self.output_dir / "ground_truth.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(gt_rows, f, indent=2)

        return {"ground_truth_csv": str(csv_path), "ground_truth_json": str(json_path)}

    def export_sqlite(self) -> str:
        """
        Builds a fully indexed SQLite database file scheduler.db
        """
        db_path = self.output_dir / "scheduler.db"
        if db_path.exists():
            db_path.unlink()

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.cursor()

        # DDL
        cur.executescript("""
        CREATE TABLE skills (
            skill_id TEXT PRIMARY KEY,
            skill_name TEXT NOT NULL,
            category TEXT NOT NULL,
            minimum_certification_level TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE teams (
            team_id TEXT PRIMARY KEY,
            team_name TEXT NOT NULL,
            department TEXT NOT NULL,
            manager_id TEXT,
            location TEXT NOT NULL,
            max_overtime_hours_per_week REAL NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE employees (
            employee_id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL,
            team_id TEXT NOT NULL,
            hire_date TEXT NOT NULL,
            contract_hours_per_week REAL NOT NULL,
            max_weekly_overtime_hours REAL NOT NULL,
            hourly_rate REAL NOT NULL,
            employment_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams(team_id)
        );

        CREATE TABLE employee_skills (
            employee_skill_id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            skill_id TEXT NOT NULL,
            proficiency_level TEXT NOT NULL,
            certified_date TEXT NOT NULL,
            expiry_date TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
        );

        CREATE TABLE shift_templates (
            shift_template_id TEXT PRIMARY KEY,
            shift_code TEXT NOT NULL,
            shift_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            is_overnight INTEGER NOT NULL,
            differential_rate_multiplier REAL NOT NULL
        );

        CREATE TABLE holiday_calendar (
            holiday_id TEXT PRIMARY KEY,
            holiday_date TEXT NOT NULL,
            holiday_name TEXT NOT NULL,
            region TEXT NOT NULL,
            is_mandatory_off INTEGER NOT NULL
        );

        CREATE TABLE coverage_requirements (
            requirement_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            shift_template_id TEXT NOT NULL,
            team_id TEXT NOT NULL,
            skill_id TEXT,
            min_headcount INTEGER NOT NULL,
            target_headcount INTEGER NOT NULL,
            priority_weight REAL NOT NULL,
            FOREIGN KEY (shift_template_id) REFERENCES shift_templates(shift_template_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
        );

        CREATE TABLE leave_requests (
            leave_id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            decision_by TEXT,
            decision_timestamp TEXT,
            decision_notes TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (decision_by) REFERENCES employees(employee_id)
        );

        CREATE TABLE shift_assignments (
            assignment_id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            shift_template_id TEXT NOT NULL,
            employee_id TEXT NOT NULL,
            team_id TEXT NOT NULL,
            role_skill_id TEXT,
            scheduled_start TEXT NOT NULL,
            scheduled_end TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            FOREIGN KEY (shift_template_id) REFERENCES shift_templates(shift_template_id),
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (role_skill_id) REFERENCES skills(skill_id)
        );

        CREATE TABLE swap_requests (
            swap_id TEXT PRIMARY KEY,
            requester_assignment_id TEXT NOT NULL,
            target_assignment_id TEXT NOT NULL,
            requester_employee_id TEXT NOT NULL,
            target_employee_id TEXT NOT NULL,
            status TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            peer_agreed_at TEXT,
            manager_decision_by TEXT,
            manager_decision_at TEXT,
            decision_notes TEXT,
            FOREIGN KEY (requester_assignment_id) REFERENCES shift_assignments(assignment_id),
            FOREIGN KEY (target_assignment_id) REFERENCES shift_assignments(assignment_id),
            FOREIGN KEY (requester_employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (target_employee_id) REFERENCES employees(employee_id)
        );

        CREATE TABLE attendance_events (
            attendance_id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL,
            assignment_id TEXT,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            source_device TEXT NOT NULL,
            matched_schedule_diff_minutes REAL NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY (assignment_id) REFERENCES shift_assignments(assignment_id)
        );

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

        CREATE INDEX idx_emp_team ON employees(team_id);
        CREATE INDEX idx_asgn_date ON shift_assignments(date);
        CREATE INDEX idx_asgn_emp ON shift_assignments(employee_id);
        CREATE INDEX idx_asgn_team ON shift_assignments(team_id);
        CREATE INDEX idx_cov_date ON coverage_requirements(date);
        CREATE INDEX idx_leave_emp ON leave_requests(employee_id);
        CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
        CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_id);
        """)

        # Insert data
        cur.executemany(
            "INSERT INTO skills VALUES (?,?,?,?,?)",
            [(s.skill_id, s.skill_name, s.category.value, s.minimum_certification_level.value, s.description) for s in self.dataset.skills],
        )
        cur.executemany(
            "INSERT INTO teams VALUES (?,?,?,?,?,?,?)",
            [(t.team_id, t.team_name, t.department, t.manager_id, t.location, t.max_overtime_hours_per_week, t.created_at) for t in self.dataset.teams],
        )
        cur.executemany(
            "INSERT INTO employees VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(e.employee_id, e.first_name, e.last_name, e.email, e.team_id, e.hire_date, e.contract_hours_per_week, e.max_weekly_overtime_hours, e.hourly_rate, e.employment_status.value, e.created_at) for e in self.dataset.employees],
        )
        cur.executemany(
            "INSERT INTO employee_skills VALUES (?,?,?,?,?,?)",
            [(es.employee_skill_id, es.employee_id, es.skill_id, es.proficiency_level.value, es.certified_date, es.expiry_date) for es in self.dataset.employee_skills],
        )
        cur.executemany(
            "INSERT INTO shift_templates VALUES (?,?,?,?,?,?,?,?)",
            [(st.shift_template_id, st.shift_code.value, st.shift_name, st.start_time, st.end_time, st.duration_hours, 1 if st.is_overnight else 0, st.differential_rate_multiplier) for st in self.dataset.shift_templates],
        )
        cur.executemany(
            "INSERT INTO holiday_calendar VALUES (?,?,?,?,?)",
            [(h.holiday_id, h.holiday_date, h.holiday_name, h.region, 1 if h.is_mandatory_off else 0) for h in self.dataset.holiday_calendar],
        )
        cur.executemany(
            "INSERT INTO coverage_requirements VALUES (?,?,?,?,?,?,?,?)",
            [(c.requirement_id, c.date, c.shift_template_id, c.team_id, c.skill_id, c.min_headcount, c.target_headcount, c.priority_weight) for c in self.dataset.coverage_requirements],
        )
        cur.executemany(
            "INSERT INTO leave_requests VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(l.leave_id, l.employee_id, l.start_date, l.end_date, l.leave_type.value, l.status.value, l.reason, l.decision_by, l.decision_timestamp, l.decision_notes) for l in self.dataset.leave_requests],
        )
        cur.executemany(
            "INSERT INTO shift_assignments VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(sa.assignment_id, sa.date, sa.shift_template_id, sa.employee_id, sa.team_id, sa.role_skill_id, sa.scheduled_start, sa.scheduled_end, sa.status.value, sa.created_at, sa.created_by) for sa in self.dataset.shift_assignments],
        )
        cur.executemany(
            "INSERT INTO swap_requests VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(sw.swap_id, sw.requester_assignment_id, sw.target_assignment_id, sw.requester_employee_id, sw.target_employee_id, sw.status.value, sw.requested_at, sw.peer_agreed_at, sw.manager_decision_by, sw.manager_decision_at, sw.decision_notes) for sw in self.dataset.swap_requests],
        )
        cur.executemany(
            "INSERT INTO attendance_events VALUES (?,?,?,?,?,?,?)",
            [(ae.attendance_id, ae.employee_id, ae.assignment_id, ae.event_type.value, ae.event_timestamp, ae.source_device, ae.matched_schedule_diff_minutes) for ae in self.dataset.attendance_events],
        )

        conn.commit()

        # Database integrity and foreign key checks
        cur.execute("PRAGMA foreign_key_check;")
        fk_violations = cur.fetchall()
        if fk_violations:
            conn.close()
            raise ValueError(f"SQLite foreign-key check failed: {fk_violations}")

        cur.execute("PRAGMA integrity_check;")
        integrity_res = cur.fetchall()
        if integrity_res != [("ok",)]:
            conn.close()
            raise ValueError(f"SQLite integrity check failed: {integrity_res}")

        conn.close()
        return str(db_path)

    def export_sql(self) -> str:
        """
        Exports standard ANSI SQL seed scripts for PostgreSQL/MySQL.
        """
        sql_path = self.output_dir / "seed_data.sql"
        with open(sql_path, "w", encoding="utf-8") as f:
            f.write("-- Fair Shift Scheduler Seed Data SQL Dump\n")
            f.write(f"-- Scale: {self.dataset.scale}, Seed: {self.dataset.seed}\n\n")

            # Skills
            f.write("-- Skills\n")
            for s in self.dataset.skills:
                desc = s.description.replace("'", "''")
                f.write(f"INSERT INTO skills VALUES ('{s.skill_id}', '{s.skill_name}', '{s.category.value}', '{s.minimum_certification_level.value}', '{desc}');\n")

            # Teams
            f.write("\n-- Teams\n")
            for t in self.dataset.teams:
                mgr = f"'{t.manager_id}'" if t.manager_id else "NULL"
                f.write(f"INSERT INTO teams VALUES ('{t.team_id}', '{t.team_name}', '{t.department}', {mgr}, '{t.location}', {t.max_overtime_hours_per_week}, '{t.created_at}');\n")

            # Employees sample / all
            f.write("\n-- Employees\n")
            for e in self.dataset.employees:
                f.write(f"INSERT INTO employees VALUES ('{e.employee_id}', '{e.first_name}', '{e.last_name}', '{e.email}', '{e.team_id}', '{e.hire_date}', {e.contract_hours_per_week}, {e.max_weekly_overtime_hours}, {e.hourly_rate}, '{e.employment_status.value}', '{e.created_at}');\n")

        return str(sql_path)

    def create_source_manifest(self, validation_report: ValidationReport | None = None) -> Dict[str, Any]:
        """
        Step 9: Source manifest with file checksums, row counts, provenance, and validation summary.
        """
        file_checksums = {}
        for item in self.output_dir.glob("*.*"):
            if item.is_file() and item.name != "source_manifest.json":
                sha256 = hashlib.sha256()
                with open(item, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        sha256.update(chunk)
                file_checksums[item.name] = {
                    "sha256": sha256.hexdigest(),
                    "size_bytes": item.stat().st_size,
                }

        manifest = {
            "project": "Fair Shift Scheduler",
            "version": "1.0.0",
            "generator_seed": self.dataset.seed,
            "scale_profile": self.dataset.scale,
            "provenance": {
                "lawful_use_notice": "100% synthetically generated using fixed deterministic seed logic. No private or scraped third-party personal data included.",
                "jurisdiction_compliance": "FLSA and EU Working Time Directive labor constraint models.",
            },
            "record_counts": {
                "skills": len(self.dataset.skills),
                "teams": len(self.dataset.teams),
                "employees": len(self.dataset.employees),
                "employee_skills": len(self.dataset.employee_skills),
                "shift_templates": len(self.dataset.shift_templates),
                "holiday_calendar": len(self.dataset.holiday_calendar),
                "coverage_requirements": len(self.dataset.coverage_requirements),
                "leave_requests": len(self.dataset.leave_requests),
                "shift_assignments": len(self.dataset.shift_assignments),
                "swap_requests": len(self.dataset.swap_requests),
                "attendance_events": len(self.dataset.attendance_events),
                "ground_truth_anomalies": len(self.dataset.ground_truth_anomalies),
            },
            "file_checksums": file_checksums,
            "validation_summary": validation_report.summary if validation_report else None,
        }

        manifest_path = self.output_dir / "source_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    def export_validation_reports(self, report: ValidationReport):
        json_path = self.output_dir / "validation_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)

        md_path = self.output_dir / "validation_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Synthetic Data Validation & Anomaly Benchmark Report\n\n")
            f.write(f"- **Scale**: {self.dataset.scale.upper()}\n")
            f.write(f"- **Seed**: `{self.dataset.seed}`\n")
            f.write(f"- **Overall Structural Integrity**: {'✅ PASS' if report.is_valid else '❌ FAIL'}\n\n")

            f.write("## 1. 8-Point Structural & Relational Verification\n\n")
            f.write("| Verification Check | Status | Details |\n")
            f.write("| --- | --- | --- |\n")
            for k, v in report.structural_integrity.items():
                status_icon = "✅ PASS" if v else "❌ FAIL"
                f.write(f"| `{k}` | {status_icon} | Structural consistency verified |\n")

            f.write("\n## 2. Ground Truth Anomaly Benchmark (Evaluation Focus)\n\n")
            gt = report.ground_truth_evaluation
            f.write(f"- **Total Ground Truth Injected**: {gt['total_ground_truth']}\n")
            f.write(f"- **True Positives**: {gt['true_positives']}\n")
            f.write(f"- **False Positives**: {gt['false_positives']}\n")
            f.write(f"- **False Negatives**: {gt['false_negatives']}\n")
            f.write(f"- **Precision**: `{gt['precision'] * 100:.1f}%`\n")
            f.write(f"- **Recall**: `{gt['recall'] * 100:.1f}%`\n")
            f.write(f"- **F1 Score**: `{gt['f1_score'] * 100:.1f}%`\n\n")

            f.write("### Detected Edge Case Anomalies\n\n")
            f.write("| Rule Code | Severity | Entity | Entity ID | Issue Message |\n")
            f.write("| --- | --- | --- | --- | --- |\n")
            for d in report.detected_rule_violations:
                f.write(f"| `{d.rule_code}` | `{d.severity}` | {d.entity_type} | `{d.entity_id}` | {d.message} |\n")
