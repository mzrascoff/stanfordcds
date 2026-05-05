# Extraction notes

This document explains which CDS fields are reliably parsed into clean CSVs
and which are preserved only as raw text in the blocks JSON.

## Reliably parsed → in `data/csv/`

| Field area              | Source field codes | CSV file                       | Notes |
| ----------------------- | ------------------ | ------------------------------ | ----- |
| Application volume      | C1                 | admissions_summary.csv         | applied / admitted / enrolled, totals across all sex breakouts |
| Application by sex      | C1                 | admissions_by_sex.csv          | covers male / female / unknown |
| Test scores             | C9                 | test_scores.csv                | SAT total/EBRW/Math, ACT composite/sections, p25/p50/p75 + submission rates |
| Enrollment              | B1                 | enrollment_summary.csv         | undergrad/grad × FT/PT × M/F/Unknown |
| Tuition & cost-of-attendance | G0–G6        | tuition_and_fees.csv           | tuition, fees, food/housing, books, transport, other |
| Financial aid headlines | H2 J/K/F rows, H4–H5 | financial_aid_summary.csv    | avg need-based grant, avg loan, avg aid package, avg per-borrower debt, pct who borrowed |
| Faculty + ratio         | I1, I2             | faculty_summary.csv            | Total instructional faculty count, student-to-faculty ratio (decimal-aware) |
| Graduation + retention  | B11, B22           | graduation_rates.csv           | 4/5/6-year graduation rate, freshman retention rate |

## Preserved as raw text only → in `data/json/<year>/blocks.json`

These fields contain multi-dimensional tables that don't fit a simple
(year, metric, value) shape. The current pipeline keeps the entire formatted
text under `raw_text` so a downstream user can build a custom parser.

- **B2 — Enrollment by race/ethnicity.** The race/ethnicity categories Stanford uses changed substantively in 2010 (post-IPEDS 9-category rollout) and again in 2024. A clean trend file would need a manual category-mapping pass.
- **C2 — Wait list activity.** Numerical but small and irregular.
- **C7 — Importance of admissions factors.** Categorical (Very Important / Important / Considered / Not Considered).
- **H1 — Total dollars awarded broken out by aid type × need-based vs. non-need-based.** Multi-column matrix.
- **H2 / H2A — Number of students awarded aid, lettered subrows A–N.** Same shape problem.
- **I3 — Class size distribution.** Histogram-style table.
- **J1 — Most common fields of study.** CIP-coded list.

If you need any of these as flat tables, contributions are welcome — start
from `data/json/<year>/blocks.json[<section>][<field>]['raw_text']` and
follow the pattern in `scripts/extract_metrics.py`.

## Known parsing quirks

1. **2017–18 and 2018–19** use a Drupal-generated layout where every line is
   prefixed with the field code (e.g. `C1   Total ...`). The block parser
   strips the prefix; the metric extractor uses anchor-aware regex to avoid
   matching `1` in `C1` as a numeric value.
2. **2025–26 student/faculty ratio jumps to 10:1.** Stanford switched to the
   IPEDS methodology that includes all 14,211 students. This is a real
   reporting change at the source, not a parsing bug.
3. **Older PDFs (pre-2014)** use a `pdftotext`-friendly columnar layout, but
   the colon placement varies — sometimes `Tuition: $X`, sometimes `Tuition  $X`.
   The G-section regex handles both.
4. **B22 freshman retention** for the 2020–21 CDS appears at 85.8% even
   though Stanford's other public reporting cites a higher number; the value
   in the CDS PDF really is 85.8 in that year (likely a COVID cohort effect).
5. **Empty cells.** Stanford leaves cells blank when a category does not apply
   to them (e.g. no tuition by residency at a private institution). Blank
   cells flow through as missing values, not zeros.

## Adding a year

1. Append `("YYYY-YYYY", "<google-drive-file-id>")` to `CDS_MANIFEST` in
   `scripts/manifest.py`.
2. Run `scripts/download.py` then `scripts/parse_blocks.py` then
   `scripts/extract_metrics.py`.
3. Spot-check the new year's row in each CSV against the source PDF.

## Adding a metric

The cleanest path is to add a new function in `scripts/extract_metrics.py`
following the pattern of `tuition_and_fees()` or `test_scores()`:

1. Pull the right block: `text = get_block(blocks, "<SECTION>", "<FIELD>")`
   (or fall back to `get_section_text(year, "<SECTION>")`).
2. Walk lines, regex-match the label, collect numbers.
3. Return a list of `{year, ..., value}` dicts.
4. Wire it into `main()` and add a `write_csv()` call.
