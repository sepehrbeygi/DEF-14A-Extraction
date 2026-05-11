#!/usr/bin/env python3
"""Create chunk and wave manifests for DEF 14A table extraction batches."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workflow:
    key: str
    label: str
    chunk_prompt: str
    agent_plan: str
    output_files: tuple[str, str]
    input_schemas: tuple[tuple[str, ...], ...]
    cik_columns: tuple[str, ...]
    company_columns: tuple[str, ...]


WORKFLOWS = {
    "outstanding-equity-awards": Workflow(
        key="outstanding-equity-awards",
        label="Outstanding Equity Awards",
        chunk_prompt="references/outstanding-equity-awards/Outstanding-Equity-Awards-Chunk-Thread-Prompt-V1.txt",
        agent_plan="references/outstanding-equity-awards/Outstanding-Equity-Awards-Agent-Plan-V1.md",
        output_files=(
            "[chunk_name]_outstanding_equity_awards.csv",
            "[chunk_name]_report.csv",
        ),
        input_schemas=(("cik", "target_fiscal_year", "source_filing_url"),),
        cik_columns=("cik", "CIK"),
        company_columns=("company_name", "Company Name", "Company"),
    ),
    "summary-compensation-table": Workflow(
        key="summary-compensation-table",
        label="Summary Compensation Table",
        chunk_prompt="references/summary-compensation-table/Summary-Compensation-Table-Chunk-Thread-Prompt-V3.txt",
        agent_plan="references/summary-compensation-table/Summary-Compensation-Table-Agent-Plan-V3.md",
        output_files=(
            "[chunk_name]_compensation_table_master.csv",
            "[chunk_name]_report.csv",
        ),
        input_schemas=(
            ("cik", "company_name", "target_fiscal_year", "source_filing_url"),
            ("CIK", "Company", "Year", "Filing URL", "accession_number", "filing_date"),
        ),
        cik_columns=("cik", "CIK"),
        company_columns=("company_name", "Company", "Company Name"),
    ),
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "def14a-batch"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        rows = list(reader)
        return list(reader.fieldnames), rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def validate_input_schema(workflow: Workflow, fieldnames: list[str]) -> None:
    available = set(fieldnames)
    if any(set(schema).issubset(available) for schema in workflow.input_schemas):
        return
    expected = [" + ".join(schema) for schema in workflow.input_schemas]
    raise ValueError(
        f"{workflow.label} input does not match a supported schema. "
        f"Found columns: {fieldnames}. Expected one of: {expected}"
    )


def first_present(row: dict[str, str], candidates: tuple[str, ...]) -> str:
    for column in candidates:
        if column in row and row[column] is not None:
            return row[column]
    return ""


def chunk_rows(rows: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def create_readme(batch_dir: Path, workflow: Workflow, chunk_size: int, wave_size: int) -> None:
    outputs = "\n".join(f"- `{name}`" for name in workflow.output_files)
    text = f"""# {batch_dir.name}

Workflow: {workflow.label}

Chunk size: {chunk_size} filing(s)
Wave size: {wave_size} chunk(s)

Each chunk should be processed with:
- `{workflow.chunk_prompt}`

The chunk prompt references this agent plan:
- `{workflow.agent_plan}`

Expected per-chunk outputs:
{outputs}

