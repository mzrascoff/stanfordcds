# Validation: spot-checks against source PDFs

_Last run: 2026-05-04_


Each dataset is sampled at random and the extracted value is checked against the source PDF text. For computed totals (e.g. admissions_summary), the validation re-sums the per-sex breakdown rather than searching for the total verbatim (Stanford's PDFs publish the per-sex parts, not the total).

## Random spot-checks (19 values)

| Dataset | Year | Field | Value | Result | Evidence |
| --- | --- | --- | --- | --- | --- |
| admissions | 2021-2022 | metric=admitted | 2190 | PASS | sum of 2 per-sex values = 2190 |
| admissions | 2020-2021 | metric=applied | 45227 | PASS | sum of 2 per-sex values = 45227 |
| admissions | 2018-2019 | metric=applied | 47452 | PASS | sum of 2 per-sex values = 47452 |
| admissions_by_sex | 2014-2015 | metric=enrolled, sex=male | 857 | PASS | matched as '857' |
| admissions_by_sex | 2012-2013 | metric=admitted, sex=male | 1306 | PASS | matched as '1,306' |
| admissions_by_sex | 2018-2019 | metric=applied, sex=female | 22760 | PASS | matched as '22760' |
| test_scores | 2021-2022 | test=pct_submitted_SAT, p25=, p75= | 48 | PASS | matched as '48' |
| test_scores | 2024-2025 | test=ACT_science, p25=33, p75=36 | 35 | PASS | matched as '35' |
| test_scores | 2022-2023 | test=ACT_composite, p25=33, p75=35 | 35 | PASS | matched as '35' |
| tuition | 2024-2025 | expense=required_fees | 813 | PASS | matched as '813' |
| tuition | 2009-2010 | expense=board_only | 4338 | PASS | matched as '4,338' |
| tuition | 2022-2023 | expense=board_only | 7325 | PASS | matched as '7,325' |
| graduation | 2016-2017 | metric=freshman_retention_rate_pct | 98.0 | PASS | matched as '98' |
| graduation | 2010-2011 | metric=rate_6yr_pct | 95.0 | PASS | matched as '95' |
| graduation | 2009-2010 | metric=freshman_retention_rate_pct | 98.0 | PASS | matched as '98' |
| faculty_ratio | 2024-2025 | metric=student_faculty_ratio | 6:1 | PASS | matched as '6 (whitespace) to (whitespace) 1' |
| faculty_ratio | 2012-2013 | metric=student_faculty_ratio | 5:1 | PASS | matched as '5 to 1' |
| faculty_count | 2010-2011 | metric=total_instructional_faculty | 1014 | PASS | matched as '1014' |
| faculty_count | 2020-2021 | metric=total_instructional_faculty | 2342 | PASS | matched as '2342' |

**Pass rate: 19/19 = 100%**
