# DEF 14A Table Extraction Skill

This folder contains the bundled Codex skill for chunked DEF 14A table extraction workflows.

Supported workflows:

- `outstanding-equity-awards`
- `summary-compensation-table`
- `beneficial-ownership`

## Workflow

Create a batch:

```bash
python def14a-table-extraction/scripts/create_def14a_batch.py \
  --workflow beneficial-ownership \
  --source-csv /path/to/All-filings-URL.csv \
  --batch-name beneficial-ownership-v1
```

Run chunk workers:

```bash
BATCH_DIR=/path/to/batches/beneficial-ownership-v1 \
WORKFLOW=beneficial-ownership \
def14a-table-extraction/scripts/run_def14a_chunk_waves.sh
```

Merge completed chunks:

```bash
python def14a-table-extraction/scripts/merge_def14a_chunks.py \
  --workflow beneficial-ownership \
  --batch-dir /path/to/batches/beneficial-ownership-v1
```

## References

Each workflow has its own reference folder with an agent plan, chunk prompt, chunking prompt, merge prompt, and sample CSVs. The agent plan is the source of truth for extraction behavior.

Beneficial ownership was added as a local-first workflow for security ownership / principal stockholder tables. It preserves row-level footnote references and content, maps direct and included ownership components, and validates chunk outputs during merge.
