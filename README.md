# DEF 14A Extraction

Reusable Codex skill and helper scripts for chunked extraction of compensation tables from DEF 14A proxy filings.

This repository currently supports two workflows:

- Outstanding Equity Awards at Fiscal Year-End
- Summary Compensation Table

The workflow is designed for large filing lists: split input filings into chunk CSVs, run Codex workers over chunks in parallel waves, then merge completed chunk outputs after schema validation.

## What Is A Skill?

A skill is a reusable folder of agent instructions, scripts, examples, and reference material for a specific task. The required `SKILL.md` file describes when the skill should be used and what workflow the agent should follow. Supporting files, such as prompts, plans, sample CSVs, and helper scripts, live beside it and are loaded only when the task needs them.

This repository is a skill-only repo: the usable skill is the `def14a-table-extraction/` directory.

## Repository Layout

```text
README.md
docs/
    +-- DESIGN_NOTES.md
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

## Use In Codex

Copy the skill directory into your Codex skills folder:

```bash
cp -R def14a-table-extraction ~/.codex/skills/
```

After copying, restart Codex or refresh skill discovery so `def14a-table-extraction` is available in future sessions. Then ask Codex for a DEF 14A table extraction task, for example:

```text
Use the def14a-table-extraction skill to create a Summary Compensation Table batch from /path/to/filings.csv.
```

Codex should load the skill when your request mentions DEF 14A compensation table extraction, Outstanding Equity Awards, Summary Compensation Table, chunked extraction, or merging completed extraction chunks.

## Use In Claude

Claude skills use the same basic shape: a directory with a `SKILL.md` file plus optional supporting files.

For Claude Code, install it as a personal skill:

```bash
mkdir -p ~/.claude/skills
cp -R def14a-table-extraction ~/.claude/skills/
```

Or install it as a project skill inside a repository:

```bash
mkdir -p .claude/skills
cp -R def14a-table-extraction .claude/skills/
```

For Claude.ai, zip the `def14a-table-extraction/` directory and upload it from `Customize > Skills`. Enable code execution and file creation if your Claude plan or organization settings require it.

After installation, ask Claude directly for the workflow you want:

```text
Use the def14a-table-extraction skill to split this DEF 14A filing list into chunks and prepare worker prompts.
```

Claude should activate the skill when the request matches the `SKILL.md` description.

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
