# Updating the callsign register

The bot never downloads or parses a PDF. Its only register input is `data/callsigns.json`. These instructions are for the agent performing a requested data update. Inspect each new PDF's actual format; use temporary extraction tools as needed, without adding a maintained importer or automatic refresh to the bot.

## Update procedure

1. **Discover the source.** Open https://www.ira.is/kallmerki/ and follow its current kallmerkjaskrá link rather than reusing the JSON's old PDF URL. Download the PDF into temporary storage and verify it opens as a PDF. Record the source URL, SHA-256 of the downloaded bytes, and date printed in the document. The document date is `register_date`; today's date is `reviewed_on`.
2. **Transcribe all pages.** Preserve the existing JSON while preparing a candidate. Extract the complete list and inspect rendered pages, including every column, annotation, and page boundary. Account for every source row; record per-page row counts and the total distinct suffix count. If the source cannot be fetched or a row remains ambiguous, report the specific blocker and retain the existing register.
3. **Normalize suffixes.** Strip the TF prefix and digit or placeholder, uppercase the suffix, and deduplicate across digits. Include all listed suffixes, including one-letter and special entries. Treat placeholder prefixes such as `TFn` and `TF#` as occupied. Resolve annotations visually: for example, the initial PDF's `WA*` means the suffix `WA`. Follow the current document's evidence rather than assuming future annotations mean the same thing.
4. **Reconcile the candidate.** Compare old and new occupied/excluded sets. Recheck every removal against the source, since a missed column can falsely free an occupied suffix. Verify additions and column/page boundaries against rendered pages. Read the current guidance for special exclusions and update `excluded_suffixes` from that evidence. Preserve known exclusions unless the new source justifies changing them. Finish this step only when every row and every removal is accounted for.
5. **Write and validate.** Write sorted, unique arrays and update provenance fields and review notes in `data/callsigns.json`. Keep the schema below. Run `.venv/bin/pytest` (install the development environment using the README if needed). Change source-specific regression expectations only when the new source establishes the change. Inspect `git diff --check` and the JSON diff. Tests cannot prove that a PDF was transcribed completely; source review remains required.
6. **Report the result.** State the register date, PDF URL, row counts, distinct suffix count, added/removed suffixes, exclusion changes, and checks run. If the source is unchanged, report that rather than manufacturing a data change. Keep PDFs and extraction tools out of the repository. Commit or deploy only when requested by the user or included in the current task's scope.

The update is complete when the JSON loads through `Registry.load`, all source rows and removals are reconciled, tests pass, and the result report includes provenance and changes. Report any incomplete verification explicitly.

## Applying an update to a running bot

After a validated update, recreate the container when deployment is requested:

```sh
docker compose up -d --force-recreate elmar
```

Check logs for successful command registration. A manual Discord check can use `/kallmerki athuga vidskeyti:IRA` and a suffix verified as unlisted in the new snapshot. State whether in-server checks were actually performed. Retain the previous JSON in Git for rollback.

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
