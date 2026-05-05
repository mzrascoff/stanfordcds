"""
Stage-2 parser: extract clean numeric values from the high-value standardized
tables and write long-format CSVs.

Inputs:  data/json/<year>/blocks.json   (from parse_blocks.py)
         raw_text/stanford-cds-<year>.txt   (raw layout text, used as fallback)
Outputs: data/csv/*.csv
"""
import csv, json, os, re, sys

ROOT = "/sessions/compassionate-sleepy-fermat/mnt/outputs/stanford-cds-open"
JSON_DIR = f"{ROOT}/data/json"
TXT_DIR = f"{ROOT}/raw_text"
CSV_DIR = f"{ROOT}/data/csv"
os.makedirs(CSV_DIR, exist_ok=True)

NUM_RE = re.compile(r"\(?\$?-?\d[\d,]*(?:\.\d+)?%?\)?")

def clean_num(s):
    if s is None: return None
    s = str(s).strip().rstrip(":").rstrip(".")
    if not s or s == "-": return None
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    s = s.replace(",", "").replace("$", "").replace("%", "")
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return None

def first_num_after(s):
    m = NUM_RE.search(s)
    return clean_num(m.group(0)) if m else None

def get_block(blocks, section, field):
    return blocks.get(section, {}).get(field, {}).get("raw_text", "")

def get_section_text(year, section):
    """Return the raw text of an entire section by reading the layout txt file."""
    path = f"{TXT_DIR}/stanford-cds-{year}.txt"
    if not os.path.exists(path): return ""
    text = open(path).read()
    section_starts = [
        ("A", r"^[ \t]*A\.\s+General\s+Information\b"),
        ("B", r"^[ \t]*B\.\s+ENROLLMENT\s+AND\s+PERSISTENCE\b"),
        ("C", r"^[ \t]*C\.\s+FIRST[- ]?TIME"),
        ("D", r"^[ \t]*D\.\s+TRANSFER"),
        ("E", r"^[ \t]*E\.\s+ACADEMIC"),
        ("F", r"^[ \t]*F\.\s+STUDENT\s+LIFE"),
        ("G", r"^[ \t]*G\.\s+ANNUAL"),
        ("H", r"^[ \t]*H\.\s+FINANCIAL\s+AID"),
        ("I", r"^[ \t]*I\.\s+INSTRUCTIONAL"),
        ("J", r"^[ \t]*J\.\s+DEGREES"),
    ]
    sec_idx = next((i for i, (s, _) in enumerate(section_starts) if s == section), None)
    if sec_idx is None: return ""
    start_re = re.compile(section_starts[sec_idx][1], re.I | re.M)
    end_re = re.compile(section_starts[sec_idx + 1][1], re.I | re.M) if sec_idx + 1 < len(section_starts) else None

    # Skip the first occurrence (TOC) - find the second
    matches = list(start_re.finditer(text))
    if not matches: return ""
    # Find the first match that doesn't have heavy dots (TOC)
    real_starts = [m for m in matches if "..." not in text[m.start():m.start()+200]]
    if not real_starts: return ""
    s = real_starts[0].start()
    if end_re:
        end_matches = [m for m in end_re.finditer(text) if m.start() > s and "..." not in text[m.start():m.start()+200]]
        e = end_matches[0].start() if end_matches else len(text)
    else:
        e = len(text)
    return text[s:e]

# ------------------- Extractors -------------------

