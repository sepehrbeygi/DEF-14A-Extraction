# DEF 14A Extraction Skill Design Notes

This file captures the planning decisions behind the `def14a-table-extraction` skill. It is written as public-friendly build notes rather than a raw private transcript.

## Initial Goal

Create a reusable Codex skill for extracting tables from DEF 14A proxy filings using the user's existing chunked extraction workflow.

The high-level process supplied by the user was:

1. Start from a CSV containing CIK and filing URL.
2. Split filings into chunks, with a default of 10 filings per chunk.
3. Create a prompt for extracting each chunk.
4. Create a bash runner to run multiple Codex workers at once, with 20 parallel workers, `gpt-5.4`, and medium reasoning.
5. Create a merge prompt.
6. Create the final merged file from the merge prompt and extracted chunks.

## Skill Design Decision

The skill should be a reusable DEF 14A table extraction skill, not a one-off Outstanding Equity Awards script.

Skill name:

```text
def14a-table-extraction
```

Supported initial workflows:

```text
outstanding-equity-awards
summary-compensation-table
```

## File Naming Decisions

The original source files used names like `QA_AGENT_PLAN`. The user requested the final bundled files drop `QA` and use clearer names.

Final naming pattern:

```text
references/
├── outstanding-equity-awards/
│   ├── Outstanding-Equity-Awards-Agent-Plan-V1.md
│   ├── Outstanding-Equity-Awards-Chunk-Thread-Prompt-V1.txt
│   ├── Outstanding-Equity-Awards-Chunking-Batch-Prompt-V1.txt
│   └── Outstanding-Equity-Awards-Merge-Prompt-V1.txt
└── summary-compensation-table/
    ├── Summary-Compensation-Table-Agent-Plan-V3.md
    ├── Summary-Compensation-Table-Chunk-Thread-Prompt-V3.txt
    ├── Summary-Compensation-Table-Chunking-Batch-Prompt-V2.txt
    └── Summary-Compensation-Table-Merge-Prompt-V2.txt
```

The user also requested the Summary Compensation files include the `Summary-Compensation-Table` prefix so they are easy to find by search.

## Agent Plan Placement

The actual extraction plans are first-class reference files under each workflow folder. They are not hidden in `SKILL.md`.

For Outstanding Equity Awards, the original plan was copied/adapted into:

```text
references/outstanding-equity-awards/Outstanding-Equity-Awards-Agent-Plan-V1.md
```

For Summary Compensation Table, the original V3 plan was copied/adapted into:

```text
references/summary-compensation-table/Summary-Compensation-Table-Agent-Plan-V3.md
```

The chunk-thread prompts were updated so they reference these bundled agent plans instead of local absolute paths.

## Workflow-Specific Behavior

Outstanding Equity Awards:

- Uses local filing lookup first.
- Checks `[PROJECT_ROOT]/data/raw` before downloading.
- Expected chunk outputs:
  - `[chunk_name]_outstanding_equity_awards.csv`
  - `[chunk_name]_report.csv`

Summary Compensation Table:

- Uses URL-only filing retrieval.
- Does not check local raw filing folders.
- Supports both failure-report-style and coverage-style input schemas.
- Expected chunk outputs:
  - `[chunk_name]_compensation_table_master.csv`
  - `[chunk_name]_report.csv`

## Sample CSV Decision

The user requested sample input and output CSVs for both workflows so future users and future agents can understand expected shapes.

The final skill includes samples under:

```text
references/outstanding-equity-awards/samples/
references/summary-compensation-table/samples/
```

Outstanding Equity Awards samples:

```text
Outstanding-Equity-Awards-Sample-Input.csv
Outstanding-Equity-Awards-Sample-Chunk-Output.csv
Outstanding-Equity-Awards-Sample-Report.csv
```

Summary Compensation Table samples:

```text
Summary-Compensation-Table-Sample-Input-Failure-Report-Style.csv
Summary-Compensation-Table-Sample-Input-Coverage-Style.csv
Summary-Compensation-Table-Sample-Chunk-Output.csv
Summary-Compensation-Table-Sample-Report.csv
```

## Scripts Added

The skill includes three reusable scripts:

```text
scripts/create_def14a_batch.py
scripts/run_def14a_chunk_waves.sh
scripts/merge_def14a_chunks.py
```

`create_def14a_batch.py`:

- Splits a source filing-list CSV into chunk CSVs.
- Defaults to 10 filings per chunk.
- Creates `chunk_manifest.csv`.
- Creates `wave_manifest.csv`.
- Creates wave files with up to 20 chunks per wave.
- Creates a batch `README.md`.

`run_def14a_chunk_waves.sh`:

- Runs Codex workers in parallel.
- Defaults to:
  - `PARALLELISM=20`
  - `MODEL=gpt-5.4`
  - `REASONING_EFFORT=medium`
- Uses the selected workflow's chunk-thread prompt.
- Skips chunks that already have expected outputs.
- Writes run logs.

`merge_def14a_chunks.py`:

- Reads `chunk_manifest.csv`.
- Verifies every chunk has expected output files.
- Validates schema consistency.
- Concatenates outputs in chunk order.
- Writes merged master output and merged report.
- Does not deduplicate, change reviewed values, or re-run extraction.

## Validation Performed

Validation completed during skill creation:

- Codex skill validator passed.
- Python scripts compiled successfully with a local pycache.
- All sample CSVs parsed successfully.
- Batch creation smoke-tested for both workflows.
- Merge smoke-tested for both workflows using the sample outputs.
- Shell syntax check passed for the runner script.

One useful issue found during smoke testing:

- Two Outstanding Equity Awards sample headers contained commas and needed CSV quoting. The sample was fixed and the merge smoke test then passed.

## Installed Skill Location In The Original Environment

The skill was installed for local Codex discovery at:

```text
~/.codex/skills/def14a-table-extraction
```

An editable staged copy also existed in the original workspace at:

```text
def14a-table-extraction/
```

## Public Repo Notes

Before publishing publicly, review whether any table plans contain project-specific local path assumptions, proprietary workflow language, or non-public examples. During skill creation, known hard-coded absolute paths were replaced with placeholders such as:

```text
[PROJECT_ROOT]
[OUTPUT_ROOT]
[BATCH_FOLDER]
[BATCH_NAME]
```
