---
name: def14a-table-extraction
description: Prepare, run, and merge chunked DEF 14A table extraction workflows for compensation and ownership data. Use when Codex needs to split filing-list CSVs into chunks, launch parallel Codex workers, or merge outputs for Outstanding Equity Awards, Summary Compensation Table, or Beneficial Ownership extraction from DEF 14A/proxy filings.
---

# DEF 14A Table Extraction

## Overview

Use this skill to run repeatable, chunked extraction workflows for DEF 14A compensation tables. It currently supports:

- Outstanding Equity Awards at Fiscal Year-End
- Summary Compensation Table
- Beneficial Ownership / Security Ownership

The filing is the source of truth. The bundled agent plans are intentionally detailed and should be treated as the extraction authority for worker runs.

## Workflow Selection

Use `outstanding-equity-awards` when extracting the `Outstanding Equity Awards at Fiscal Year-End` table into the outstanding equity awards schema.

Use `summary-compensation-table` when extracting `Summary Compensation Table` rows into the compensation master schema. This workflow supports both failure-report-style and coverage-style filing-list CSVs.

Use `beneficial-ownership` when extracting beneficial ownership, security ownership, principal stockholder/shareholder, stock ownership, or ownership-of-common-stock tables into the beneficial ownership schema. This workflow is local-first and relies heavily on row footnote capture and footnote component mapping.

Before creating a new batch, inspect the relevant sample CSVs to confirm the expected input, chunk output, and report shape.

## Core Workflow

1. Create a batch from a filing-list CSV:

```bash
python def14a-table-extraction/scripts/create_def14a_batch.py \
  --workflow outstanding-equity-awards \
  --source-csv /path/to/filings.csv \
  --batch-name outstanding-equity-awards-v1
```

2. Run chunk workers in waves:

```bash
BATCH_DIR=/path/to/batches/outstanding-equity-awards-v1 \
WORKFLOW=outstanding-equity-awards \
def14a-table-extraction/scripts/run_def14a_chunk_waves.sh
```

Defaults are `PARALLELISM=20`, `MODEL=gpt-5.4`, and `REASONING_EFFORT=medium`.

3. Merge completed chunk outputs:

```bash
python def14a-table-extraction/scripts/merge_def14a_chunks.py \
  --workflow outstanding-equity-awards \
  --batch-dir /path/to/batches/outstanding-equity-awards-v1
```

## Reference Files

Outstanding Equity Awards:

- `references/outstanding-equity-awards/Outstanding-Equity-Awards-Agent-Plan-V1.md`
- `references/outstanding-equity-awards/Outstanding-Equity-Awards-Chunk-Thread-Prompt-V1.txt`
- `references/outstanding-equity-awards/Outstanding-Equity-Awards-Chunking-Batch-Prompt-V1.txt`
- `references/outstanding-equity-awards/Outstanding-Equity-Awards-Merge-Prompt-V1.txt`
- `references/outstanding-equity-awards/samples/`

Summary Compensation Table:

- `references/summary-compensation-table/Summary-Compensation-Table-Agent-Plan-V3.md`
- `references/summary-compensation-table/Summary-Compensation-Table-Chunk-Thread-Prompt-V3.txt`
- `references/summary-compensation-table/Summary-Compensation-Table-Chunking-Batch-Prompt-V2.txt`
- `references/summary-compensation-table/Summary-Compensation-Table-Merge-Prompt-V2.txt`
- `references/summary-compensation-table/samples/`

Beneficial Ownership:

- `references/beneficial-ownership/Beneficial-Ownership-Agent-Plan-V1.md`
- `references/beneficial-ownership/Beneficial-Ownership-Chunk-Thread-Prompt-V1.txt`
- `references/beneficial-ownership/Beneficial-Ownership-Chunking-Batch-Prompt-V1.txt`
- `references/beneficial-ownership/Beneficial-Ownership-Merge-Prompt-V1.txt`
- `references/beneficial-ownership/samples/`

## Workflow Differences

Outstanding Equity Awards is local-first: workers should check `data/raw` before downloading, following the bundled V1 plan.

Summary Compensation Table V3 is URL-only: workers should use `source_filing_url` / `Filing URL` and should not check local raw filing folders.

Beneficial Ownership is local-first: workers should check `data/raw`, download missing SEC filings only when the run allows network access, and save downloaded HTML before extracting. Workers should leave `Total Included Non-Direct Amount` and `Calculated Direct Shares` blank for deterministic post-merge calculation.

## Guardrails

Do not treat scripts or previous extraction output as the source of truth for cell values. Worker agents must manually inspect the filing table and follow the selected agent plan.

Do not merge until every expected chunk output file exists. Merge scripts concatenate verified chunk files in chunk order and do not deduplicate, alter reviewed cells, or re-run extraction.
