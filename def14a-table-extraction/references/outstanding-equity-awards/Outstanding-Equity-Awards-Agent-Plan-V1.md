# Agent Plan V1 For Outstanding Equity Awards At Fiscal Year-End Extraction

## Contents
- [Objective](#objective)
- [Review Standard](#review-standard)
- [Input Source](#input-source)
- [Local Filing Lookup Rule](#local-filing-lookup-rule)
- [Target Output](#target-output)
- [Scope](#scope)
- [What Counts As The Target Table](#what-counts-as-the-target-table)
- [Table Continuation Rules](#table-continuation-rules)
- [Real Heading Validation Rules](#real-heading-validation-rules)
- [Row Creation Rule](#row-creation-rule)
- [Schema Mapping Rules](#schema-mapping-rules)
- [Header-Driven Mapping Rules](#header-driven-mapping-rules)
- [Normalization Rules](#normalization-rules)
- [Agent Roles](#agent-roles)
- [Required Workflow](#required-workflow)
- [High-Risk Triggers](#high-risk-triggers)
- [High-Risk Review Rule](#high-risk-review-rule)
- [Comparison And Creation Rules](#comparison-and-creation-rules)
- [Output Spec](#output-spec)
- [Acceptance Criteria](#acceptance-criteria)

For examples of valid input, chunk output, and report shape, see `samples/` in this reference folder.

## Objective
Create a master-format `Outstanding Equity Awards at Fiscal Year-End` dataset from a filing list chunk by manually locating the correct table in each filing, transcribing each disclosed award row into the schema used by `outstanding_equity_awards.csv`, flagging uncertain filings directly in the per-filing report, and updating the batch report during the batch merge step after chunk processing is complete.

## Review Standard
- Operate with audit-level precision, not throughput-level precision.
- Treat every filing row as potentially tricky until it is manually confirmed from the filing.
- The filing is the source of truth. Prior extraction output, row patterns, and expected compensation structures are never the source of truth.
- Treat each filing as an independent document, even when multiple filings in the batch are for the same company.
- Do not assume the same company uses the same table structure, row grouping, date logic, stock columns, role formatting, or continuation behavior across different filings or years.
- Do not carry mapping assumptions from one filing into another filing, even for the same issuer.
- This plan is the extraction specification and source of truth for chunk runs.
- The chunk prompt is intentionally brief. If the prompt is shorter than this plan or appears less specific, follow this plan.

## Input Source
- Input is a chunk CSV.
- Each chunk row is one filing work item, not one award row.
- Required chunk columns:
  - `cik`
  - `target_fiscal_year`
  - `source_filing_url`
- Recommended chunk columns:
  - `company_name`
  - `source_filing_date`
  - `source_accession_number`
  - `zero_padded_cik`
  - `source_accession_number_nodashes`
  - `local_html_path`
  - `local_html_exists`
  - `status`
  - `error`

## Local Filing Lookup Rule
- If the chunk row already includes `local_html_path` and `local_html_exists=TRUE`, open that file directly first.
- First look for the filing HTML in `[PROJECT_ROOT]/data/raw`.
- Before declaring a filing missing from `data/raw`, derive local filenames from the filing row as:
  - zero-padded 10-digit `cik`, or `zero_padded_cik` if already present
  - `_`
  - accession number from `source_accession_number_nodashes` if present, otherwise from `source_accession_number` or `source_filing_url` with dashes removed
- Check these local paths in order:
  - `[PROJECT_ROOT]/data/raw/[zero-padded CIK]_[accession-without-dashes].html`
  - `[PROJECT_ROOT]/data/raw/[zero-padded CIK]_[accession-without-dashes].htm`
- If the local filing is present, use it instead of downloading.
- If the local filing is not present and the workflow allows network access, download the filing from `source_filing_url`.
- If the filing still cannot be obtained, mark the filing unresolved in the report and set `investigation_required=TRUE`.

## Target Output
Create or append to a master-format CSV using this exact schema from `[PROJECT_ROOT]/outstanding_equity_awards.csv`:
- `CIK`
- `Company Name`
- `Filing URL`
- `Name`
- `Role`
- `Grant Date`
- `Option Award (Number of Securities Underlying Unexercised Options Exercisable (#))`
- `Option Award (Number of Securities Underlying Unexercised Options Unexercisable (#))`
- `Option Award (Equity Incentive Plan Awards: Number of Securities Underlying Unexercised Unearned Options (#))`
- `Option Exercise Price ($)`
- `Option Expiration Date`
- `Stock Awards (Number of Shares or Units of Stock that Have Not Vested (#))`
- `Stock Awards (Market Value of Shares or Units of Stock that Have Not Vested ($))`
- `Stock Awards (Equity Incentive Plan Awards: Number of Unearned Shares, Units, or Other Rights that Have Not Vested (#))`
- `Stock Awards (Equity Incentive Plan Awards: Market or Payout Value of Unearned Shares, Units, or Other Rights that Have Not Vested ($))`

Recommended chunk output file:
- `[chunk_name]_outstanding_equity_awards.csv`

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
- `equity_heading_found`
- `equity_table_found`
- `rows_extracted`
- `llm_confidence`
- `investigation_required`
- `elapsed_seconds`
- `error`

Report rule:
- Only these fields are required unless other values are confidently known:
  - `cik`
  - `company_name`
  - `source_filing_url`
  - `status`
  - `equity_table_found`
  - `error`

## Scope
- Input is a filing list chunk, not a prebuilt awards table.
- Output rows should match the row-level structure of the disclosed `Outstanding Equity Awards at Fiscal Year-End` table.
- One filing can create many output rows for the same executive.
- One executive can appear across multiple rows because different grants, different award types, or split option/stock lines are disclosed separately.
- If the same executive name spans multiple consecutive rows in the filing, repeat the name on every created CSV row that belongs to that executive.

## What Counts As The Target Table
- Look for headings such as:
  - `Outstanding Equity Awards at Fiscal Year-End`
  - `Outstanding Equity Awards at 2024 Fiscal Year End`
  - `Outstanding Equity Awards at 2025 Fiscal Year-End`
  - `Outstanding Equity Awards at December 31, 2024`
  - `Outstanding Equity Awards at December 31, 2023`
  - `Outstanding Equity Awards at Year End`
- The exact year in the heading may differ from `target_fiscal_year`; the filing disclosure itself is the source of truth.
- Treat `Outstanding Equity Awards at December 31, YYYY` as a valid target-heading variant even when the filing does not use the literal phrase `Fiscal Year-End`.
- Ignore table-of-contents entries, cross-reference links, and internal navigation links that repeat the heading text but are not the actual body section.
- The table may begin on the next page after the heading.
- The same table may continue across one or more later page breaks after the first visible page of rows.
- The table may contain:
  - only option columns
  - only stock columns
  - both option and stock columns
  - extra equity incentive plan columns for unearned options or unearned shares
  - `Grant Date`
  - `Award Date`
  - `Vesting Commencement Date`
- If the table uses `Award Date` instead of `Grant Date`, map `Award Date` into the output `Grant Date` field.
- If the table uses `Vesting Commencement Date` instead of `Grant Date`, map `Vesting Commencement Date` into the output `Grant Date` field.

## Table Continuation Rules
- After finding the target heading or the first page of the target table, keep scanning forward until the table truly ends.
- Start extraction from the first page of rows that follows the real body heading, not from a later repeated header on a continuation page.
- Do not stop only because a page break, page header, page footer, or repeated column header appears.
- Treat later rows as part of the same table when the next page resumes the same column structure, row pattern, or executive award disclosure.
- A repeated header after a page break usually means the same table is continuing, not that a new table has started.
- If a later page repeats the column headers, make sure the rows from the earlier page were already captured before continuing onto the repeated-header page.
- If continuation rows after a page break or within the same table have a blank name cell, keep assigning those rows to the most recent executive name until a new nonblank executive name appears.
- If a page ends with executive A and the next page starts with a repeated header followed by unnamed numeric rows, treat those first unnamed rows as executive A's continuation until a new explicit name appears or the filing clearly moves to footnotes.
- For every page boundary inside the table, explicitly compare the last named executive on the prior page with the first data rows on the next page before deciding the table has switched executives or ended.
- Only treat the table as ended when the filing clearly moves into footnotes, a different compensation table, a new section heading, or unrelated narrative text.
- Before finalizing a filing as extracted, explicitly check whether additional executive rows appear after the first page of the table.

## Real Heading Validation Rules
- Do not treat a table-of-contents hyperlink or bookmarked cross-reference as the actual table heading.
- A real target heading should appear in the body of the executive compensation disclosure and should usually be followed by explanatory text such as `The following table shows...` or by the table itself.
- If the first text match for the heading is followed by an unrelated table such as a director list, committee roster, or governance table, continue searching for the real body section instead of failing the filing.
- When multiple matches for the heading text exist, prefer the body section that is followed by the actual option and stock award column headers.
- Do not reject a filing just because the heading uses a date-specific suffix such as `at December 31, 2024` or `at December 31, 2023` instead of `Fiscal Year-End`.
- If a body heading starts with `Outstanding Equity Awards at` and is followed by the real `Option Awards` / `Stock Awards` table structure, treat it as the target table even if the suffix wording differs from prior filings.

## Row Creation Rule
- Create one output row per disclosed award line in the target table.
- Do not collapse multiple disclosed filing rows into one synthesized row unless the filing visually uses a single row with wrapped text only.
- Do not merge separate option and stock rows just because they share the same name and grant date.
- A valid output row must contain at least one populated award field beyond `Name`, `Role`, and `Grant Date`.
- Do not emit pure name rows, pure title rows, roster rows, or other rows that contain no award values.
- Do not emit table header rows or subheader rows as award data.
- When a filing leaves the name cell blank on continuation rows, carry forward the prior executive name until the next explicit name appears.
- Only populate `Role` when the role is disclosed inside the target Outstanding Equity Awards table itself, including an immediate split row, italic row, or continuation row that is visibly part of the same table row block.
- When a filing discloses the executive role in a second split row, italic row, or separate continuation row immediately under the name within the target table, capture that text in `Role` and repeat it across that executive's output rows.
- When a filing shows the role in parentheses within the same cell as the executive name inside the target table, split it so `Name` contains only the person name and `Role` contains the parenthetical title without the surrounding parentheses.
- Do not pull `Role` from narrative text, executive biographies, other compensation tables, employment agreement sections, or any filing content outside the target Outstanding Equity Awards table.
- If no role is disclosed for the row or executive block, leave `Role` blank.
- If a filing discloses a blank grant date for a row, leave `Grant Date` blank.
- If the table does not contain a `Grant Date` header but does contain an `Award Date` header, use `Award Date` as `Grant Date`.
- If the table does not contain `Grant Date` or `Award Date` but does contain a `Vesting Commencement Date` header, use `Vesting Commencement Date` as `Grant Date`.
- If the table contains none of `Grant Date`, `Award Date`, or `Vesting Commencement Date`, leave `Grant Date` blank and do not shift nearby numeric award counts into that field.
- If a filing uses em dashes or blanks for a value, leave the target cell blank unless the existing dataset convention clearly preserves the disclosed text.

## Schema Mapping Rules
- `CIK`
  - use the zero-padded 10-digit `cik`
- `Company Name`
  - use `company_name` from the chunk if available
  - if missing, leave blank rather than inventing
- `Filing URL`
  - use `source_filing_url`
- `Name`
  - use the executive name from the table
  - if the title is in a separate italic row, do not put the title into `Name`
  - if the filing shows the title in parentheses in the same cell, remove the parenthetical title from `Name`
- `Role`
  - map the executive role or title only when the target Outstanding Equity Awards table itself discloses it
  - if the role appears in a second split row or separate title row within the target table, carry it into `Role`
  - if the role appears in parentheses after the name within the target table, capture the parenthetical text in `Role` without the parentheses
  - do not infer or import the role from elsewhere in the filing
  - if the filing does not disclose a role for that executive block inside the target table, leave blank
- `Grant Date`
  - map from the filing `Grant Date` column when present
  - if `Grant Date` is not present but `Award Date` is present, map `Award Date` into `Grant Date`
  - if neither `Grant Date` nor `Award Date` is present but `Vesting Commencement Date` is present, map `Vesting Commencement Date` into `Grant Date`
  - otherwise leave blank
- `Option Award (Number of Securities Underlying Unexercised Options Exercisable (#))`
  - map from the filing exercisable option count column
- `Option Award (Number of Securities Underlying Unexercised Options Unexercisable (#))`
  - map from the filing unexercisable option count column
- `Option Award (Equity Incentive Plan Awards: Number of Securities Underlying Unexercised Unearned Options (#))`
  - fill only if the filing explicitly has an unearned-options equity incentive plan column
- `Option Exercise Price ($)`
  - map directly from the filing
- `Option Expiration Date`
  - map directly from the filing
  - do not leave blank when the filing visibly discloses an expiration date in the option block
- `Stock Awards (Number of Shares or Units of Stock that Have Not Vested (#))`
  - map only from a filing column explicitly labeled as nonvested shares/units of stock
- `Stock Awards (Market Value of Shares or Units of Stock that Have Not Vested ($))`
  - map only from a filing column explicitly labeled as market value of nonvested shares/units of stock
- `Stock Awards (Equity Incentive Plan Awards: Number of Unearned Shares, Units, or Other Rights that Have Not Vested (#))`
  - fill only if the filing explicitly has an unearned-shares equity incentive plan column
  - if the filing stock section uses only this unearned-shares column and does not have a plain nonvested-shares column, put the stock count here and leave the plain nonvested-shares column blank
- `Stock Awards (Equity Incentive Plan Awards: Market or Payout Value of Unearned Shares, Units, or Other Rights that Have Not Vested ($))`
  - fill only if the filing explicitly has the related market or payout value column
  - if the filing stock section uses only this market-or-payout-value column and does not have a plain market-value-of-nonvested-shares column, put the dollar value here and leave the plain market-value column blank

## Header-Driven Mapping Rules
- Map every stock-side value according to the exact stock column header above that value, not according to what seems economically similar.
- Do not place a stock value into the plain nonvested stock columns when the filing header instead says `Equity Incentive Plan Awards: Number of Unearned Shares, Units or Other Rights That Have Not Vested` or `Market or Payout Value of Unearned Shares, Units or Other Rights That Have Not Vested`.
- Some filings use only equity incentive plan stock columns and omit the plain nonvested stock columns entirely.
- When only the equity incentive plan stock columns are present, leave the plain stock-award columns blank.

## Normalization Rules
- Match the style already used in `outstanding_equity_awards.csv`.
- Remove thousands separators from numeric values.
- Preserve decimal precision for prices and dollar values when disclosed.
- Preserve slash-form dates when the filing uses slash-form dates.
- Do not convert blanks or dashes into zero.
- Do not invent a grant date from nearby footnotes or from award history.
- When a filing displays option exercise price as a standalone `$` marker plus a separate numeric value, treat both cells as the single price field and still map the following date into `Option Expiration Date`.

## Agent Roles
### 1. Intake Agent
- Open the chunk CSV.
- Treat each row as one filing work item.
- Read `cik`, `target_fiscal_year`, and `source_filing_url`.
- If `source_filing_url` is blank, mark the filing unresolved in the report and set `investigation_required=TRUE`.

### 2. Filing Agent
- Check `data/raw` first using the local lookup rule.
- If needed, obtain the filing from `source_filing_url`.
- Locate the `Outstanding Equity Awards at Fiscal Year-End` table.
- Read the table header exactly as disclosed.
- Treat the current filing on its own terms and do not borrow table expectations from another filing for the same company.
- Validate that the matched heading is the real body section, not a table-of-contents or navigation entry.
- Follow the table across all continuation pages until the table actually ends.
- Determine whether the table includes:
  - `Grant Date`
  - `Award Date`
  - `Vesting Commencement Date`
  - option columns only
  - stock columns only
  - both option and stock columns
  - plain nonvested stock columns
  - stock-side equity incentive plan columns without plain nonvested stock columns
  - equity incentive plan columns for unearned options
  - equity incentive plan columns for unearned shares or payout value
- Read footnotes only when a cell, vesting treatment, or row split is ambiguous.

### 3. Extraction Agent
- Create one output row per disclosed award line.
- Repeat the executive name across continuation rows as needed.
- Use the filing table only, not inferred grant history.
- Re-derive the row structure and column mapping from the current filing itself, not from prior filings for the same issuer.
- Use the target Outstanding Equity Awards table only for `Role`; do not source `Role` from elsewhere in the filing.
- Confirm every mapped cell directly from the filing before finalizing the row.
- Leave cells blank when the filing shows blank or dash.
- For stock-side values, confirm the exact header above the value before choosing between the plain stock-award columns and the equity-incentive-plan stock columns.

### 4. Confidence Agent
- If the table cannot be found after careful review, do not guess.
- If the table is found but the row structure or column mapping remains ambiguous, do not guess.
- If the filing may contain a continuation page that was not fully reviewed, do not mark the filing high-confidence.
- If a filing produces more than 30 extracted award rows, automatically mark `investigation_required=TRUE` even if the extraction otherwise appears complete.
- Mark low-confidence or blocked filings in the report with `investigation_required=TRUE`.
- Record the blocker or ambiguity in the report `error` field.

### 5. Review Agent
- Re-open the created rows and verify they parse cleanly in CSV format.
- Spot-check each filing one more time against the disclosed table.
- Confirm that no additional rows for the same table appear after a page break or repeated header.
- Confirm that the first page of the table was not skipped in favor of a later repeated-header page.
- Confirm that every filing needing follow-up is clearly marked with `investigation_required=TRUE` and a useful report `error`.
- Finalize the chunk output CSV and filing report.

## Required Workflow
1. Read the chunk CSV.
2. For each filing row:
   - use `cik`, `target_fiscal_year`, and `source_filing_url`
   - if `source_filing_url` is blank, mark unresolved in the report and set `investigation_required=TRUE`
   - check `data/raw` first
   - if missing locally, obtain the filing from SEC if the workflow permits
   - locate the `Outstanding Equity Awards at Fiscal Year-End` table
   - identify the exact disclosed column layout
   - continue through repeated headers and page breaks until the target table actually ends
3. For each disclosed award row:
   - manually inspect the row cell by cell
   - create one output row in the outstanding equity awards schema
   - confirm `Name`, `Role` if present, `Grant Date`, `Award Date`, or `Vesting Commencement Date` if present, and every award cell directly from the filing
4. If the filing is not confidently extractable:
   - do not create guessed output rows
   - set `investigation_required=TRUE` in the report
   - keep `rows_extracted` limited to rows that were confidently confirmed
   - record the issue in the report `error` field
5. Create one filing-level report row per filing.
6. Verify the created CSVs.
7. After all chunk filings are complete for the batch, update the batch outputs during the merge step:
   - append or merge the chunk output into the batch master awards CSV
   - append or merge the chunk report into the master batch report

## High-Risk Triggers
- Split name/title rows.
- The executive title appears on a separate italic row.
- The executive role appears in parentheses after the name.
- More than 30 extracted award rows for a single filing.
- A potential award row contains only `Name`, `Role`, and/or `Grant Date` with no populated award values.
- A table header or subheader line appears to have been transcribed as data.
- Blank name cells on continuation rows.
- The table starts on one page and the data begins on the next page.
- The table continues onto a later page after some rows have already been disclosed.
- A repeated column header appears after a page break.
- The same table has multiple pages and the first page contains rows before a later repeated header.
- Multiple rows share the same executive name and grant date.
- Option and stock rows appear separately for the same grant date.
- The table includes `Award Date`, which must be mapped into `Grant Date` when `Grant Date` is not present.
- The table includes `Vesting Commencement Date`, which must be mapped into `Grant Date` when neither `Grant Date` nor `Award Date` is present.
- The table includes only stock columns or only option columns.
- The table includes equity incentive plan columns for unearned options or unearned shares.
- The stock section has only equity incentive plan columns and no plain nonvested stock columns.
- Footnote-heavy rows or superscript-heavy cells.
- Former executive wording such as `former`, `ceased`, `resigned`, or `consulting agreement`.
- Blank or dash-heavy rows with only one populated column group.

## High-Risk Review Rule
- If any high-risk trigger is present, perform a mandatory second review from the filing before finalizing the row.
- The second review must start from the filing again, not from a drafted CSV row.
- For multi-page tables, the second review must include the continuation pages, not just the first visible page of the table.
- If a filing has more than 30 extracted award rows, keep `investigation_required=TRUE` in the report even after the second review.
- If uncertainty remains after the second review, keep `investigation_required=TRUE` in the report instead of guessing.

## Comparison And Creation Rules
- Match the exact output column order from `outstanding_equity_awards.csv`.
- Do not invent rows that are not actually in the disclosed table.
- Do not synthesize grant dates, exercise prices, or vesting values from footnotes unless the filing explicitly ties the value to the row.
- Do not move a value into an equity incentive plan column unless the table header explicitly supports that mapping.
- Do not combine multiple filing rows into one row just because they appear economically related.
- If a filing truly does not contain the table after manual review, do not fabricate one.

## Output Spec
### Chunk Awards CSV
- One row per disclosed award line.
- Exact schema from `outstanding_equity_awards.csv`.

### Per-Chunk Filing Report CSV
- One row per filing in the chunk.
- Suggested `status` values:
  - `completed`
  - `completed_with_investigation`
  - `failed`
  - `unresolved`
- Suggested `equity_table_found` values:
  - `True`
  - `False`
- Suggested `investigation_required` values:
  - `True`
  - `False`

## Acceptance Criteria
- Every filing in the chunk with a nonblank `source_filing_url` has been reviewed for an `Outstanding Equity Awards at Fiscal Year-End` table.
- Every created output row was manually confirmed against the filing.
- Every high-risk row received a second review.
- Every extracted table was checked for continuation pages before `rows_extracted` and `llm_confidence` were finalized.
- Every low-confidence or blocked filing is marked `investigation_required=TRUE` in the report.
- Every filing with more than 30 extracted award rows is marked `investigation_required=TRUE` in the report.
- No output row is just a name/title/header line without at least one populated award field.
- The chunk output CSV matches the schema of `outstanding_equity_awards.csv`.
- The master batch report is updated after the batch merge step completes.