def admissions_summary(year, blocks):
    """C1 applications summary: applied/admitted/enrolled by sex.

    Newer (2017+) CDSes have BOTH a top-line "Total ... who enrolled" row and
    sub-rows split by full-time/part-time. Older (pre-2017) CDSes ONLY have
    the full-time / part-time split. Strategy: prefer the top-line if present,
    otherwise sum FT + PT for that sex.
    """
    text = get_block(blocks, "C", "C1") or get_section_text(year, "C")
    rows = []
    if not text: return rows
    lines = text.split("\n")

    # Helper: find numeric value AFTER the action verb (avoid catching "C1"
    # prefix or other line noise).
    def get_value(line, action_pat):
        # Strip any leading field-code prefix like "C1" / "H1"
        m = re.search(action_pat, line, re.I)
        if not m: return None
        after = line[m.end():]
        if ":" in after:
            after = after.split(":", 1)[-1]
        return first_num_after(after)

    sex_pats = {
        "male":   [r"\bmen\b", r"\bmales?\b"],
        "female": [r"\bwomen\b", r"\bfemales?\b"],
        "unknown": [r"unknown sex"],
    }

    # applied + admitted: simple - look for line with action+sex
    for action, action_pat in [("applied", r"who applied"), ("admitted", r"who were admitted")]:
        for sex_label, pats in sex_pats.items():
            for line in lines:
                if not re.search(action_pat, line, re.I): continue
                if not any(re.search(p, line, re.I) for p in pats): continue
                v = get_value(line, action_pat)
                if v is not None:
                    rows.append({"year": year, "metric": action, "sex": sex_label, "value": v})
                    break

    # enrolled: prefer the non-FT/PT total line; if not found, sum FT+PT
    for sex_label, pats in sex_pats.items():
        # Try top-line first (no full-time/part-time qualifier)
        toplevel = None
        for line in lines:
            if not re.search(r"who enrolled", line, re.I): continue
            if not any(re.search(p, line, re.I) for p in pats): continue
            if re.search(r"\b(?:full|part)[-\s]?time\b", line, re.I): continue
            v = get_value(line, r"who enrolled")
            if v is not None:
                toplevel = v
                break
        if toplevel is not None:
            rows.append({"year": year, "metric": "enrolled", "sex": sex_label, "value": toplevel})
            continue
        # Fallback: sum FT + PT
        ft, pt = None, None
        for line in lines:
            if not re.search(r"who enrolled", line, re.I): continue
            if not any(re.search(p, line, re.I) for p in pats): continue
            if re.search(r"\bfull[-\s]?time\b", line, re.I) and ft is None:
                ft = get_value(line, r"who enrolled")
            elif re.search(r"\bpart[-\s]?time\b", line, re.I) and pt is None:
                pt = get_value(line, r"who enrolled")
        if ft is not None or pt is not None:
            rows.append({"year": year, "metric": "enrolled", "sex": sex_label,
                         "value": (ft or 0) + (pt or 0)})

    # FALLBACK: 2023-2024 layout has "students who applied/admitted/enrolled"
    # with men + women + another-gender values in columns on the same line.
    if not rows:
        column_actions = [
            ("applied", r"Total first[-\s]+time,?\s+first[-\s]+year\s+students\s+who\s+applied"),
            ("admitted", r"Total first[-\s]+time,?\s+first[-\s]+year\s+students\s+(?:admitted|who were admitted)"),
            ("enrolled", r"^\s*Total first[-\s]+time,?\s+first[-\s]+year\s+students\s+(?:enrolled|who enrolled)"),
        ]
        for action, pat in column_actions:
            for line in lines:
                m = re.search(pat, line, re.I)
                if not m: continue
                if action == "enrolled" and re.search(r"\b(?:Full|Part)[-\s]?time", line, re.I):
                    continue
                rest = line[m.end():]
                # Strip the "in Fall YYYY" / "Fall YYYY" prefix that contains
                # a 4-digit year we must not capture as the male count.
                rest = re.sub(r"^\s*(?:in\s+)?Fall\s+\d{4}", "", rest, flags=re.I)
                nums = NUM_RE.findall(rest)
                if len(nums) >= 2:
                    rows.append({"year": year, "metric": action, "sex": "male",
                                 "value": clean_num(nums[0])})
                    rows.append({"year": year, "metric": action, "sex": "female",
                                 "value": clean_num(nums[1])})
                    if len(nums) >= 3:
                        rows.append({"year": year, "metric": action, "sex": "unknown",
                                     "value": clean_num(nums[2])})
                    break

    # Dedupe (year, metric, sex)
    seen = set(); out = []
    for r in rows:
        k = (r["year"], r["metric"], r["sex"])
        if k in seen: continue
        seen.add(k); out.append(r)
    return out

def admissions_totals(year, blocks):
    """Computed totals by year - sum of male+female+unknown for applied/admitted/enrolled."""
    rows = admissions_summary(year, blocks)
    totals = {}
    for r in rows:
        totals.setdefault(r["metric"], 0)
        if r["value"] is not None:
            totals[r["metric"]] += r["value"]
    return [{"year": year, "metric": k, "value": v} for k, v in totals.items() if v]

