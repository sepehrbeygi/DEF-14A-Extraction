# DEF 14A Extraction

Reusable Codex skill and helper scripts for chunked extraction of compensation tables from DEF 14A proxy filings.

This repository currently supports two workflows:

- Outstanding Equity Awards at Fiscal Year-End
- Summary Compensation Table

The workflow is designed for large filing lists: split input filings into chunk CSVs, run Codex workers over chunks in parallel waves, then merge completed chunk outputs after schema validation.

## What Is DEF 14A?

DEF 14A is the definitive proxy statement that U.S. public companies file with the SEC when they ask shareholders to vote on annual meeting matters. It is filed under Schedule 14A, which covers proxy statements pursuant to Section 14(a) of the Securities Exchange Act of 1934.

DEF 14A filings commonly include:

- Director nominees and board committee information
- Shareholder voting matters
- Executive compensation tables and narrative disclosure
- Outstanding equity awards
- Say-on-pay proposals
- Beneficial ownership and related governance disclosures
- Shareholder proposals and company responses

These filings matter because they connect governance, incentives, ownership, and shareholder voting. For compensation research in particular, DEF 14A documents often contain the cleanest source tables for named executive officer pay, stock awards, option awards, incentive compensation, and year-end equity exposure.

## What Is A Skill?

A skill is a reusable folder of agent instructions, scripts, examples, and reference material for a specific task. The required `SKILL.md` file describes when the skill should be used and what workflow the agent should follow. Supporting files, such as prompts, plans, sample CSVs, and helper scripts, live beside it and are loaded only when the task needs them.

This repository is a skill-only repo: the usable skill is the `def14a-table-extraction/` directory.

## Who Can Benefit From This Skill?

- Academic researchers studying executive compensation, pay-for-performance, corporate governance, board structure, shareholder voting, or ESG-linked incentives.
- Quant analysts building structured datasets from proxy disclosures for factor research, event studies, governance signals, management incentive features, or alternative data products.
- Institutional investors and stewardship teams reviewing say-on-pay votes, board elections, compensation design, and governance risks across large portfolios.
- Proxy advisory and corporate governance analysts comparing pay programs, incentive metrics, equity awards, director compensation, and shareholder proposal patterns.
- Activist investors and ownership researchers looking for governance weak points, compensation misalignment, insider ownership patterns, or proposal histories.
- Legal, compliance, and corporate advisory teams benchmarking disclosures, reviewing annual meeting materials, or checking compensation table consistency.
- ESG and sustainability researchers tracking whether companies tie executive compensation to ESG, safety, human capital, climate, or other non-financial metrics.
- Data vendors and internal data engineering teams converting messy proxy tables into repeatable CSV outputs with audit-friendly chunk reports.

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

## Request More DEF 14A Tables

This skill currently focuses on Outstanding Equity Awards and Summary Compensation Table extraction. DEF 14A filings contain many other useful tables and disclosures, including director compensation, pay-versus-performance, beneficial ownership, CEO pay ratio, incentive plan metrics, and shareholder proposal data.

To request support for another DEF 14A table or disclosure, open a GitHub issue: https://github.com/sepehrbeygi/DEF-14A-Extraction/issues

Helpful issue details include:

- The table or disclosure you want extracted
- One or more example DEF 14A filing URLs
- The desired output columns
- Any special edge cases, years, industries, or company types you care about
- Whether you need a one-off extraction prompt, a reusable workflow, or full chunk/merge support

## Contact Me

For questions, collaboration, agentic workflows, business process automation, or building AI products, connect with Sepehr Beygi on LinkedIn: https://www.linkedin.com/in/sepehrbeygi/
