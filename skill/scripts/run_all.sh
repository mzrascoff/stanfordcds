#!/usr/bin/env bash
# Runs the full CDS pipeline: download → text → blocks → metrics → validate.
# Run from the repo root (the directory that contains scripts/, raw_pdfs/, etc.)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p raw_pdfs raw_text data/csv data/json docs

echo "==> 1. Downloading PDFs from manifest"
python3 scripts/fetch.py

echo
echo "==> 2. Extracting layout text from PDFs"
for pdf in raw_pdfs/*.pdf; do
  out="raw_text/$(basename "${pdf%.pdf}").txt"
  if [[ ! -f "$out" ]]; then
    pdftotext -layout "$pdf" "$out"
  fi
done

echo
echo "==> 3. Chunking PDFs into per-field structured JSON"
python3 scripts/parse_blocks.py

echo
echo "==> 4. Extracting numeric tables to CSV"
python3 scripts/extract_metrics.py

echo
echo "==> 5. Validating against source PDFs"
python3 scripts/validate.py

echo
echo "Done. Outputs:"
echo "  raw_pdfs/      <- $(ls raw_pdfs/ | wc -l) PDFs"
echo "  raw_text/      <- $(ls raw_text/ | wc -l) layout-text files"
echo "  data/json/     <- $(ls data/json/ 2>/dev/null | wc -l) per-year structured dumps"
echo "  data/csv/      <- $(ls data/csv/ 2>/dev/null | wc -l) curated CSVs"
echo "  docs/VALIDATION.md  <- spot-check report"
