"""
Spot-check extracted CSV values against the source CDS text.
Smarter version: for computed totals, validates against by-sex breakdown.
For ratios, allows both "X:Y" and "X to Y" formats. Writes results to
docs/VALIDATION.md.
"""
import csv, os, random, re, sys
from datetime import date

ROOT = "/sessions/compassionate-sleepy-fermat/mnt/outputs/stanford-cds-open"
TXT_DIR = f"{ROOT}/raw_text"
CSV_DIR = f"{ROOT}/data/csv"

random.seed(20260504)

def load_csv(name):
    return list(csv.DictReader(open(f"{CSV_DIR}/{name}")))

def text_for_year(year):
    return open(f"{TXT_DIR}/stanford-cds-{year}.txt").read()

def value_in_text(value, text, value_kind="number"):
    if value in (None, "", "None"): return False, "empty"
    s = str(value).strip()

    if value_kind == "ratio":
        # Allow "X:1" or "X to 1" or "X-to-1"
        m = re.match(r"^(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)$", s)
        if m:
            a, b = m.group(1), m.group(2)
            # Try literal seps first
            for sep in [" to ", " to-", "-to-", ":", " : "]:
                if f"{a}{sep}{b}" in text:
                    return True, f"matched as '{a}{sep}{b}'"
            # Then allow flexible whitespace
            import re as _re
            if _re.search(rf"\b{_re.escape(a)}\s+to\s+{_re.escape(b)}\b", text):
                return True, f"matched as '{a} (whitespace) to (whitespace) {b}'"
        return False, "ratio not found"

    if s.endswith(".0"):
        s = s[:-2]
    candidates = [s]
    try:
        n = float(s)
        if n.is_integer():
            ni = int(n)
            candidates.append(f"{ni:,}")
    except ValueError:
        pass
    if "." in s:
        candidates.append(s.rstrip("0").rstrip("."))
    for c in candidates:
        if c and c in text:
            return True, f"matched as '{c}'"
    return False, "not found"

def admissions_total_check(row, year):
    """For an admissions_summary row (a computed total), validate by re-summing
    the per-sex breakdown from admissions_by_sex.csv."""
    metric = row["metric"]
    expected = int(row["value"])
    by_sex = load_csv("admissions_by_sex.csv")
    parts = [int(r["value"]) for r in by_sex
             if r["year"] == year and r["metric"] == metric and r["value"]]
    if not parts:
        return False, "no per-sex parts found"
    actual = sum(parts)
    if actual == expected:
        return True, f"sum of {len(parts)} per-sex values = {actual}"
    return False, f"sum mismatch: expected {expected}, got {actual}"

def random_checks(rows, year_col, value_col, n, dataset_label, value_kind="number",
                  totals_check=None):
    checks = []
    rows = [r for r in rows if r.get(value_col, "").strip()]
    sample = random.sample(rows, min(n, len(rows)))
    for r in sample:
        year = r[year_col]
        v = r[value_col]
        if totals_check:
            ok, why = totals_check(r, year)
        else:
            text = text_for_year(year)
            ok, why = value_in_text(v, text, value_kind)
        checks.append({
            "dataset": dataset_label, "year": year,
            "row": {k: r[k] for k in r if k != value_col},
            "value": v,
            "found": ok,
            "evidence": why,
        })
    return checks

def main():
    out_lines = ["# Validation: spot-checks against source PDFs\n",
                 f"_Last run: {date.today()}_\n",
                 "",
                 "Each dataset is sampled at random and the extracted value is "
                 "checked against the source PDF text. For computed totals "
                 "(e.g. admissions_summary), the validation re-sums the per-sex "
                 "breakdown rather than searching for the total verbatim "
                 "(Stanford's PDFs publish the per-sex parts, not the total).\n"]

    all_checks = []
    all_checks += random_checks(load_csv("admissions_summary.csv"),
                                "year", "value", 3, "admissions",
                                totals_check=admissions_total_check)
    all_checks += random_checks(load_csv("admissions_by_sex.csv"),
                                "year", "value", 3, "admissions_by_sex")
    all_checks += random_checks(load_csv("test_scores.csv"),
                                "year", "p50", 3, "test_scores")
    all_checks += random_checks(load_csv("tuition_and_fees.csv"),
                                "year", "amount", 3, "tuition")
    all_checks += random_checks(load_csv("graduation_rates.csv"),
                                "year", "value", 3, "graduation")
    fac = [r for r in load_csv("faculty_summary.csv") if r["value"].strip()]
    fac_ratio = [r for r in fac if r["metric"] == "student_faculty_ratio"]
    fac_count = [r for r in fac if r["metric"] == "total_instructional_faculty"]
    all_checks += random_checks(fac_ratio, "year", "value", 2, "faculty_ratio",
                                value_kind="ratio")
    all_checks += random_checks(fac_count, "year", "value", 2, "faculty_count")

    n_pass = sum(1 for c in all_checks if c["found"])
    out_lines.append("## Random spot-checks (19 values)\n")
    out_lines.append("| Dataset | Year | Field | Value | Result | Evidence |")
    out_lines.append("| --- | --- | --- | --- | --- | --- |")
    for c in all_checks:
        details = ", ".join(f"{k}={v}" for k, v in c["row"].items() if k != "year")
        marker = "PASS" if c["found"] else "FAIL"
        out_lines.append(
            f"| {c['dataset']} | {c['year']} | {details} | {c['value']} | {marker} | {c['evidence']} |"
        )
    out_lines.append("")
    pct = n_pass*100//len(all_checks)
    out_lines.append(f"**Pass rate: {n_pass}/{len(all_checks)} = {pct}%**")
    out_lines.append("")
    if n_pass < len(all_checks):
        out_lines.append("Any FAIL warrants a manual look. Common reasons a value can "
                         "FAIL despite being correct: the value appears in the PDF in a "
                         "less-common formatting (e.g. spelled-out percentages, decimals "
                         "instead of percent), or it spans multiple lines that the "
                         "validation scan didn't stitch back together.")
    with open(f"{ROOT}/docs/VALIDATION.md", "w") as f:
        f.write("\n".join(out_lines))
    print(open(f"{ROOT}/docs/VALIDATION.md").read())

if __name__ == "__main__":
    main()