def test_scores(year, blocks):
    """C9 SAT/ACT score percentiles + submission rates."""
    text = get_block(blocks, "C", "C9") or get_section_text(year, "C")
    rows = []
    if not text: return rows
    test_labels = [
        ("SAT Composite", "SAT_total"),
        ("SAT Evidence-Based Reading", "SAT_EBRW"),
        ("SAT Math", "SAT_math"),
        ("SAT Critical Reading", "SAT_CR"),
        ("SAT Writing", "SAT_writing"),
        ("ACT Composite", "ACT_composite"),
        ("ACT English", "ACT_english"),
        ("ACT Math", "ACT_math"),
        ("ACT Reading", "ACT_reading"),
        ("ACT Science", "ACT_science"),
        ("ACT Writing", "ACT_writing"),
    ]
    for label_pat, key in test_labels:
        for line in text.split("\n"):
            if re.search(label_pat, line, re.I):
                # Skip description lines
                if "test scores" in line.lower() and "policy" in line.lower(): continue
                rest = line[re.search(label_pat, line, re.I).end():]
                nums = NUM_RE.findall(rest)
                # Filter out numbers that are obviously percentages
                clean_nums = [n for n in nums if not n.endswith("%")]
                if len(clean_nums) >= 3:
                    rows.append({"year": year, "test": key,
                                 "p25": clean_num(clean_nums[0]),
                                 "p50": clean_num(clean_nums[1]),
                                 "p75": clean_num(clean_nums[2])})
                    break
                elif len(clean_nums) == 2:
                    rows.append({"year": year, "test": key,
                                 "p25": clean_num(clean_nums[0]), "p50": None,
                                 "p75": clean_num(clean_nums[1])})
                    break
    # Submission percentages
    for label_pat, key in [
        (r"submitting\s+SAT\s+scores", "pct_submitted_SAT"),
        (r"submitting\s+ACT\s+scores", "pct_submitted_ACT"),
    ]:
        for line in text.split("\n"):
            if re.search(label_pat, line, re.I):
                v = first_num_after(line[re.search(label_pat, line, re.I).end():])
                if v is not None:
                    rows.append({"year": year, "test": key,
                                 "p25": None, "p50": v, "p75": None})
                    break
    # Dedupe
    seen = set(); out = []
    for r in rows:
        if r["test"] in seen: continue
        seen.add(r["test"]); out.append(r)
    return out

def enrollment_summary(year, blocks):
    """B1: full-time/part-time enrollment by level + sex."""
    text = get_block(blocks, "B", "B1") or get_section_text(year, "B")
    rows = []
    if not text: return rows
    items = [
        ("undergrad_FT_total", r"Total Undergraduate Full[- ]?Time\s+Students"),
        ("undergrad_PT_total", r"Total Undergraduate Part[- ]?Time\s+Students"),
        ("undergrad_total", r"Total Undergraduate Students"),
        ("graduate_FT_total", r"Total Graduate Full[- ]?Time\s+Students"),
        ("graduate_PT_total", r"Total Graduate Part[- ]?Time\s+Students"),
        ("graduate_total", r"Total Graduate Students"),
        ("total_FT_students", r"^\s*Total Full[- ]?Time\s+Students"),
        ("total_PT_students", r"^\s*Total Part[- ]?Time\s+Students"),
        ("total_undergraduates", r"Total\s+all\s+undergraduates"),
        ("total_graduate", r"Total\s+all\s+graduate"),
        ("grand_total", r"GRAND TOTAL ALL STUDENTS"),
        ("FT_first_time_first_year", r"Degree[- ]?seeking,\s+first[- ]?time\s+first[- ]?year\s+students"),
    ]
    for key, pat in items:
        for line in text.split("\n"):
            m = re.search(pat, line, re.I)
            if m:
                nums = NUM_RE.findall(line[m.end():])
                if not nums: continue
                male = clean_num(nums[0]) if len(nums) >= 1 else None
                female = clean_num(nums[1]) if len(nums) >= 2 else None
                unk = clean_num(nums[2]) if len(nums) >= 3 else None
                rows.append({"year": year, "category": key,
                             "male": male, "female": female, "unknown": unk})
                break
    # Dedupe
    seen = set(); out = []
    for r in rows:
        if r["category"] in seen: continue
        seen.add(r["category"]); out.append(r)
    return out