Use `chunk_manifest.csv` as the source of truth for chunk membership.
Use `wave_manifest.csv` and the files under `waves/` to run parallel chunk workers.
Merge only after every expected chunk output exists.
"""
    (batch_dir / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", required=True, choices=sorted(WORKFLOWS))
    parser.add_argument("--source-csv", required=True, type=Path)
    parser.add_argument("--output-root", type=Path, default=Path.cwd() / "batches")
    parser.add_argument("--batch-name")
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--wave-size", type=int, default=20)
    parser.add_argument("--force", action="store_true", help="allow writing into an existing empty batch directory")
    args = parser.parse_args()

    if args.chunk_size < 1:
        raise ValueError("--chunk-size must be positive")
    if args.wave_size < 1:
        raise ValueError("--wave-size must be positive")

    workflow = WORKFLOWS[args.workflow]
    source_csv = args.source_csv.expanduser().resolve()
    fieldnames, rows = read_csv(source_csv)
    validate_input_schema(workflow, fieldnames)

    batch_name = slugify(args.batch_name or source_csv.stem)
    batch_dir = (args.output_root.expanduser() / batch_name).resolve()
    chunks_dir = batch_dir / "chunks"
    merged_dir = batch_dir / "merged"
    waves_dir = batch_dir / "waves"

    if batch_dir.exists() and not args.force:
        raise FileExistsError(f"Batch directory already exists: {batch_dir}")
    if batch_dir.exists() and any(batch_dir.iterdir()) and args.force:
        raise FileExistsError(f"--force only allows an existing empty directory: {batch_dir}")

    chunks_dir.mkdir(parents=True, exist_ok=True)
    merged_dir.mkdir(parents=True, exist_ok=True)
    waves_dir.mkdir(parents=True, exist_ok=True)

    chunks = chunk_rows(rows, args.chunk_size)
    chunk_manifest_rows: list[dict[str, str]] = []

    width = max(2, len(str(len(chunks))))
    for index, chunk in enumerate(chunks, start=1):
        chunk_file = f"{batch_name}_chunk-{index:0{width}d}.csv"
        chunk_path = chunks_dir / chunk_file
        write_csv(chunk_path, fieldnames, chunk)

        first = chunk[0] if chunk else {}
        last = chunk[-1] if chunk else {}
        chunk_manifest_rows.append(
            {
                "Chunk Number": str(index),
                "Chunk File": chunk_file,
                "Chunk Path": str(chunk_path),
                "Filings In Chunk": str(len(chunk)),
                "First CIK": first_present(first, workflow.cik_columns),
                "First Company": first_present(first, workflow.company_columns),
                "Last CIK": first_present(last, workflow.cik_columns),
                "Last Company": first_present(last, workflow.company_columns),
            }
        )

    manifest_fields = [
        "Chunk Number",
        "Chunk File",
        "Chunk Path",
        "Filings In Chunk",
        "First CIK",
        "First Company",
        "Last CIK",
        "Last Company",
    ]
    write_csv(batch_dir / "chunk_manifest.csv", manifest_fields, chunk_manifest_rows)

    wave_manifest_rows: list[dict[str, str]] = []
    wave_chunks = chunk_rows(chunk_manifest_rows, args.wave_size)
    wave_width = max(2, len(str(len(wave_chunks))))
    for wave_index, wave in enumerate(wave_chunks, start=1):
        wave_file = f"{batch_name}_wave-{wave_index:0{wave_width}d}.csv"
        wave_path = waves_dir / wave_file
        wave_rows = []
        for position, row in enumerate(wave, start=1):
            wave_rows.append(
                {
                    "Wave Number": str(wave_index),
                    "Wave File": wave_file,
                    "Position In Wave": str(position),
                    **row,
                }
            )
        wave_fields = ["Wave Number", "Wave File", "Position In Wave", *manifest_fields]
        write_csv(wave_path, wave_fields, wave_rows)
        wave_manifest_rows.append(
            {
                "Wave Number": str(wave_index),
                "Wave File": wave_file,
                "Chunks In Wave": str(len(wave)),
                "Total Filings In Wave": str(sum(int(row["Filings In Chunk"]) for row in wave)),
                "Wave Path": str(wave_path),
            }
        )

    write_csv(
        batch_dir / "wave_manifest.csv",
        ["Wave Number", "Wave File", "Chunks In Wave", "Total Filings In Wave", "Wave Path"],
        wave_manifest_rows,
    )
    create_readme(batch_dir, workflow, args.chunk_size, args.wave_size)

    # Parse the generated CSVs once more before reporting success.
    read_csv(batch_dir / "chunk_manifest.csv")
    for row in chunk_manifest_rows:
        read_csv(Path(row["Chunk Path"]))

    print(f"Workflow: {workflow.label}")
    print(f"Total filings: {len(rows)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Waves created: {len(wave_manifest_rows)}")
    print(f"Output folder: {batch_dir}")
    print(f"Chunk manifest: {batch_dir / 'chunk_manifest.csv'}")
    print(f"Wave manifest: {batch_dir / 'wave_manifest.csv'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
