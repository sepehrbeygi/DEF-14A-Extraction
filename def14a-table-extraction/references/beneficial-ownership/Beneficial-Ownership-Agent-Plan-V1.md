# Beneficial Ownership Agent Plan V1

## Contents

- [Objective](#objective)
- [Review Standard](#review-standard)
- [Input Source](#input-source)
- [Local Filing Lookup Rule](#local-filing-lookup-rule)
- [Target Tables](#target-tables)
- [False Positive Rules](#false-positive-rules)
- [Output Schema](#output-schema)
- [Report Schema](#report-schema)
- [Row Creation Rules](#row-creation-rules)
- [Footnote Capture Rules](#footnote-capture-rules)
- [Mapping Rules](#mapping-rules)
- [Footnote Content Analysis Rules](#footnote-content-analysis-rules)
- [High-Risk Patterns](#high-risk-patterns)
- [Required Workflow](#required-workflow)
- [Merge Criteria](#merge-criteria)

## Objective

Create a row-level beneficial ownership dataset from DEF 14A/proxy filing HTML. Extract the real beneficial ownership table, preserve row-level footnote references, extract the matching footnote content, and analyze footnote content to populate direct ownership, included ownership indicators, and included option/RSU/warrant components.

## Review Standard

- Treat the filing HTML as the source of truth.
- Work at audit-level precision.
- Treat each filing independently.
- Do not rely on previous extraction output as the source of truth.
- Do not guess when table structure, row mapping, footnote matching, or directness is ambiguous.
- Mark uncertain filings or rows with `investigation_required=TRUE` in the report.

## Input Source

Input is a filing-list chunk CSV. Each row is one filing work item.

Minimum required columns:

- `cik`
- `source_filing_url`

Recommended columns:

- `company_name`
- `target_fiscal_year`
- `source_filing_date`
- `source_accession_number`
- `zero_padded_cik`
- `source_accession_number_nodashes`
- `local_html_path`
- `local_html_exists`

Known source file shape: `All-filings-URL.csv`.

## Local Filing Lookup Rule

Use local HTML before any download. If a filing is missing locally and network access is allowed, download it from `source_filing_url`, save it into `data/raw`, and then treat the saved local file as the extraction source.

1. If `local_html_path` exists and `local_html_exists=TRUE`, open it first.
2. Otherwise derive a local filename from:
   - 10-digit zero-padded CIK
   - `_`
   - accession number with dashes removed
3. Check:
   - `data/raw/[zero-padded CIK]_[accession-without-dashes].html`
   - `data/raw/[zero-padded CIK]_[accession-without-dashes].htm`
4. If missing locally and the run allows network access:
   - Create `data/raw` if needed.
   - Download from `source_filing_url`.
   - Use a compliant SEC `User-Agent` header when downloading from SEC EDGAR.
   - Save the downloaded filing as `data/raw/[zero-padded CIK]_[accession-without-dashes].html`.
   - Do not overwrite an existing local filing with different content unless the user explicitly asks.
   - Confirm the saved file is nonempty and appears to contain HTML before extracting.
5. If unavailable or the download fails, report `status=unresolved`, `ownership_table_found=False`, `investigation_required=TRUE`.

## Target Tables

Accept body-section tables under headings such as:

- `Security Ownership of Certain Beneficial Owners and Management`
- `Principal Stockholders`
- `Principal Shareholders`
- `Stock Ownership`
- `Ownership of Our Common Stock`
- `Ownership of Securities`
- `Common Stock Ownership of Directors and Executive Officers`

Heading wording can vary. Accept the table when the nearby real body section contains owner rows and columns for beneficial ownership, shares owned, amount and nature of ownership, or percent of class.

## False Positive Rules

Reject:

- table-of-contents rows
- internal links or navigation repeats
- meeting Q&A about proof of stock ownership
- Section 16(a) beneficial ownership reporting compliance sections
- director stock ownership guideline sections
- equity compensation plan information tables
- footnote-only tables unless they are attached to the actual ownership table
- narrative-only beneficial ownership limitation text

The real target table usually has columns such as:

- `Name of Beneficial Owner`
- `Name and Address of Beneficial Owner`
- `Shares Beneficially Owned`
- `Amount and Nature of Beneficial Ownership`
- `Number of Shares`
- `Percent of Class`
- `%`
- footnote references such as `(1)`, `[1]`, superscripts, or standalone row numbers

## Output Schema

Chunk output file:

- `[chunk_name]_beneficial_ownership.csv`

Use this exact column order unless the user explicitly changes it:

- `CIK`
- `Company Name`
- `Filing URL`
- `Source Filing Date`
- `Source Accession Number`
- `Beneficial Owner`
- `Owner Category`
- `Title / Position`
- `Address`
- `Security Class`
- `Shares Beneficially Owned`
- `Shares Beneficially Owned (Direct)`
- `Is Direct`
- `Includes Indirect Ownership`
- `Percent of Class`
- `Options Exercisable Within 60 Days`
- `RSUs Vesting Within 60 Days`
- `Warrants Exercisable Within 60 Days`
- `Restricted Stock / Stock Awards Included`
- `Convertible / Preferred Shares Included`
- `Indirect Common Shares Included`
- `Other Included Non-Direct Securities Amount`
- `Total Included Non-Direct Amount`
- `Calculated Direct Shares`
- `Direct Shares Calculation Method`
- `Excluded / Disclaimed Securities Amount`
- `Excluded / Disclaimed Securities Detail`
- `Other Included Securities`
- `Footnote References`
- `Footnote Content`
- `Extra Information`

Do not include sole/shared voting power, sole/shared dispositive power, or total voting power percentage by default.

## Report Schema

Per-chunk report file:

- `[chunk_name]_report.csv`

Use this exact column order unless the user explicitly changes it:

- `cik`
- `company_name`
- `run_scope`
- `target_fiscal_year`
- `source_filing_date`
- `source_accession_number`
- `source_filing_url`
- `status`
- `extraction_method`
- `table_count`
- `ownership_heading_found`
- `ownership_table_found`
- `rows_extracted`
- `dual_class_table`
- `footnote_heavy`
- `llm_confidence`
- `investigation_required`
- `elapsed_seconds`
- `error`

Suggested status values:

- `completed`
- `completed_with_investigation`
- `completed_zero_rows_confirmed`
- `failed`
- `unresolved`

## Row Creation Rules

Create one output row per disclosed owner or ownership group row in the target table.

Include:

- 5% stockholders
- greater-than-five-percent stockholders
- directors
- named executive officers
- director nominees
- all directors and executive officers as a group
- institutional holders
- sponsors or private funds

Do not emit:

- group heading rows with no owner values
- blank spacer rows
- pure footnote rows
- table headers or repeated headers
- narrative-only ownership mentions outside the target table

## Footnote Capture Rules

Most beneficial ownership rows have a footnote marker. Capture the marker and matching text.

Reference capture:

- Capture markers in or adjacent to the owner name cell.
- Accept `(1)`, `[1]`, superscripts, and standalone numbers.
- Preserve multiple references, such as `(1)(2)` or `1, 2`.
- Store normalized markers in `Footnote References`.
- Locate matching content near the table, usually immediately after the table and before the next major section.
- Store the full matched note text in `Footnote Content`.

Table-heading footnotes:

- If a marker belongs to the table heading or table-level ownership explanation, capture it.
- Assign table-heading footnotes to the first executive/director row.
- If no executive/director row exists, assign to the first extracted owner row.
- Do not duplicate table-heading footnotes onto every row unless the filing marks every row with that reference.

Cumulative footnotes:

- Some notes describe multiple executives or directors in one note.
- When a footnote lists multiple named people and their share, option, RSU, warrant, or excluded-security amounts, parse it person by person.
- Assign each amount only to the matching extracted owner row.
- Use conservative name matching. Prefer full-name matches. Allow `Mr. Smith`, `Dr. Werner`, or last-name-only references only when the table row makes identity unambiguous.
- If any name or amount cannot be confidently matched, preserve the full footnote text and mark `investigation_required=TRUE`.
- Do not apply every amount in a cumulative footnote to every row citing that footnote.

## Mapping Rules

- `CIK`: zero-padded 10-digit CIK when available.
- `Company Name`: use `company_name` when available.
- `Filing URL`: use `source_filing_url`.
- `Source Filing Date`: use `source_filing_date`.
- `Source Accession Number`: use `source_accession_number`.
- `Beneficial Owner`: owner or group name from the target table.
- `Owner Category`: group labels such as `5% Stockholders`, `Named Executive Officers and Directors`, or `All directors and executive officers as a group`.
- `Title / Position`: only if disclosed in the target table.
- `Address`: only if disclosed in the owner cell or adjacent address column.
- `Security Class`: class disclosed in the relevant table column, especially multi-class tables.
- `Shares Beneficially Owned`: the table-disclosed total beneficial ownership amount.
- `Percent of Class`: table-disclosed ownership percentage.
- `Footnote References`: row/table markers.
- `Footnote Content`: matched footnote text.
- `Is Direct`: whether the table-disclosed `Shares Beneficially Owned` appears direct-only.
- `Includes Indirect Ownership`: `YES` when the matched footnote indicates indirect ownership or any ownership component included in the table amount, including options, RSUs, warrants, restricted stock, stock awards, convertible/issuable securities, trusts, family members, entities, partnerships, funds, or similar arrangements; otherwise `NO`.
- `Restricted Stock / Stock Awards Included`: numeric amount of restricted stock, unvested stock, restricted shares, stock awards, or shares subject to forfeiture included in the table amount.
- `Convertible / Preferred Shares Included`: numeric amount of shares included in the table amount because preferred stock, convertible securities, notes, or similar instruments are convertible into common stock.
- `Indirect Common Shares Included`: numeric amount of common shares included in the table amount that are held through trusts, family members, entities, partnerships, funds, investment vehicles, custodial arrangements, or similar indirect holders.
- `Other Included Non-Direct Securities Amount`: numeric amount of included non-direct securities that cannot be placed in a dedicated component column. If multiple miscellaneous included security amounts are disclosed and none fit the dedicated component columns, sum those miscellaneous included amounts into this field.
- `Total Included Non-Direct Amount`: leave blank during worker extraction. This will be calculated after merge from the numeric component columns.
- `Calculated Direct Shares`: leave blank during worker extraction. This will be calculated after merge from `Shares Beneficially Owned` minus `Total Included Non-Direct Amount`.
- `Direct Shares Calculation Method`: leave blank during worker extraction unless needed to explain why a component could not be captured numerically.
- `Excluded / Disclaimed Securities Amount`: numeric amount of securities mentioned in the footnote but expressly excluded, disclaimed, capped out, blocker-limited, or otherwise not included in the table amount.
- `Excluded / Disclaimed Securities Detail`: text explanation of securities mentioned but not included in the table amount.

Do not overwrite the table-disclosed total with parsed component values from the footnote. Do not calculate `Total Included Non-Direct Amount` or `Calculated Direct Shares` during chunk extraction. The only allowed worker-side summation is within `Other Included Non-Direct Securities Amount`, and only for miscellaneous included security amounts that do not fit any dedicated component column.

## Footnote Content Analysis Rules

Analyze `Footnote Content` after extracting the table row.

Common mappings:

- `shares of common stock owned directly`, `shares owned directly`, `held directly`, or `held of record` -> `Shares Beneficially Owned (Direct)`
- `shares issuable upon exercise of options exercisable within 60 days` -> `Options Exercisable Within 60 Days`
- `RSUs vesting within 60 days`, `restricted stock units vesting within 60 days`, or `shares issuable upon settlement of RSUs within 60 days` -> `RSUs Vesting Within 60 Days`
- `shares issuable upon exercise of warrants exercisable within 60 days` -> `Warrants Exercisable Within 60 Days`
- `restricted stock`, `restricted shares`, `unvested shares`, `stock awards`, or `shares subject to forfeiture` -> `Restricted Stock / Stock Awards Included`
- `preferred stock`, `Series A Preferred`, `convertible`, `conversion`, `convertible notes`, or similar instruments included in beneficial ownership -> `Convertible / Preferred Shares Included`
- common shares held through trusts, family members, entities, partnerships, funds, investment vehicles, custodial arrangements, or similar indirect holders -> `Indirect Common Shares Included`
- included non-direct securities that are numerically disclosed but do not fit a dedicated column -> `Other Included Non-Direct Securities Amount` plus explanation in `Other Included Securities`
- when multiple miscellaneous included security types do not fit dedicated columns, sum only those miscellaneous included amounts into `Other Included Non-Direct Securities Amount`; do not include values already mapped to options, RSUs, warrants, restricted stock/stock awards, convertible/preferred shares, indirect common shares, or excluded/disclaimed securities
- securities mentioned but excluded, disclaimed, capped out, blocker-limited, not exercisable/convertible because of an ownership limitation, or otherwise not included in the table total -> `Excluded / Disclaimed Securities Amount` and `Excluded / Disclaimed Securities Detail`
- Other included securities text -> `Other Included Securities` plus explanation in `Extra Information`
- Leave `Total Included Non-Direct Amount` and `Calculated Direct Shares` blank. They are calculation fields for a later deterministic post-merge step.

Directness:

- Set `Is Direct=TRUE` only when the table amount appears to consist solely of directly owned, held-of-record, or directly held shares.
- Set `Is Direct=FALSE` when the amount includes options, RSUs, warrants, convertible/issuable securities, shares held by trusts, family members, funds, entities, or any other indirect/non-direct component.
- Set `Is Direct=FALSE` when a footnote says the amount consists only of options, RSUs, warrants, or other derivative/issuable securities.
- If both direct shares and included securities are present, set `Is Direct=FALSE`, populate direct shares and component columns, and keep the total in `Shares Beneficially Owned`.
- Leave blank and mark `investigation_required=TRUE` when directness cannot be determined.

Included or indirect ownership:

- Set `Includes Indirect Ownership=YES` when `Footnote Content` mentions indirect ownership, or when it explains that the table amount includes any non-direct ownership component.
- Set `Includes Indirect Ownership=YES` for included options, RSUs, warrants, restricted stock, stock awards, shares issuable or underlying awards, convertible securities, other included securities, or other amounts included in beneficial ownership.
- Set `Includes Indirect Ownership=YES` for holdings through trusts, family members, entities, partnerships, funds, investment vehicles, foundations, estates, or similar arrangements.
- Set `Includes Indirect Ownership=YES` when the footnote uses phrases such as `includes`, `consists of`, `issuable upon`, `underlying`, `subject to`, `vest`, `exercisable`, `indirectly`, `held by spouse`, `held by children`, `family trust`, `revocable trust`, `LLC`, `LP`, `partnership`, `fund`, `investment fund`, `entity`, `affiliate`, `general partner`, or states that the owner disclaims beneficial ownership of shares held by another person or entity.
- Set `Includes Indirect Ownership=NO` only when the footnote does not indicate any indirect holder, arrangement, option, RSU, warrant, restricted stock, stock award, convertible/issuable security, or other included ownership component.
- If there is no row-level or assigned table-level footnote content, set `Includes Indirect Ownership=NO` unless the table row itself clearly states an included component or indirect holder.

Example from `data/raw/0001607678_000156459019010928.html`:

`Consists of: (a) 1,452,588 shares of common stock owned directly, of which 1,269,493 are vested or will vest within 60 days of April 1, 2019, and (b) 430,517 shares of common stock issuable upon exercise of options exercisable within 60 days of April 1, 2019.`

Map:

- `Shares Beneficially Owned (Direct)` = `1452588`
- `Options Exercisable Within 60 Days` = `430517`
- `Restricted Stock / Stock Awards Included` = blank
- `Total Included Non-Direct Amount` = blank
- `Calculated Direct Shares` = blank
- `Is Direct` = `FALSE`
- `Includes Indirect Ownership` = `YES`

Example from `data/raw/0001750149_000095017025069152.html`:

`Consists of 538,639 shares of common stock underlying options exercisable within 60 days of May 1, 2025.`

Map:

- `Options Exercisable Within 60 Days` = `538639`
- `Shares Beneficially Owned (Direct)` = blank
- `Total Included Non-Direct Amount` = blank
- `Calculated Direct Shares` = blank
- `Is Direct` = `FALSE`
- `Includes Indirect Ownership` = `YES`

## High-Risk Patterns

Mark `investigation_required=TRUE` when any of these are present:

- dual-class or multi-class tables
- voting power columns separate from economic ownership
- 13D-style sole/shared voting/dispositive power tables
- footnote-heavy rows with unclear ownership composition
- footnote-only table detection
- missing or unmatched row footnote references
- cumulative footnotes requiring person-by-person allocation
- ambiguous directness
- table-heading footnotes that are not clearly row-specific
- table-of-contents match before the real body table
- rows split across multiple HTML tables
- options, RSUs, warrants, and total shares shown as separate columns
- `*`, less-than-one-percent, or nonnumeric percentage conventions

## Required Workflow

1. Read the chunk CSV.
2. Resolve local HTML from `data/raw` before downloading; if missing and network access is allowed, download the filing, save it into `data/raw`, and extract from the saved file.
3. Locate the real target body section.
4. Identify the exact table header structure.
5. Extract each owner/group row into the output schema.
6. Capture row and table footnote references.
7. Match footnote references to content.
8. Analyze footnote content for direct shares, options, RSUs, warrants, other securities, `Is Direct`, and `Includes Indirect Ownership`.
9. Create one report row per filing.
10. Verify CSV schemas and parseability before finishing the chunk.

## Merge Criteria

Only merge after every expected chunk output and report exists.

The merge step should:

- validate each chunk output schema
- validate each chunk report schema
- concatenate in chunk manifest order
- not deduplicate
- not alter reviewed cell values
- report missing files, schema mismatches, merged row counts, and report row counts