def tuition_and_fees(year, blocks):
    """G section: tuition, fees, room and board, food/housing.

    The G1 cost-of-attendance table looks roughly like:
        Tuition:               $67,731     $67,731
        Required Fees:           $843        $843
        Food and housing:     $22,944     $22,944
        ...
    The first dollar amount is "first-year" cost, second is "all undergrads".
    We capture the first ($-prefixed) value per row.
    """
    text = get_section_text(year, "G")
    if not text: return []
    rows = []
    # Match a label that starts the line (after whitespace), optionally with colon,
    # followed by at least one $-amount.
    items = [
        ("tuition_first_year",          r"^[ \t]*Tuition\s*:?\s*\$"),
        ("tuition_in_state",            r"^[ \t]*Tuition[: ]\s*[Ii]n[-\s]?state\s*:?\s*\$"),
        ("tuition_out_of_state",        r"^[ \t]*Tuition[: ]\s*[Oo]ut[-\s]?of[-\s]?state\s*:?\s*\$"),
        ("tuition_nonresident",         r"^[ \t]*Tuition[: ]\s*[Nn]onresident\s*:?\s*\$"),
        ("required_fees",               r"^[ \t]*Required\s+[Ff]ees\s*:?\s*\$"),
        ("room_only",                   r"^[ \t]*Room\s+[Oo]nly\s*:?\s*\$"),
        ("board_only",                  r"^[ \t]*Board\s+[Oo]nly\s*:?\s*\$"),
        ("room_and_board",              r"^[ \t]*Room\s+and\s+[Bb]oard\s*:?\s*\$"),
        ("food_and_housing",            r"^[ \t]*Food\s+and\s+housing\b"),
        ("housing_only",                r"^[ \t]*Housing\s+[Oo]nly\b"),
        ("food_only",                   r"^[ \t]*Food\s+[Oo]nly\b"),
        ("books_supplies",              r"^[ \t]*Books\s+and\s+supplies\s*:?"),
        ("transportation",              r"^[ \t]*Transportation\s*:?"),
        ("other_expenses",              r"^[ \t]*Other\s+expenses\s*:?"),
    ]
    for key, pat in items:
        for line in text.split("\n"):
            m = re.search(pat, line, re.I | re.M)
            if not m: continue
            # Find first dollar-prefixed number on the line
            md = re.search(r"\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", line)
            if md:
                v = clean_num(md.group(1))
                if v is not None and v >= 1:
                    rows.append({"year": year, "expense": key, "amount": v})
                    break
            # Fallback: any large number on the line
            v = first_num_after(line[m.end():])
            if v is not None and v > 100:
                rows.append({"year": year, "expense": key, "amount": v})
                break
    # Dedupe
    seen = set(); out = []
    for r in rows:
        if r["expense"] in seen: continue
        seen.add(r["expense"]); out.append(r)
    return out

def financial_aid_summary(year, blocks):
    """H section headline metrics. Stick to the metrics that have a label
    immediately followed by a single value on the same (or next) line.

    For the complex H1/H2 multi-column tables we keep the raw text in the
    blocks JSON. Curating those into clean columns is left to a downstream
    pass — see docs/EXTRACTION_NOTES.md.
    """
    text = get_section_text(year, "H")
    if not text: return []
    lines = text.split("\n")
    rows = []

    def find_value_after_label(pat, lookahead=2, want_pct=False):
        for i, line in enumerate(lines):
            m = re.search(pat, line, re.I)
            if not m: continue
            for j in range(i, min(i + 1 + lookahead, len(lines))):
                ln = lines[j] if j > i else lines[j][m.end():]
                if want_pct:
                    pm = re.search(r"(\d+(?:\.\d+)?)\s*%", ln)
                    if pm:
                        return float(pm.group(1))
                else:
                    v = first_num_after(ln)
                    if v is not None:
                        return v
            return None
        return None

    # Avg need-based grant award (typically column F or K of H2 row labeled "Average need-based scholarship/grant")
    v = find_value_after_label(r"Average\s+need-based\s+scholarship\s+(?:and|or|/)?\s*grant\s+award", 2)
    if v is not None: rows.append({"year": year, "metric": "avg_need_based_grant_award", "value": v})

    # Avg need-based loan
    v = find_value_after_label(r"Average\s+need-based\s+loan", 2)
    if v is not None: rows.append({"year": year, "metric": "avg_need_based_loan", "value": v})

    # Avg financial aid package
    v = find_value_after_label(r"[Aa]verage\s+(?:financial\s+)?aid\s+package", 2)
    if v is not None: rows.append({"year": year, "metric": "avg_financial_aid_package", "value": v})

    # H4 numbers reaching graduation
    v = find_value_after_label(r"received\s+a\s+bachelor's\s+degree\s+between", 4)
    if v is not None and v > 50:  # exclude tiny artifacts
        rows.append({"year": year, "metric": "num_grads_in_borrowing_cohort", "value": v})

    # Pct of class who borrowed (H4)
    v = find_value_after_label(r"Percent\s+of\s+(?:first[-\s]?year|the\s+class|students\s+in\s+H4).*?(?:who\s+)?borrowed", 4, want_pct=True)
    if v is not None: rows.append({"year": year, "metric": "pct_class_borrowed", "value": v})

    # Avg cumulative debt borrowed - need a stronger pattern that lands on a $ amount
    for i, line in enumerate(lines):
        if not re.search(r"per[-\s]?(?:undergraduate[-\s]?)?borrower\s+cumulative", line, re.I): continue
        for j in range(i, min(i + 6, len(lines))):
            md = re.search(r"\$\s*(\d{1,3}(?:,\d{3})+)", lines[j])
            if md:
                rows.append({"year": year, "metric": "avg_per_borrower_cumulative_debt",
                             "value": clean_num(md.group(1))})
                break
        break

    seen = set(); out = []
    for r in rows:
        if r["metric"] in seen: continue
        seen.add(r["metric"]); out.append(r)
    return out

