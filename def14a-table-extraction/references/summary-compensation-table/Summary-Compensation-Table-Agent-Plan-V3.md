# Agent Plan V3 For Summary Compensation Table Creation

## Contents
- [Objective](#objective)
- [Review Standard](#review-standard)
- [Input Source](#input-source)
- [Target Output](#target-output)
- [Scope](#scope)
- [Agent Roles](#agent-roles)
- [Required Workflow](#required-workflow)
- [High-Risk Row Triggers](#high-risk-row-triggers)
- [High-Risk Review Rule](#high-risk-review-rule)
- [Comparison And Creation Rules](#comparison-and-creation-rules)
- [Output Spec](#output-spec)
- [Acceptance Criteria](#acceptance-criteria)

For examples of valid input, chunk output, and report shape, see `samples/` in this reference folder.

## Objective
Create a new master-format compensation table from a filing-list CSV by manually locating the `Summary Compensation Table` in each filing and transcribing it into the same schema used by the other master compensation tables.

## Review Standard
- Operate with audit-level precision, not throughput-level precision.
- Treat every filing row as potentially tricky until it is manually confirmed from the filing.
- The filing is the source of truth. Prior extraction failures, parser output, and nearby-row patterns are never the source of truth.

## Input Source
- Filing list is a CSV with one filing per row.
- V3 supports either of these input schemas:
  - `failure_report-after18.csv` style:
    - `cik`
    - `company_name`
    - `target_fiscal_year`
    - `source_filing_url`
    - `status`
    - `failure_reason`
    - `error`
  - coverage-style batch schema, used by `IPO-batch-22-coverage.csv` and its chunks:
    - `CIK`
    - `Company`
    - `Year`
    - `Filing URL`
    - `accession_number`
    - `filing_date`
- Column mapping rules:
  - `CIK` maps to `cik`
  - `Company` maps to `company_name`
  - `Year` maps to `target_fiscal_year`
  - `Filing URL` maps to `source_filing_url`
  - `accession_number` maps to `source_accession_number`
  - `filing_date` maps to `source_filing_date`
- If the input schema does not include `status`, `failure_reason`, or `error`, treat them as blank input fields.

## Target Output
Create a new master-format CSV using this schema:
- `CIK`
- `Company Name`
- `Filing URL`
- `ticker`
- `Name`
- `Title`
- `Year`
- `Salary ($)`
- `Bonus Awards ($)`
- `Stock Awards ($)`
- `Option Awards ($)`
- `Non-Equity Incentive Plan Compensation ($)`
- `Change in pension value and nonqualified deferred compensation earnings ($)`
- `All Other Compensation ($)`
- `Total ($)`
- `Extra information`
- `Is QA done?`

Recommended output file:
- `[batch_name]_compensation_table_master_v3.csv`

Create a per-chunk filing report using this schema:
- `cik`
- `company_name`
- `run_scope`
- `target_fiscal_year`
- `source_filing_date`
- `source_accession_number`
- `source_filing_url`
- `status`
- `extraction_method`
- `block_count`
- `table_count`
- `comp_heading_found`
- `comp_table_found`
- `grant_table_found`
- `det_rows`
- `llm_confidence`
- `cda_token_count`
- `pay_for_performance_flag`
- `elapsed_seconds`
- `error`

Report rule:
- For the per-chunk report, only these fields are required to be filled:
  - `cik`
  - `company_name`
  - `source_filing_url`
  - `status`
  - `comp_table_found`
  - `error`
- All other fields may be left blank unless the agent already has the value with confidence.

## Scope
- Input is a filing list, not a prebuilt compensation table.
- Output is a newly created master-format table.
- Each output row should correspond to one executive, using only the latest year disclosed for that executive in the filing’s `Summary Compensation Table`.
- Use the same schema and normalization style as the existing master compensation tables in this workspace.

## Agent Roles
### 1. Intake Agent
- Open the provided filing-list CSV.
- Detect which supported schema the CSV uses before processing.
- Read the filing list from the mapped fields for `cik`, `company_name`, and `source_filing_url`.
- Treat each row in the filing-list CSV as one filing work item.
- If `source_filing_url` is blank, do not invent one. Mark that filing unresolved.

### 2. Filing Agent
- Use `source_filing_url` as the only filing source.
- Do not check `Data/Raw` or any other local filing folder.
- Download the filing directly from `source_filing_url`.
- If the download fails, do not guess. Mark the filing unresolved and record the error.
- Find `Summary Compensation Table`.
- Read the table header exactly as disclosed.
- Read every executive row in that table and identify the latest disclosed year for each executive.
- Read nearby footnotes only when a cell is `N/A`, blank, ambiguous, or clearly footnote-driven.

### 3. Extraction Agent
- Create one output row per executive, using only the latest year disclosed for that executive in the filing’s `Summary Compensation Table`.
- Map the filing text into the master schema exactly as used in the other compensation master tables.
- Confirm `Name`, `Title`, `Year`, and every relevant compensation cell directly from the filing before finalizing the row.
- Keep values normalized to plain digits unless the target schema requires otherwise.
- Leave fields blank when the filing shows blank or dash.
- Preserve `N/A` only when the filing clearly discloses `N/A`.
- Set:
  - `CIK` from the mapped input `cik`
  - `Company Name` from the mapped input `company_name`
  - `Filing URL` from `source_filing_url`
  - `ticker` as blank unless the source workflow already provides a reliable ticker
  - `Extra information` as blank unless the project explicitly needs a note
  - `Is QA done?` to `true` only after manual verification of that row
- Create one filing-level report row for each filing in the chunk.
- In the report row:
  - fill `cik`
  - fill `company_name`
  - fill `source_filing_url`
  - fill `status`
  - fill `comp_table_found`
  - fill `error`
  - leave non-starred fields blank unless confidently known

### 4. Review Agent
- Re-open the created rows and verify they parse cleanly in CSV format.
- Spot-check every created row against the filing one more time.
- Re-check all high-risk rows a second time from scratch before finalizing the filing.
- Finalize the created master-format CSV and the per-chunk filing report.

## Required Workflow
1. Read the provided filing-list CSV.
2. For each filing row:
   - use the mapped fields for `cik`, `company_name`, `target_fiscal_year`, and `source_filing_url`
   - if `source_filing_url` is blank, mark the filing unresolved and continue
   - download the filing from `source_filing_url`
   - locate `Summary Compensation Table`
   - identify every disclosed executive row in that table
   - determine the latest disclosed year for each executive
3. For each executive:
   - manually inspect the row cell by cell
   - keep only the latest year for that executive
   - create one output row in the master-table schema
   - confirm `Name`, `Title`, `Year`, and every relevant compensation cell directly from the filing, including `Bonus Awards ($)`, `Stock Awards ($)`, `Option Awards ($)`, `Change in pension value and nonqualified deferred compensation earnings ($)`, and `All Other Compensation ($)`
4. Mark every completed output row with `Is QA done? = true`.
5. Create one report row per filing in the chunk using the standard report schema.
6. Verify the created CSV and the report CSV.
7. Re-check every high-risk row from scratch.
8. Report counts:
   - filings reviewed
   - filings successfully converted
   - output rows created
   - filings still unresolved

## High-Risk Row Triggers
- Split name/title rows.
- Executive transition wording such as `former`, `from`, `until`, `effective`, or multiple executives sharing one role in the same year.
- Large or unusual `All Other Compensation ($)` values.
- Rows with many blanks and one large total.
- Suspected stock/option/non-equity column shifts.
- Tables where only one of `Stock Awards ($)` or `Option Awards ($)` is present.
- Footnote-heavy rows.
- Name variants with credentials, suffixes, punctuation, or footnote markers.
- Any row where the table layout is visually compressed or repeated across multiple header lines.

## High-Risk Review Rule
- If any high-risk trigger is present, the row requires a mandatory second manual review before finalization.
- The second review must start from the filing again, not from a drafted output row.
- If the agent still cannot resolve the row confidently, it must not guess.

## Comparison And Creation Rules
- The target schema should match the style of the other master compensation tables in this workspace.
- Do not invent rows that are not actually in the filing’s `Summary Compensation Table`.
- Do not include older years for an executive if the same executive has a more recent year in the same filing.
- Do not invent mappings for columns that do not appear in the filing.
- Before assigning any award value, confirm whether the filing header includes `Stock Awards ($)`, `Option Awards ($)`, both, or neither.
- If only `Option Awards ($)` is present in the filing, map the award value only to `Option Awards ($)` and leave `Stock Awards ($)` blank.
- If only `Stock Awards ($)` is present in the filing, map the award value only to `Stock Awards ($)` and leave `Option Awards ($)` blank.
- If the filing has `Bonus` but the target schema uses `Bonus Awards ($)`, map the disclosed bonus into `Bonus Awards ($)`.
- If the filing has `Bonus` and also `Non-Equity Incentive Plan Compensation ($)`, preserve each value in its corresponding field.
- Do not accept a row as correct just because the total appears to reconcile.
- Do not infer a cell value from adjacent rows, prior years, or expected compensation patterns.
- If a filing truly does not contain a `Summary Compensation Table` after manual review, do not fabricate one.

## Output Spec
### Created Master CSV
- One row per executive, using only the latest disclosed year for that executive in the filing’s `Summary Compensation Table`.
- Same schema as the other master compensation tables in this workspace.
- Final column must be `Is QA done?`.
- Reviewed created rows must have `true` in `Is QA done?`.

### Per-Chunk Filing Report CSV
- One row per filing in the chunk.
- Use this exact column order:
  - `cik`
  - `company_name`
  - `run_scope`
  - `target_fiscal_year`
  - `source_filing_date`
  - `source_accession_number`
  - `source_filing_url`
  - `status`
  - `extraction_method`
  - `block_count`
  - `table_count`
  - `comp_heading_found`
  - `comp_table_found`
  - `grant_table_found`
  - `det_rows`
  - `llm_confidence`
  - `cda_token_count`
  - `pay_for_performance_flag`
  - `elapsed_seconds`
  - `error`
- Only these fields are required to be filled:
  - `cik`
  - `company_name`
  - `source_filing_url`
  - `status`
  - `comp_table_found`
  - `error`
- Leave non-starred fields blank unless the value is confidently available.
- Suggested status values:
  - `completed`
  - `failed`
  - `unresolved`
- Suggested `comp_table_found` values:
  - `True`
  - `False`
- Leave `error` blank when the filing was completed cleanly.

## Acceptance Criteria
- Every filing from the input CSV with a nonblank `source_filing_url` has been manually reviewed for a `Summary Compensation Table`.
- Every created row was manually confirmed against the filing before final output.
- Every high-risk row received a second manual review.
- Every created row uses the target master-table schema.
- Every finalized row has `Is QA done?` set to `true`.
- Every filing in the chunk has exactly one report row in the standard report schema.
