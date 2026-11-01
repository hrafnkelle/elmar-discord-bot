# Updating the callsign register

The bot never downloads or parses a PDF. Its only register input is `data/callsigns.json`. PDF formats can change, so updates are a reviewed task, optionally performed with Codex.

## Update procedure

1. Visit https://www.ira.is/kallmerki/ and follow the current kallmerkjaskrá link. Check the date printed in the document, rather than assuming the download date is the register date.
2. Ask Codex to inspect the PDF and update the JSON using this schema. Include all listed suffixes, including one-letter and special entries, even though they must not be suggested. Occupancy is independent of digit. Include placeholder prefixes such as `TFn` and `TF#`.
3. Review every page, annotations, and the diff against the previous register. Resolve extraction artifacts and investigate removed suffixes before accepting the update. Cross-check counts and the first/last entries of each column and page. Text extraction alone can merge column headings into suffixes.
4. Update `register_date`, `source_url`, `source_sha256`, `reviewed_on`, and review notes. Check ÍRA's guidance for special exclusions too. Keep `occupied_suffixes` sorted and unique. Do not use an empty or partial list.
5. Run `.venv/bin/pytest`. Review and update source-specific regression cases when the register genuinely changes. Tests cannot prove that a PDF was transcribed completely.
6. Commit the reviewed JSON and recreate the container: `docker compose up -d --force-recreate elmar`. Test `/kallmerki athuga vidskeyti:IRA` and an unlisted suffix in Discord. Retain the old JSON in Git for rollback.

Suggested Codex request:

> Inspect the current ÍRA callsign guidance and linked PDF. Update data/callsigns.json manually for this bot. Follow docs/register-updates.md, review every page and all unusual prefixes/annotations, report additions and removals, and run the tests. Do not add an automated PDF importer.

## JSON schema (version 1)

```json
{
  "schema_version": 1,
  "register_date": "2025-11-02",
  "source_url": "https://www.ira.is/path/to/register.pdf",
  "occupied_suffixes": ["A", "AA", "IRA"],
  "excluded_suffixes": ["WARD", "YOTA"]
}
```

This example is illustrative, not a complete register. Dates must be ISO dates, the source must use HTTPS on ira.is, and suffixes must be uppercase A–Z with one to four letters. `occupied_suffixes` must be nonempty; both arrays must contain no duplicates. Extra metadata fields are allowed. `excluded_suffixes` identifies known special/reserved suffixes absent from the register; all one- and four-letter suffixes are excluded from ordinary availability automatically.

Invalid or missing input prevents startup. Syntactically valid but incomplete data cannot be detected reliably, which is why review is required. Results always show the register date.

## Initial snapshot

The 2 November 2025 PDF contains 475 rows, representing 442 distinct suffixes. Extracted row counts by page: 94, 95, 73, 53, 90, 53, 17. Two local text extractors agreed on all rows, and all seven pages were visually reviewed. The `TF3 WA*` annotation was normalized to `WA`, which also has an independent row. `TFn`/`TF#` entries are occupied. The source page names WARD and YOTA as special allocations, so they are excluded too.

The page's text as returned by web extraction incorrectly merged some page boundaries (e.g. `DX` with the next heading `E`); the initial JSON uses the actual downloaded PDF text instead. Do not copy a web extraction without checking it against the PDF.