def faculty_summary(year, blocks):
    """I sections: faculty counts and student-to-faculty ratio."""
    text = get_section_text(year, "I")
    if not text: return []
    rows = []
    # Student-to-faculty ratio is usually written like "5 to 1" or "5:1"
    for line in text.split("\n"):
        m = re.search(r"(?:Student[-\s/]?(?:to[-\s/]?)?[Ff]aculty\s+ratio|fall\s+\d{4}\s+student/faculty\s+ratio)", line, re.I)
        if m:
            rest = line[m.end():]
            m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|:|/)\s*(\d+(?:\.\d+)?)", rest)
            if m2:
                rows.append({"year": year, "metric": "student_faculty_ratio",
                             "value": f"{m2.group(1)}:{m2.group(2)}"})
                break
            v = first_num_after(rest)
            if v is not None:
                rows.append({"year": year, "metric": "student_faculty_ratio", "value": v})
                break

    items = [
        ("total_instructional_faculty",
         r"Total\s+(?:number\s+of\s+)?instructional\s+faculty"),
        ("total_full_time_faculty",
         r"^\s*Total\s+full[-\s]?time\s+(?:instructional\s+)?faculty"),
        ("total_part_time_faculty",
         r"^\s*Total\s+part[-\s]?time\s+(?:instructional\s+)?faculty"),
    ]
    for key, pat in items:
        for line in text.split("\n"):
            m = re.search(pat, line, re.I | re.M)
            if not m: continue
            nums = NUM_RE.findall(line[m.end():])
            if nums:
                # I1 typically has Men/Women columns then Total at end
                v = clean_num(nums[-1])
                if v is not None:
                    rows.append({"year": year, "metric": key, "value": v})
                    break
    # Dedupe
    seen = set(); out = []
    for r in rows:
        if r["metric"] in seen: continue
        seen.add(r["metric"]); out.append(r)
    return out

def graduation_rates(year, blocks):
    """B-section: graduation rates and freshman retention.
    Handles multiple formats: 'X% in same line', 'X%' on next line,
    and decimals (0.9261) which we convert to percent."""
    text = get_section_text(year, "B")
    if not text: return []
    lines = text.split("\n")
    rows = []

    def extract_rate(lines, idx, lookahead=4):
        """Find a percent or decimal-rate value within the next `lookahead` lines."""
        for j in range(idx, min(idx + lookahead, len(lines))):
            ln = lines[j]
            # Percentage form
            m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", ln)
            if m:
                return float(m.group(1))
            # Decimal form e.g. 0.9261 (treat as ratio, convert to pct)
            m = re.search(r"\b0\.(\d{2,})\b", ln)
            if m:
                return round(float("0." + m.group(1)) * 100, 2)
        return None

    grad_labels = [
        (r"(?:Four|4)[-\s]?year\s+(?:completion|graduation)\s+rate", "rate_4yr_pct"),
        (r"(?:Five|5)[-\s]?year\s+(?:completion|graduation)\s+rate", "rate_5yr_pct"),
        (r"(?:Six|6)[-\s]?year\s+(?:completion|graduation)\s+rate", "rate_6yr_pct"),
    ]
    for pat, key in grad_labels:
        for i, line in enumerate(lines):
            if re.search(pat, line, re.I):
                v = extract_rate(lines, i, 4)
                if v is not None:
                    rows.append({"year": year, "metric": key, "value": v})
                    break

    # Freshman retention rate (B22)
    for i, line in enumerate(lines):
        if re.search(r"B22\b.*[Rr]etention", line) or re.search(r"^[ \t]*B22\b", line):
            v = extract_rate(lines, i, 12)
            if v is not None:
                rows.append({"year": year, "metric": "freshman_retention_rate_pct", "value": v})
                break

    seen = set(); out = []
    for r in rows:
        if r["metric"] in seen: continue
        seen.add(r["metric"]); out.append(r)
    return out

