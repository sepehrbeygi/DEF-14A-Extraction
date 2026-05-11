# DEF 14A Extraction

Reusable Codex skill and helper scripts for chunked extraction of compensation tables from DEF 14A proxy filings.

This repository currently supports two workflows:

- Outstanding Equity Awards at Fiscal Year-End
- Summary Compensation Table

The workflow is designed for large filing lists: split input filings into chunk CSVs, run Codex workers over chunks in parallel waves, then merge completed chunk outputs after schema validation.

## Repository Layout

```text
def14a-table-extraction/
+-- SKILL.md
+-- agents/
+-- references/
|   +-- outstanding-equity-awards/
|   +-- summary-compensation-table/
+-- scripts/
    +-- create_def14a_batch.py
    +-- run_def14a_chunk_waves.sh
    +-- merge_def14a_chunks.py
```

## Quick Start

Create a batch from a filing-list CSV:

```bash
python def14a-table-extraction/scripts/create_def14a_batch.py \
  --workflow outstanding-equity-awards \
  --source-csv /path/to/filings.csv \
  --batch-name outstanding-equity-awards-v1
```

Run chunk workers in waves:

```bash
BATCH_DIR=/path/to/batches/outstanding-equity-awards-v1 \
WORKFLOW=outstanding-equity-awards \
def14a-table-extraction/scripts/run_def14a_chunk_waves.sh
```

Merge completed chunk outputs:

```bash
python def14a-table-extraction/scripts/merge_def14a_chunks.py \
  --workflow outstanding-equity-awards \
  --batch-dir /path/to/batches/outstanding-equity-awards-v1
```

Use `summary-compensation-table` as the workflow key for Summary Compensation Table extraction.

## Notes

- The filing is the source of truth for extracted values.
- Worker agents should follow the selected workflow's bundled agent plan.
- Merge scripts validate expected schemas and require every expected chunk output to exist before merging.
- Generated batches, logs, caches, and virtual environments are intentionally ignored by git.
