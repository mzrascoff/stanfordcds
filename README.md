# Stanford Common Data Set — Open Data Repository

An open, machine-readable repository of every Stanford University Common Data Set (CDS) report ever published, scraped from the [Stanford Institutional Research & Decision Support](https://irds.stanford.edu/data-findings/cds) page and parsed out of PDFs into CSV and JSON.

**Coverage:** 18 academic years, **2008-09 through 2025-26.**

**Why this exists.** Stanford (like nearly every U.S. university) publishes its CDS only as PDFs. That makes it nearly impossible to pull a 10-year trend of admit rates or financial-aid generosity without a great deal of manual transcription. This repo does the transcription once and ships the result as flat files anyone can `pd.read_csv` or `cat`.

> **Disclaimer.** This is an unofficial community project. The authoritative source is Stanford's published PDFs in `raw_pdfs/`. Always cross-check figures against the PDF before quoting. See `docs/EXTRACTION_NOTES.md` for known limitations.

---

## Quick start

```bash
# Clone the repo
git clone <this-repo>.git
cd stanford-cds-open

# Look at the data
ls data/csv/
head data/csv/admissions_summary.csv

# In Python
import pandas as pd
adm = pd.read_csv("data/csv/admissions_summary.csv")
print(adm.pivot(index="year", columns="metric", values="value"))
```

A starter analysis notebook lives in `notebooks/01_admissions_trends.ipynb`.

---

## Repository layout

```
stanford-cds-open/
├── README.md
├── LICENSE
├── raw_pdfs/                 # original PDFs (~10 MB total)
│   └── stanford-cds-YYYY-YYYY.pdf   ×18
├── raw_text/                 # `pdftotext -layout` output, one .txt per year
│   └── stanford-cds-YYYY-YYYY.txt
├── data/
│   ├── csv/                  # long-format CSVs — one row per (year, metric)
│   │   ├── admissions_summary.csv          # totals: applied / admitted / enrolled
│   │   ├── admissions_by_sex.csv           # broken out by male / female / unknown
│   │   ├── test_scores.csv                 # SAT & ACT 25th/50th/75th percentiles
│   │   ├── enrollment_summary.csv          # B1 enrollment table by level + sex
│   │   ├── tuition_and_fees.csv            # G1 cost-of-attendance components
│   │   ├── financial_aid_summary.csv       # H section aid headline metrics
│   │   ├── faculty_summary.csv             # student/faculty ratio + faculty counts
│   │   ├── graduation_rates.csv            # 4-/5-/6-yr graduation + freshman retention
│   │   └── all_fields_long.csv             # index of every field in every year
│   └── json/                 # full per-year structured dump
│       └── YYYY-YYYY/blocks.json          # {section: {field_code: {label, raw_text}}}
├── scripts/
│   ├── manifest.py           # list of all CDS PDFs and their Drive IDs
│   ├── download.py           # fetches every PDF
│   ├── parse_blocks.py       # stage 1: chunk PDFs into field-keyed blocks
│   └── extract_metrics.py    # stage 2: extract clean numeric CSVs
├── docs/
│   ├── EXTRACTION_NOTES.md   # known limitations + which fields are clean vs. raw
│   └── VALIDATION.md         # spot-check results
└── notebooks/
    └── 01_admissions_trends.ipynb
```

---

## Schema reference

### `admissions_summary.csv`
| Column  | Type | Description                                                  |
| ------- | ---- | ------------------------------------------------------------ |
| year    | str  | Academic year, e.g. `2024-2025`                              |
| metric  | str  | One of `applied`, `admitted`, `enrolled`                     |
| value   | int  | Total count, summed over male + female + unknown             |

### `admissions_by_sex.csv`
| year | metric (`applied`/`admitted`/`enrolled`) | sex (`male`/`female`/`unknown`) | value |

### `test_scores.csv`
| year | test (`SAT_total`, `SAT_math`, `SAT_EBRW`, `ACT_composite`, …) | p25 | p50 | p75 |
> Some pre-2017 CDSes only published 25th/75th percentile (no median); those rows have `p50` blank.

### `enrollment_summary.csv`
| year | category (`undergrad_FT_total`, `graduate_total`, `grand_total`, …) | male | female | unknown |

### `tuition_and_fees.csv`
| year | expense (`tuition_first_year`, `required_fees`, `food_and_housing`, `room_and_board`, `books_supplies`, `transportation`, `other_expenses`, …) | amount (USD) |

### `financial_aid_summary.csv`
| year | metric (`avg_need_based_grant_award`, `avg_need_based_loan`, `avg_financial_aid_package`, `avg_per_borrower_cumulative_debt`, `pct_class_borrowed`, `num_grads_in_borrowing_cohort`) | value |

### `faculty_summary.csv`
| year | metric (`student_faculty_ratio`, `total_instructional_faculty`) | value |

### `graduation_rates.csv`
| year | metric (`rate_4yr_pct`, `rate_5yr_pct`, `rate_6yr_pct`, `freshman_retention_rate_pct`) | value |

### `all_fields_long.csv`
A flat index: every field code (A0, A1, …, J3) found in every year, with a one-line preview of its raw text. Useful for grep-ing the corpus.

---

## How to reproduce

```bash
pip install pdfplumber                          # only dependency
python scripts/download.py                       # ~10 MB total, < 1 minute
python scripts/parse_blocks.py                   # stage 1 → data/json/
python scripts/extract_metrics.py                # stage 2 → data/csv/
```

If Stanford updates the IRDS page, add the new file ID to `scripts/manifest.py` and re-run.

---

## License & attribution

The CDS data itself is published by Stanford University. Stanford does not currently attach an explicit reuse license to the published PDFs. This repository is a derivative work intended for **non-commercial educational and research use only**. If you republish, **always credit Stanford IRDS as the source** and link back to <https://irds.stanford.edu/data-findings/cds>.

The parser code in `scripts/` is released under the MIT License (see `LICENSE`).

---

## Caveats

1. **The CDS template changes over time.** Some field codes (for example race/ethnicity reporting) shift dramatically between years; trend lines should always be sanity-checked against the source PDFs.
2. **Numeric extraction is regex-based and best-effort.** Fields whose values appear in multi-column tables (notably H1 financial-aid totals broken out by source, B2 enrollment by ethnicity, J1 fields-of-study breakdown) are preserved verbatim in `blocks.json` but are NOT parsed into the curated CSVs. Adding these is a great PR opportunity.
3. **The 2025-26 student/faculty ratio** is reported as `10 to 1` because Stanford that year switched to the IPEDS methodology counting all 14,211 students; earlier years used a more conservative ratio of around 5:1. This is a real reporting change in the source, not a parsing artifact.
4. **2018-19 was an unusual layout** — every line had a leading "C1"/"H1"/etc. field-code prefix. The parser handles this but if you spot a value that looks off in that year, double-check against the PDF.

See `docs/EXTRACTION_NOTES.md` for more.

---

## Reproducing this for your university

This repo includes a [Claude skill](./skill/SKILL.md) that generalizes the
parser so it works for any U.S. university's CDS PDFs. The CDS template is
standardized across institutions, so the same scripts that ingested 18 years
of Stanford CDSes will work for Princeton, Harvard, MIT, your state flagship,
or any liberal-arts college that publishes one.

To use it:

```bash
# 1. Copy the skill into your project
cp -r skill/ ../mycollegecds && cd ../mycollegecds

# 2. List your university's CDS PDFs in scripts/manifest.py
#    (URLs, Google Drive IDs, or local paths all work)

# 3. Run the pipeline
bash scripts/run_all.sh

# 4. Optionally publish as your own repo
git init -b main && git add -A
git commit -m "Initial release: <university> CDS"
gh repo create <university>cds --public --source=. --push
```

See `skill/SKILL.md` for the full workflow Claude follows when invoked, and
`skill/references/example-manifests/` for filled-in manifests you can use as
templates.
