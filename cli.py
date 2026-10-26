"""
Command Line Interface for Fair Shift Scheduler.
Provides commands for:
  - generate: Generate synthetic datasets (starter or full)
  - validate: Run 8-point validator and anomaly detection against ground truth
  - verify-reproducibility: Run dual generation and check SHA-256 reproducibility
  - solve: Run the constraint and fairness scheduling optimizer
"""

from __future__ import annotations
import argparse
import sys
import io
import json
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from data_generator.generator import SyntheticDataGenerator
from data_generator.validator import DatasetValidator
from data_generator.export import DatasetExporter
from data_generator.scheduler import FairShiftScheduler
from data_generator.reproducibility import verify_reproducibility

console = Console(safe_box=True)


def handle_generate(args):
    console.print(f"[bold cyan][*] Starting Synthetic Data Generation[/bold cyan]")
    console.print(f"Scale: [green]{args.scale}[/green] | Seed: [yellow]{args.seed}[/yellow] | Output: [magenta]{args.out}[/magenta]\n")

    gen = SyntheticDataGenerator(seed=args.seed, scale=args.scale)
    dataset = gen.generate()

    console.print(f"[+] Generated [bold]{len(dataset.employees)}[/bold] employees across [bold]{len(dataset.teams)}[/bold] teams.")
    console.print(f"[+] Generated [bold]{len(dataset.shift_assignments)}[/bold] shifts over [bold]{dataset.metadata['num_days']}[/bold] days.")
    console.print(f"[+] Generated [bold]{len(dataset.leave_requests)}[/bold] leave requests & [bold]{len(dataset.attendance_events)}[/bold] attendance events.")
    console.print(f"[!] Injected [bold red]{len(dataset.ground_truth_anomalies)}[/bold red] labelled edge case anomalies into ground truth.")

    # Validate
    validator = DatasetValidator(dataset)
    report = validator.validate()

    # Export
    exporter = DatasetExporter(dataset, args.out)
    exported = exporter.export_all(report)

    console.print(f"\n[bold green][+] Successfully exported all datasets to: {args.out}[/bold green]")
    console.print(f"  - CSV files: {len(exported['csv_files'])} tables")
    console.print(f"  - SQLite DB: {exported['sqlite_db']}")
    console.print(f"  - Ground Truth: {exported['ground_truth_files']['ground_truth_csv']}")
    console.print(f"  - Manifest: {list(exported['manifest']['file_checksums'].keys())}")

    # Display ground truth evaluation table
    table = Table(title="Ground Truth Anomaly Detection & Benchmark")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    gt = report.ground_truth_evaluation
    table.add_row("Total Injected Anomalies", str(gt["total_ground_truth"]))
    table.add_row("True Positives (Detected)", str(gt["true_positives"]))
    table.add_row("False Positives", str(gt["false_positives"]))
    table.add_row("False Negatives", str(gt["false_negatives"]))
    table.add_row("Detection Precision", f"{gt['precision'] * 100:.1f}%")
    table.add_row("Detection Recall", f"{gt['recall'] * 100:.1f}%")
    table.add_row("Detection F1 Score", f"{gt['f1_score'] * 100:.1f}%")
    console.print(table)


def handle_verify_reproducibility(args):
    console.print(f"[bold cyan][*] Verifying Step 10: Dual Generation Reproducibility[/bold cyan]")
    console.print(f"Seed: [yellow]{args.seed}[/yellow] | Scale: [green]{args.scale}[/green]\n")

    res = verify_reproducibility(seed=args.seed, scale=args.scale)

    table = Table(title="Step 10: Checksum & Row Count Comparison")
    table.add_column("Table / File", style="cyan")
    table.add_column("Run 1 SHA-256", style="yellow")
    table.add_column("Run 2 SHA-256", style="yellow")
    table.add_column("Run 1 Rows", justify="right")
    table.add_column("Run 2 Rows", justify="right")
    table.add_column("Match?", justify="center")

    for f in res["file_comparisons"]:
        match_str = "[bold green]MATCH [OK][/bold green]" if f["match"] else "[bold red]MISMATCH [FAIL][/bold red]"
        table.add_row(
            f["file"],
            f["run1_sha256"],
            f["run2_sha256"],
            str(f["run1_rows"]),
            str(f["run2_rows"]),
            match_str,
        )

    console.print(table)
    if res["is_reproducible"]:
        console.print(Panel("[bold green][OK] 100% Deterministic Reproducibility Confirmed! Bit-for-bit identical checksums.[/bold green]"))
    else:
        console.print(Panel("[bold red][FAIL] Reproducibility check failed![/bold red]"))
        sys.exit(1)


def handle_solve(args):
    console.print(f"[bold cyan][*] Running Fair Shift Optimization Solver[/bold cyan]")
    gen = SyntheticDataGenerator(seed=args.seed, scale=args.scale)
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
        start_date=dataset.metadata.get("start_date", "2026-01-01"),
        num_days=dataset.metadata.get("num_days", 14),
    )

    m = result.metrics
    table = Table(title="Fair Scheduling Optimization Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Coverage Fulfillment Rate", f"{m.coverage_fulfillment_rate_pct:.1f}%")
    table.add_row("Total Scheduled Shifts", str(m.total_scheduled_shifts))
    table.add_row("Total Scheduled Hours", f"{m.total_scheduled_hours:.1f}h")
    table.add_row("Total Overtime Hours", f"{m.total_overtime_hours:.1f}h")
    table.add_row("Fairness (Gini Coefficient)", f"{m.fairness_gini_coefficient:.4f}")
    table.add_row("Night Shift Equity Score", f"{m.night_shift_equity_score:.1f}/100")
    table.add_row("Weekend Shift Equity Score", f"{m.weekend_shift_equity_score:.1f}/100")
    table.add_row("Hard Constraint Violations", str(m.hard_constraint_violations))
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="Fair Shift Scheduler CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic data")
    gen_parser.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset scale")
    gen_parser.add_argument("--seed", type=int, default=20261022, help="Deterministic integer seed")
    gen_parser.add_argument("--out", default="data/starter", help="Output directory")

    # Verify Reproducibility
    repro_parser = subparsers.add_parser("verify-reproducibility", help="Verify bit-for-bit reproducibility")
    repro_parser.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset scale")
    repro_parser.add_argument("--seed", type=int, default=20261022, help="Deterministic integer seed")

    # Solve
    solve_parser = subparsers.add_parser("solve", help="Run constraint and fairness scheduling optimizer")
    solve_parser.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset scale")
    solve_parser.add_argument("--seed", type=int, default=20261022, help="Deterministic integer seed")

    args = parser.parse_args()

    if args.command == "generate":
        handle_generate(args)
    elif args.command == "verify-reproducibility":
        handle_verify_reproducibility(args)
    elif args.command == "solve":
        handle_solve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
