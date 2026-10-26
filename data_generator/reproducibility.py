"""
Step 10: Reproducibility Verification Engine.
Regenerates datasets twice with identical seed and verifies bit-for-bit SHA-256 checksums and row counts.
Checks: *.csv, *.json (excluding source_manifest.json), *.sql, *.md files.
"""

from __future__ import annotations
import shutil
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple

from .generator import SyntheticDataGenerator
from .export import DatasetExporter


# source_manifest.json embeds per-file checksums and generation timestamps,
# so it is intentionally excluded from the cross-run hash comparison.
EXCLUDE_FROM_HASH = {"source_manifest.json"}

# File patterns to include in the reproducibility check
SCAN_PATTERNS = ["*.csv", "*.json", "*.sql", "*.md"]


def compute_dir_checksums(dir_path: Path) -> Dict[str, Tuple[str, int]]:
    """
    Computes (sha256_hex, row_count) for all target files in a directory.
    row_count is the number of lines excluding the header for CSV files,
    or the total line count for other file types.
    """
    results: Dict[str, Tuple[str, int]] = {}
    seen_names: set = set()

    for pattern in SCAN_PATTERNS:
        for f in sorted(dir_path.glob(pattern)):
            if f.name in EXCLUDE_FROM_HASH or f.name in seen_names:
                continue
            seen_names.add(f.name)

            sha256 = hashlib.sha256()
            with open(f, "rb") as fp:
                for chunk in iter(lambda: fp.read(65536), b""):
                    sha256.update(chunk)

            # Count lines; for CSV subtract 1 for the header row
            with open(f, "r", encoding="utf-8", errors="replace") as fp:
                total_lines = sum(1 for _ in fp)
            row_count = max(0, total_lines - 1) if f.suffix == ".csv" else total_lines

            results[f.name] = (sha256.hexdigest(), row_count)

    return results


def verify_reproducibility(seed: int = 20261022, scale: str = "starter") -> Dict[str, Any]:
    """
    Performs dual generation and validates 100% deterministic reproducibility.
    Fails if any tracked file is missing in either run or has a hash/count mismatch.
    """
    temp_dir_1 = Path(tempfile.mkdtemp(prefix="repro_run1_"))
    temp_dir_2 = Path(tempfile.mkdtemp(prefix="repro_run2_"))

    try:
        # Run 1
        gen1 = SyntheticDataGenerator(seed=seed, scale=scale)
        data1 = gen1.generate()
        exp1 = DatasetExporter(data1, str(temp_dir_1))
        exp1.export_all()
        checksums1 = compute_dir_checksums(temp_dir_1)

        # Run 2
        gen2 = SyntheticDataGenerator(seed=seed, scale=scale)
        data2 = gen2.generate()
        exp2 = DatasetExporter(data2, str(temp_dir_2))
        exp2.export_all()
        checksums2 = compute_dir_checksums(temp_dir_2)

        # Union of all file names from both runs — catch files missing in either direction
        all_fnames = sorted(set(checksums1.keys()) | set(checksums2.keys()))

        comparisons = []
        all_matched = True

        for fname in all_fnames:
            in_run1 = fname in checksums1
            in_run2 = fname in checksums2

            if not in_run1 or not in_run2:
                all_matched = False
                comparisons.append({
                    "file": fname,
                    "run1_sha256": (checksums1[fname][0][:12] + "...") if in_run1 else "MISSING",
                    "run2_sha256": (checksums2[fname][0][:12] + "...") if in_run2 else "MISSING",
                    "run1_rows": checksums1[fname][1] if in_run1 else 0,
                    "run2_rows": checksums2[fname][1] if in_run2 else 0,
                    "match": False,
                    "mismatch_reason": f"File only present in {'run1' if in_run1 else 'run2'}",
                })
                continue

            hash1, rows1 = checksums1[fname]
            hash2, rows2 = checksums2[fname]
            hash_match = hash1 == hash2
            rows_match = rows1 == rows2
            is_match = hash_match and rows_match

            if not is_match:
                all_matched = False

            reasons = []
            if not hash_match:
                reasons.append("sha256_mismatch")
            if not rows_match:
                reasons.append(f"row_count_mismatch({rows1}!={rows2})")

            comparisons.append({
                "file": fname,
                "run1_sha256": hash1[:12] + "...",
                "run2_sha256": hash2[:12] + "...",
                "run1_rows": rows1,
                "run2_rows": rows2,
                "match": is_match,
                "mismatch_reason": "; ".join(reasons) if reasons else None,
            })

        return {
            "seed": seed,
            "scale": scale,
            "is_reproducible": all_matched,
            "total_files_verified": len(comparisons),
            "excluded_files": list(EXCLUDE_FROM_HASH),
            "file_comparisons": comparisons,
        }

    finally:
        shutil.rmtree(temp_dir_1, ignore_errors=True)
        shutil.rmtree(temp_dir_2, ignore_errors=True)
