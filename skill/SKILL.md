---
name: cds-extractor
description: |
  Extract structured CSV/JSON data from any U.S. university's Common Data Set (CDS)
  PDFs and assemble a clean open-data repository. The CDS uses a standardized
  template (sections A through J, fields A0–J3) shared across nearly every
  American college, so this works for Stanford, Princeton, Harvard, MIT, public
  flagships, liberal arts colleges — anyone who publishes a CDS.
  
  Trigger this skill when the user wants to:
  - "Parse the CDS for [university]"
  - "Extract admissions / financial aid / tuition data from CDS PDFs"
  - "Build an open data repo from [university]'s Common Data Set"
  - "Convert CDS PDFs to CSV"
  - "Track 5/10/20-year trends in admit rate / yield / test scores at [university]"
  - "Reproduce the Stanford CDS open data repo for another school"
  Also trigger for any request that names the Common Data Set or a specific
  CDS section by code (e.g. "B1 enrollment table", "C9 test scores").
---

# Common Data Set extractor

Convert university Common Data Set PDFs into a queryable open-data repo.

## When to use this skill

Use it when the user has, or wants to acquire, one or more CDS PDFs from a
U.S. college or university and wants the data in CSV/JSON form. Don't use it
for other types of higher-ed data (IPEDS direct, college scorecard, internal
admissions data); those have their own structures.

## Inputs

The user typically supplies one of:

1. **A list of public PDF URLs** — most institutions publish their CDSes on a
   public IR/registrar page (e.g. `irds.stanford.edu/data-findings/cds`,
   `princeton.edu/.../common-data-set`). Some host on Google Drive.
2. **A folder of PDFs they've already downloaded.**
3. **The URL of a CDS index page** — Claude can scrape it for PDF links.

If the user only names the institution without supplying URLs, web-search
`<university> common data set` and surface the index page. Confirm the URLs
with the user before downloading.

## Workflow

### 1. Build the manifest

Edit `scripts/manifest.py` to list every (year_label, source) pair you want
to ingest. `source` can be:

- A direct PDF URL: `"https://provost.princeton.edu/sites/default/files/2024-04/CDS_2023-2024.pdf"`
- A Google Drive file ID: `"1GIPKgVj1d86dkmLkHI_mZVCk_iY6kiCp"`
- An absolute local path: `"/Users/me/Downloads/cds_2024.pdf"`

```python
CDS_MANIFEST = [
    ("2024-2025", "https://example.edu/cds/2024-2025.pdf"),
    ("2023-2024", "https://example.edu/cds/2023-2024.pdf"),
]
```

### 2. Download the PDFs

```bash
python scripts/fetch.py
```

Saves to `raw_pdfs/cds-<year>.pdf`. Skips files that already exist with
non-trivial size, so it's safe to re-run after manifest edits.

### 3. Convert PDFs to layout text

```bash
for f in raw_pdfs/*.pdf; do
  pdftotext -layout "$f" "raw_text/$(basename "${f%.pdf}").txt"
done
```

`pdftotext` ships with poppler (`brew install poppler` on macOS). The
`-layout` flag preserves column alignment which the parsers rely on.

### 4. Chunk into per-field structured JSON

```bash
python scripts/parse_blocks.py
```

Walks each `raw_text/` file, splits it into the 10 sections (A–J), and
keys every numbered field block (`A0`, `A1`, …, `J3`) with its raw text.
Output: `data/json/<year_label>/blocks.json`.

This step works on the standard CDS template and rarely needs adjusting.
If a year fails, the most likely culprit is a section header that uses a
non-standard label — search for `SECTION_HEADERS` in `parse_blocks.py` and
add a regex variant.

### 5. Extract clean numeric tables

```bash
python scripts/extract_metrics.py
```

Reads `data/json/*/blocks.json` and produces long-format CSVs in
`data/csv/`:

| File | What it covers |
| --- | --- |
| `admissions_summary.csv` | applied / admitted / enrolled per year |
| `admissions_by_sex.csv` | same broken out by male/female/unknown |
| `test_scores.csv` | SAT & ACT 25th/50th/75th percentiles |
| `enrollment_summary.csv` | undergrad/grad × FT/PT × M/F |
| `tuition_and_fees.csv` | tuition, fees, food/housing, books, transport |
| `financial_aid_summary.csv` | avg need-based grant / loan / aid package |
| `faculty_summary.csv` | total faculty + student/faculty ratio |
| `graduation_rates.csv` | 4/5/6-yr grad rates + freshman retention |
| `all_fields_long.csv` | every field × every year (searchable index) |

### 6. Validate

```bash
python scripts/validate.py
```

Picks 19 random extracted values and confirms each appears verbatim in the
source PDF text. Writes `docs/VALIDATION.md` with results. The Stanford
benchmark hit 100% pass rate. New universities should also hit 90%+; lower
indicates a parser quirk to investigate.

### 7. Wrap as a repo (optional)

```bash
git init -b main
git add -A
git commit -m "Initial release: <university> CDS"
gh repo create <university>cds --public --source=. --push
```

## What this skill does NOT extract automatically

The CDS contains some multi-dimensional tables that don't fit a flat
(year, metric, value) shape. They are preserved verbatim in
`data/json/<year>/blocks.json` under the relevant field code, but adding
them to the curated CSVs requires a custom extractor:

- **B2** — Enrollment by race/ethnicity (categories changed in 2010 and 2024)
- **C7** — Importance of admissions factors (categorical: Very Important / …)
- **H1** — Total dollars awarded × aid type × need-based vs. non-need-based
- **H2 / H2A** — Lettered subrows A–N for aid recipients
- **I3** — Class size distribution histogram
- **J1** — Most common fields of study (CIP-coded)

When the user asks for one of these, work from `blocks.json[<section>][<field>]['raw_text']`
and follow the extractor pattern in `extract_metrics.py`.

## Adapting to a new university

The four scripts are mostly institution-agnostic — they target standard CDS
field codes. The only files you typically need to change are:

1. **`manifest.py`** — list the institution's PDFs.
2. **Section headers in `parse_blocks.py`** — only if the institution uses
   unusual capitalization or wording (e.g. "ENROLLMENT" vs. "Enrollment").

Spot-check the first run with `validate.py` — if the pass rate is below 80%,
look at any failing rows and tighten the extractor regexes in
`extract_metrics.py`.

## See also

- The reference Stanford repo: <https://github.com/mzrascoff/stanfordcds>
- Common Data Set initiative: <https://www.commondataset.org/>
- IPEDS for institution-level data outside the CDS: <https://nces.ed.gov/ipeds/>
