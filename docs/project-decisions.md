# Project decisions

## Confirmed intent

- Serve the Elmar Discord community, especially newly licensed amateur radio operators.
- Prefer Python; consider frameworks or an extensible open source bot.
- First release: check suffix availability and suggest random available callsigns.
- Later: additional commands and monitoring/reporting of amateur radio topics and events.
- Keep this project in a local Git repository, eventually hosted on the owner's GitHub.

## Source findings

Checked on 2026-11-01:

- [ÍRA callsign guidance](https://www.ira.is/kallmerki/) links to the [register dated 2 November 2025](https://www.ira.is/wp-content/uploads/2025/11/2_NOV_2025_TF_kallmerki.pdf).
- The page says an unlisted callsign is generally available for allocation, with possible errors. Fjarskiptastofa issues callsigns; absence from this register is not a guaranteed allocation.
- Suffix occupancy applies across digits: an existing IRA suffix rules it out irrespective of the chosen digit.
- Ordinary suffixes contain two or three letters. Single-letter suffixes are generally not allocated; some four-letter suffixes are special allocations.
- The page says TF0 is traditionally not allocated.
- The PDF includes unusual entries such as `TFn FOX`, `TF# GU`, and `TFn JAM`; transcription must include these rather than silently mark their suffixes available.

## Decision tree — interview in progress

### Round 1: open decisions

1. Initial scope: Icelandic TF callsigns only, with future monitoring deferred?
2. Availability meaning: report listed / not listed, with register date and source, rather than promise allocation?
3. Interaction: Discord slash commands accepting a suffix or complete callsign, with suggestions returning suffixes until a digit is selected?
4. Language: Icelandic by default, with English available?
5. Deployment constraints: self-hosted always-running process, or an existing preferred host?

### Round 1 answers

- Icelandic TF callsigns only for the first release.
- User requests the wording “not available”; interpreting this as the occupied case, with unlisted-case wording awaiting clarification.
- Slash command mechanism explained: bots register their own Discord slash commands; a different prefix is unnecessary. Exact command names remain open.
- Exclude single-letter suffixes and special allocations from random suggestions.
- Icelandic default, English option.
- Deploy to the owner's existing server using Docker Compose.

### Framework findings

Both discord.py and Red DiscordBot support slash commands and modular extensions. discord.py also supplies background task loops for future monitoring. A focused custom bot using discord.py is recommended; Red is an alternative if existing general community features are needed.

Primary sources:

- https://discordpy.readthedocs.io/en/stable/interactions/api.html
- https://discordpy.readthedocs.io/en/stable/ext/commands/extensions.html
- https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html
- https://github.com/Cog-Creators/Red-DiscordBot
- https://docs.discord.red/en/stable/framework_tree.html

### Round 2: open decisions

1. Confirm occupied/unlisted result wording.
2. Choose discord.py versus extending a general-purpose bot.
3. Agree refresh and outage behavior for the source register.
4. Choose command names and public/private response defaults.

### Final decisions — approved through rounds 2 and 3

- Use Python and discord.py, with Docker Compose on the owner's server.
- Listed suffixes reply “Ekki laust”. Unlisted ordinary suffixes reply “Virðist laust samkvæmt kallmerkjaskrá ÍRA”, with register date/source and allocation confirmation wording.
- Use `/kallmerki athuga` and `/kallmerki velja`; accept suffixes or full TF callsigns for checks.
- Replies are private to the invoking user. Icelandic is default; `tungumal:English` switches the reply language.
- Random suggestions are uniformly selected unlisted A–Z suffixes, defaulting to three letters, optionally two. Exclude one-letter suffixes and special allocations. Return suffixes without a digit.
- The bot reads JSON mounted read-only at startup. Update the file and recreate the container to reload it.
- No automatic refresh and no maintained PDF conversion script. Ask Codex to inspect and transcribe future PDFs, with manual review.
- Include initial JSON, implementation, tests, Compose configuration, and setup/update documentation. User approved building this deliverable in Q15 and confirmed the remaining choices.

The interview is complete. Future monitoring features remain outside this release.
