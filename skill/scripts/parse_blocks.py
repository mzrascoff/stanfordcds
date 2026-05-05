"""
Stage-1 parser: chunk each CDS PDF (already converted to layout text) into
field blocks keyed by their CDS field code (A1, B1, C1, ..., J3).

Output: data/json/<year>/blocks.json  - {section: {field_code: {label, raw_text}}}
"""
import json, os, re, sys

import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TXT_DIR = f"{ROOT}/raw_text"
OUT_DIR = f"{ROOT}/data/json"

SECTION_HEADERS = [
    ("A", re.compile(r"A\.\s+General\s+Information", re.I)),
    ("B", re.compile(r"B\.\s+ENROLLMENT\s+AND\s+PERSISTENCE", re.I)),
    ("C", re.compile(r"C\.\s+FIRST[- ]TIME,?\s+FIRST[- ]YEAR\s+(?:\(?FRESHMAN\)?\s+)?ADMISSION", re.I)),
    ("D", re.compile(r"D\.\s+TRANSFER\s+ADMISSION", re.I)),
    ("E", re.compile(r"E\.\s+ACADEMIC\s+OFFERINGS\s+AND\s+POLICIES", re.I)),
    ("F", re.compile(r"F\.\s+STUDENT\s+LIFE", re.I)),
    ("G", re.compile(r"G\.\s+(?:ANNUAL\s+EXPENSES|ANNUAL\s+EXPENSE)", re.I)),
    ("H", re.compile(r"H\.\s+FINANCIAL\s+AID", re.I)),
    ("I", re.compile(r"I\.\s+INSTRUCTIONAL\s+FACULTY\s+AND\s+CLASS\s+SIZE", re.I)),
    ("J", re.compile(r"J\.\s+DEGREES?\s+CONFERRED", re.I)),
]

# Field code: A0, A0A, A1, ..., A23, B1, ..., J3.  Up to 3 chars after letter.
FIELD_CODE_RE = re.compile(r"^[ \t]*([A-J])(\d{1,2}[A-Z]?)\b")

# Skip lines that are clearly TOC entries (full of dots)
TOC_RE = re.compile(r"\.{8,}")
# Skip page headers/footers
PAGE_FOOTER_RE = re.compile(r"^\s*(Page\s+\d+|Common Data Set \d{4}[-‑]\d{4})\s*$")

def is_section_header_line(line):
    for sec, rx in SECTION_HEADERS:
        if rx.search(line) and not TOC_RE.search(line):
            return sec
    return None

def find_first_real_section_start(lines):
    """Skip the table of contents and find where 'A. General Information' actually begins."""
    a_count = 0
    for i, line in enumerate(lines):
        if SECTION_HEADERS[0][1].search(line) and not TOC_RE.search(line):
            a_count += 1
            if a_count >= 1:
                # Look ahead - body starts when we see actual content (A0, A1, etc.)
                # The TOC line uses dots; the real section header has clean spacing.
                return i
    return 0

def parse_year(year):
    txt_path = f"{TXT_DIR}/cds-{year}.txt"
    if not os.path.exists(txt_path):
        return None
    with open(txt_path) as f:
        lines = f.readlines()

    # Skip the TOC area: find the FIRST occurrence of "A. General Information" that is
    # followed soon after by an "A0" or "A1" field code.
    body_start = 0
    for i, line in enumerate(lines):
        if SECTION_HEADERS[0][1].search(line) and not TOC_RE.search(line):
            # Look ahead 30 lines for A0 or A1 field
            for j in range(i+1, min(i+40, len(lines))):
                if FIELD_CODE_RE.match(lines[j]) and lines[j].strip().startswith("A"):
                    body_start = i
                    break
            if body_start: break

    # Walk body, tracking current section + current field code
    sections = {sec: {"_section_label": label_from_re(rx)} for sec, rx in SECTION_HEADERS}
    current_section = None
    current_field = None
    current_label = None
    current_buf = []

    def flush():
        nonlocal current_field, current_label, current_buf
        if current_section and current_field and current_buf:
            text = "\n".join(current_buf).rstrip()
            # Strip page footers/headers from inside blocks
            text = "\n".join(
                ln for ln in text.split("\n")
                if not PAGE_FOOTER_RE.match(ln)
                and not is_section_header_line(ln)
            ).strip("\n")
            entry = sections[current_section].setdefault(current_field, {})
            if "label" not in entry or (current_label and not entry["label"]):
                entry["label"] = current_label or ""
            # Append - in case a field's content spans multiple chunks
            existing = entry.get("raw_text", "")
            entry["raw_text"] = (existing + "\n" + text).strip("\n") if existing else text
        current_buf = []

    for line in lines[body_start:]:
        sec = is_section_header_line(line)
        if sec:
            flush()
            current_section = sec
            current_field = None
            current_label = None
            continue
        m = FIELD_CODE_RE.match(line)
        if m and current_section and m.group(1) == current_section:
            flush()
            current_field = m.group(1) + m.group(2)
            # The rest of the line after the code is often the start of the label
            rest = line[m.end():].strip()
            current_label = rest
            current_buf = [line.rstrip()]
            continue
        if current_section and current_field:
            if PAGE_FOOTER_RE.match(line):
                continue
            current_buf.append(line.rstrip("\n"))

    flush()

    return sections

def label_from_re(rx):
    # Pull a friendly section label from the regex pattern
    return rx.pattern.replace("\\s+", " ").replace("\\.", ".").replace("[- ]", "-")

def main():
    sys.path.insert(0, os.path.dirname(__file__))
    from manifest import CDS_MANIFEST
    os.makedirs(OUT_DIR, exist_ok=True)
    summary = {}
    for year, _ in CDS_MANIFEST:
        result = parse_year(year)
        if not result:
            print(f"  [skip] {year}: no text file")
            continue
        out_dir = f"{OUT_DIR}/{year}"
        os.makedirs(out_dir, exist_ok=True)
        with open(f"{out_dir}/blocks.json", "w") as f:
            json.dump(result, f, indent=2)
        nfields = sum(len([k for k in v.keys() if not k.startswith("_")]) for v in result.values())
        summary[year] = nfields
        print(f"  [ok]   {year}: {nfields} field blocks")
    print(f"\nTotal years parsed: {len(summary)}")
    with open(f"{OUT_DIR}/_extraction_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
