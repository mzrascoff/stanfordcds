"""
Manifest of CDS PDFs to ingest.

Each entry is (year_label, source). `source` can be:
  - A direct PDF URL:        "https://example.edu/cds/2024.pdf"
  - A Google Drive file ID:  "1GIPKgVj1d86dkmLkHI_mZVCk_iY6kiCp"  (the long random part of the share URL)
  - An absolute local path:  "/Users/me/Downloads/2024.pdf"

This file is the only place an institution-specific URL list lives.
Replace the example below with your own and save the file.
"""

CDS_MANIFEST = [
    # ("2025-2026", "https://example.edu/cds/CDS_2025-2026.pdf"),
    # ("2024-2025", "https://example.edu/cds/CDS_2024-2025.pdf"),
    # ("2023-2024", "https://example.edu/cds/CDS_2023-2024.pdf"),
]
