#!/usr/bin/env python3
"""Merge completed DEF 14A extraction chunks for a selected workflow."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


OUTSTANDING_EQUITY_COLUMNS = [
    "CIK",
    "Company Name",
    "Filing URL",
    "Name",
    "Role",
    "Grant Date",
    "Option Award (Number of Securities Underlying Unexercised Options Exercisable (#))",
    "Option Award (Number of Securities Underlying Unexercised Options Unexercisable (#))",
    "Option Award (Equity Incentive Plan Awards: Number of Securities Underlying Unexercised Unearned Options (#))",
    "Option Exercise Price ($)",
    "Option Expiration Date",
    "Stock Awards (Number of Shares or Units of Stock that Have Not Vested (#))",
    "Stock Awards (Market Value of Shares or Units of Stock that Have Not Vested ($))",
    "Stock Awards (Equity Incentive Plan Awards: Number of Unearned Shares, Units, or Other Rights that Have Not Vested (#))",
    "Stock Awards (Equity Incentive Plan Awards: Market or Payout Value of Unearned Shares, Units, or Other Rights that Have Not Vested ($))",
]

SUMMARY_COMP_COLUMNS = [
    "CIK",
    "Company Name",
    "Filing URL",
    "ticker",
    "Name",
    "Title",
    "Year",
    "Salary ($)",
    "Bonus Awards ($)",
    "Stock Awards ($)",
    "Option Awards ($)",
    "Non-Equity Incentive Plan Compensation ($)",
    "Change in pension value and nonqualified deferred compensation earnings ($)",
    "All Other Compensation ($)",
    "Total ($)",
    "Extra information",
    "Is QA done?",
]

REPORT_COLUMNS = [
    "cik",
    "company_name",
    "run_scope",
    "target_fiscal_year",
    "source_filing_date",
    "source_accession_number",
    "source_filing_url",
    "status",
    "extraction_method",
    "block_count",
    "table_count",
    "comp_heading_found",
    "comp_table_found",
    "grant_table_found",
    "det_rows",
    "llm_confidence",
    "cda_token_count",
    "pay_for_performance_flag",
    "elapsed_seconds",
    "error",
]

OUTSTANDING_EQUITY_REPORT_COLUMNS = [
    "cik",
    "company_name",
    "run_scope",
    "target_fiscal_year",
    "source_filing_date",
    "source_accession_number",
    "source_filing_url",
    "status",
    "extraction_method",
    "block_count",
    "table_count",
    "equity_heading_found",
    "equity_table_found",
    "rows_extracted",
    "llm_confidence",
    "investigation_required",
    "elapsed_seconds",
    "error",
]


@dataclass(frozen=True)
class Workflow:
    master_suffix: str
    report_suffix: str
    merged_master_suffix: str
    merged_report_suffix: str
    master_columns: list[str]
    report_columns: list[str]


WORKFLOWS = {
    "outstanding-equity-awards": Workflow(
        master_suffix="_outstanding_equity_awards.csv",
        report_suffix="_report.csv",
        merged_master_suffix="-merged_outstanding_equity_awards.csv",
        merged_report_suffix="-merged_report.csv",
        master_columns=OUTSTANDING_EQUITY_COLUMNS,
        report_columns=OUTSTANDING_EQUITY_REPORT_COLUMNS,
    ),
    "summary-compensation-table": Workflow(
        master_suffix="_compensation_table_master.csv",
        report_suffix="_report.csv",
        merged_master_suffix="-merged_master.csv",
        merged_report_suffix="-merged_report.csv",
        master_columns=SUMMARY_COMP_COLUMNS,
        report_columns=REPORT_COLUMNS,
    ),
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def chunk_base_from_manifest_row(batch_dir: Path, row: dict[str, str]) -> tuple[str, Path]:
    chunk_path_text = row.get("Chunk Path", "").strip()
    chunk_file = row.get("Chunk File", "").strip()
    if chunk_path_text:
        chunk_path = Path(chunk_path_text)
    elif chunk_file:
        chunk_path = batch_dir / "chunks" / chunk_file
    else:
        raise ValueError("Manifest row lacks Chunk Path and Chunk File")
    return chunk_path.stem, chunk_path.parent


def validate_schema(path: Path, actual: list[str], expected: list[str]) -> None:
    if actual != expected:
        raise ValueError(
            f"Schema mismatch in {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, choices=sorted(WORKFLOWS))
    parser.add_argument("--batch-dir", required=True, type=Path)
    parser.add_argument("--batch-name")
    args = parser.parse_args()

    workflow = WORKFLOWS[args.workflow]
    batch_dir = args.batch_dir.expanduser().resolve()
    manifest_path = batch_dir / "chunk_manifest.csv"
    merged_dir = batch_dir / "merged"
    merged_dir.mkdir(exist_ok=True)

    manifest_fields, manifest_rows = read_csv(manifest_path)
    if "Chunk File" not in manifest_fields and "Chunk Path" not in manifest_fields:
        raise ValueError(f"Manifest must include Chunk File or Chunk Path: {manifest_path}")

    missing: list[str] = []
    master_rows: list[dict[str, str]] = []
    report_rows: list[dict[str, str]] = []
    master_count_by_file: dict[str, int] = {}
    report_count_by_file: dict[str, int] = {}

    for row in manifest_rows:
        base, outdir = chunk_base_from_manifest_row(batch_dir, row)
        master_path = outdir / f"{base}{workflow.master_suffix}"
        report_path = outdir / f"{base}{workflow.report_suffix}"
        if not master_path.is_file():
            missing.append(str(master_path))
        if not report_path.is_file():
            missing.append(str(report_path))
        if missing:
            continue

        master_fields, current_master_rows = read_csv(master_path)
        report_fields, current_report_rows = read_csv(report_path)
        validate_schema(master_path, master_fields, workflow.master_columns)
        validate_schema(report_path, report_fields, workflow.report_columns)
        master_rows.extend(current_master_rows)
        report_rows.extend(current_report_rows)
        master_count_by_file[str(master_path)] = len(current_master_rows)
        report_count_by_file[str(report_path)] = len(current_report_rows)

    if missing:
        print("Missing expected chunk outputs:", file=sys.stderr)
        for path in missing:
            print(f"- {path}", file=sys.stderr)
        return 1

    batch_name = args.batch_name or batch_dir.name
    merged_master = merged_dir / f"{batch_name}{workflow.merged_master_suffix}"
    merged_report = merged_dir / f"{batch_name}{workflow.merged_report_suffix}"
    write_csv(merged_master, workflow.master_columns, master_rows)
    write_csv(merged_report, workflow.report_columns, report_rows)

    merged_master_fields, merged_master_rows = read_csv(merged_master)
    merged_report_fields, merged_report_rows = read_csv(merged_report)
    validate_schema(merged_master, merged_master_fields, workflow.master_columns)
    validate_schema(merged_report, merged_report_fields, workflow.report_columns)

    expected_master_rows = sum(master_count_by_file.values())
    expected_report_rows = sum(report_count_by_file.values())
    if len(merged_master_rows) != expected_master_rows:
        raise ValueError("Merged master row count does not match chunk row count sum")
    if len(merged_report_rows) != expected_report_rows:
        raise ValueError("Merged report row count does not match chunk row count sum")

    if args.workflow == "summary-compensation-table":
        if merged_master_fields[-1] != "Is QA done?":
            raise ValueError("Merged Summary Compensation output does not end with Is QA done?")

    print(f"Chunk master files merged: {len(master_count_by_file)}")
    print(f"Chunk report files merged: {len(report_count_by_file)}")
    print(f"Merged master row count: {len(merged_master_rows)}")
    print(f"Merged report row count: {len(merged_report_rows)}")
    print("Master schema mismatches: 0")
    print("Report schema mismatches: 0")
    print("Missing files: 0")
    print(f"Merged master: {merged_master}")
    print(f"Merged report: {merged_report}")
    print("Merge completed cleanly.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
