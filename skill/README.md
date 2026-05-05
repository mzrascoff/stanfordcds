# cds-extractor — a Claude skill

Extract structured CSV/JSON from any U.S. university's Common Data Set PDFs.
The CDS uses a standardized template across institutions, so this skill works
for Stanford, Princeton, Harvard, MIT, public flagships, liberal arts colleges
— anyone who publishes one.

See [SKILL.md](./SKILL.md) for the full instructions Claude follows when
invoked. The TL;DR for human users:

```bash
# 1. Edit scripts/manifest.py to list the PDFs you want
# 2. Run the pipeline
bash scripts/run_all.sh
# 3. Find your results in data/csv/ and data/json/
```

Reference manifests for a few institutions live in `references/example-manifests/`.

## Reference implementation

This skill is a generalization of the Stanford CDS open-data repo at
<https://github.com/mzrascoff/stanfordcds>, which ingests 18 years (2008-09
through 2025-26) of Stanford CDSes with 100% spot-check validation.
