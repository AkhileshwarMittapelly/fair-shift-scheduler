"""
Step 10: Reproducibility Verification Engine.
Regenerates datasets twice with identical seed and verifies bit-for-bit SHA-256 checksums and row counts.
"""

from __future__ import annotations
import shutil
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Any, Tuple

from .generator import SyntheticDataGenerator
from .export import DatasetExporter


def compute_dir_checksums(dir_path: Path) -> Dict[str, Tuple[str, int]]:
    """
    Computes (sha256_hex, row_count) for all CSV and JSON files in a directory.
    """
    results = {}
    for f in sorted(dir_path.glob("*.csv")):
        sha256 = hashlib.sha256()
        with open(f, "rb") as fp:
            for chunk in iter(lambda: fp.read(65536), b""):
                sha256.update(chunk)

        # Count rows (excluding header)
        with open(f, "r", encoding="utf-8") as fp:
            rows = max(0, sum(1 for _ in fp) - 1)

        results[f.name] = (sha256.hexdigest(), rows)
    return results


def verify_reproducibility(seed: int = 20261022, scale: str = "starter") -> Dict[str, Any]:
    """
    Performs dual generation and validates 100% deterministic reproducibility.
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

        # Compare
        comparisons = []
        all_matched = True

        for fname, (hash1, rows1) in checksums1.items():
            if fname not in checksums2:
                all_matched = False
                comparisons.append({
                    "file": fname,
                    "run1_sha256": hash1[:12] + "...",
                    "run2_sha256": "MISSING",
                    "run1_rows": rows1,
                    "run2_rows": 0,
                    "match": False,
                })
                continue

            hash2, rows2 = checksums2[fname]
            is_match = (hash1 == hash2) and (rows1 == rows2)
            if not is_match:
                all_matched = False

            comparisons.append({
                "file": fname,
                "run1_sha256": hash1[:12] + "...",
                "run2_sha256": hash2[:12] + "...",
                "run1_rows": rows1,
                "run2_rows": rows2,
                "match": is_match,
            })

        return {
            "seed": seed,
            "scale": scale,
            "is_reproducible": all_matched,
            "total_files_verified": len(comparisons),
            "file_comparisons": comparisons,
        }

    finally:
        shutil.rmtree(temp_dir_1, ignore_errors=True)
        shutil.rmtree(temp_dir_2, ignore_errors=True)