def all_fields_long(year, blocks):
    rows = []
    for sec, fields in blocks.items():
        if not isinstance(fields, dict): continue
        for fid, payload in fields.items():
            if fid.startswith("_"): continue
            if not isinstance(payload, dict): continue
            text = payload.get("raw_text", "").strip()
            label = payload.get("label", "")
            preview = re.sub(r"\s+", " ", text.replace("\n", " "))[:300]
            rows.append({"year": year, "section": sec, "field": fid,
                         "label": label[:200], "raw_preview": preview})
    return rows


def write_csv(path, rows, fieldnames):
    rows = [r for r in rows if r]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return len(rows)


def main():
    sys.path.insert(0, os.path.dirname(__file__))
    from manifest import CDS_MANIFEST

    all_admissions, all_admissions_totals = [], []
    all_tests, all_enroll = [], []
    all_tuition, all_aid, all_faculty, all_grad, all_long = [], [], [], [], []

    for year, _ in CDS_MANIFEST:
        bp = f"{JSON_DIR}/{year}/blocks.json"
        if not os.path.exists(bp): continue
        blocks = json.load(open(bp))

        adm = admissions_summary(year, blocks)
        all_admissions += adm
        all_admissions_totals += admissions_totals(year, blocks)
        all_tests += test_scores(year, blocks)
        all_enroll += enrollment_summary(year, blocks)
        all_tuition += tuition_and_fees(year, blocks)
        all_aid += financial_aid_summary(year, blocks)
        all_faculty += faculty_summary(year, blocks)
        all_grad += graduation_rates(year, blocks)
        all_long += all_fields_long(year, blocks)

    n_adm = write_csv(f"{CSV_DIR}/admissions_by_sex.csv", all_admissions,
                      ["year", "metric", "sex", "value"])
    n_at = write_csv(f"{CSV_DIR}/admissions_summary.csv", all_admissions_totals,
                     ["year", "metric", "value"])
    n_ts = write_csv(f"{CSV_DIR}/test_scores.csv", all_tests,
                     ["year", "test", "p25", "p50", "p75"])
    n_en = write_csv(f"{CSV_DIR}/enrollment_summary.csv", all_enroll,
                     ["year", "category", "male", "female", "unknown"])
    n_tu = write_csv(f"{CSV_DIR}/tuition_and_fees.csv", all_tuition,
                     ["year", "expense", "amount"])
    n_fa = write_csv(f"{CSV_DIR}/financial_aid_summary.csv", all_aid,
                     ["year", "metric", "value"])
    n_fc = write_csv(f"{CSV_DIR}/faculty_summary.csv", all_faculty,
                     ["year", "metric", "value"])
    n_gr = write_csv(f"{CSV_DIR}/graduation_rates.csv", all_grad,
                     ["year", "metric", "value"])
    n_lo = write_csv(f"{CSV_DIR}/all_fields_long.csv", all_long,
                     ["year", "section", "field", "label", "raw_preview"])

    print(f"admissions_by_sex.csv:    {n_adm} rows")
    print(f"admissions_summary.csv:   {n_at} rows")
    print(f"test_scores.csv:          {n_ts} rows")
    print(f"enrollment_summary.csv:   {n_en} rows")
    print(f"tuition_and_fees.csv:     {n_tu} rows")
    print(f"financial_aid_summary.csv: {n_fa} rows")
    print(f"faculty_summary.csv:      {n_fc} rows")
    print(f"graduation_rates.csv:     {n_gr} rows")
    print(f"all_fields_long.csv:      {n_lo} rows")

if __name__ == "__main__":
    main()
