# Elmar

A Discord bot for the Elmar amateur radio community, helping newly licensed operators get started.

Elmar is named for the amateur radio tradition of mentoring newly licensed operators.

## Commands

- `/kallmerki athuga vidskeyti:IRA` — check a suffix; `TF3IRA` also works. Occupied suffixes reply **Ekki laust**, regardless of digit.
- `/kallmerki velja` — suggest a random three-letter suffix.
- `/kallmerki velja lengd:2` — suggest a two-letter suffix.
- Both commands accept `tungumal:English`. Replies default to Icelandic and are visible only to the person invoking the command.
- `/kindex nuna` — show the latest published provisional local K-index at Leirvogur, its UTC observation interval, graph and source. This reply is visible only to the requester and also accepts `tungumal:English`. Callsign replies remain private.

Unlisted suffixes reply **Virðist laust samkvæmt kallmerkjaskrá ÍRA**, with the source and register date. Allocation must be confirmed by Fjarskiptastofa. Selection is uniform over unlisted A–Z combinations of the requested length; single-letter and special allocations are excluded. Suggestions contain no digit. TF0 is outside ordinary allocation.

## Run with Docker Compose

1. Create an application and bot in the [Discord Developer Portal](https://discord.com/developers/applications). Copy its bot token.
2. Enable Developer Mode in Discord settings, then right-click the Elmar server and copy its server ID.
3. In the portal's OAuth2 URL Generator, select `bot` and `applications.commands`, then use the generated URL to install the bot into your server. No administrator permission or privileged intents are needed. Ensure members can use application commands in the desired channel.
4. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `DISCORD_GUILD_ID`. Keep the token private; `.env` is ignored by Git.
5. Start the bot:

```sh
docker compose up -d --build
docker compose logs -f elmar
```

The bot registers commands only in the configured server. The callsign JSON is mounted read-only and loaded at startup. No inbound port or runtime access to ÍRA is needed. The server needs outbound HTTPS/WebSocket access to Discord and HTTPS access to `flux.phys.uit.no`. The container runs as UID 10001; ensure the JSON file and its parent directories are readable by it. K-index cache and alert progress are stored in SQLite on the `kindex-state` Docker volume.

To update the register, follow [the manual update guide](docs/register-updates.md), then run `docker compose up -d --force-recreate elmar`. Recreating the container also handles a replaced bind-mounted file correctly.

## Leirvogur K-index alerts

Create a dedicated text channel in the configured server and give Elmar **View Channel** and **Send Messages** there. Copy its channel ID into `.env`:

```dotenv
ELMAR_K_CHANNEL_ID=your_channel_id
ELMAR_K_THRESHOLD=5
```

Then rebuild/recreate with `docker compose up -d --build`. The channel ID is optional: leaving it empty disables automatic posts while `/kindex nuna` still works. The threshold is inclusive and accepts integers 0–9; an invalid value stops startup. After changing it, recreate the container to apply it. Changing the threshold does not replay old intervals.

Elmar checks [TGO's numerical Leirvogur file](https://flux.phys.uit.no/Kindice/k_lrv1a.txt) every ten minutes; commands use the shared cache. Source failures use exponential backoff up to an hour. The index describes completed three-hour UTC intervals, not instantaneous conditions or planetary Kp. Queries and Icelandic channel posts link the [graph](https://flux.phys.uit.no/Kindice/k_lrv1a.gif) and attribute Leirvogur/Háskóli Íslands and UiT/TGO.

An alert is posted when a **new interval increases** and its value reaches or exceeds the threshold. With threshold 5, `4 → 5 → 5 → 6 → 6 → 5 → 4` produces two posts. Posts contain no mentions. Members can enable all-message channel notifications or mute the channel; no subscription roles are needed.

The first successful fetch establishes a baseline quietly. Later restarts retain cache and progress. Corrections to processed intervals update the displayed value without posting. Missing intervals break increase comparisons; two consecutive valid intervals restore them. After an outage, only the latest fresh interval can generate a post, with no historical backlog.

A newly completed interval has a 30-minute publication grace period. If it remains absent, the last known value is shown with a stale warning and cannot trigger an alert. Query replies also warn when a source check fails or restored data has not been verified yet.

Progress is committed **before** attempting a channel post to prevent duplicate pings across restarts. A failed or interrupted send can therefore lose that interval's alert; it is logged and not replayed. Run one bot instance per state volume. Keep the volume across updates; `docker compose down -v` deletes the baseline and cached data. The volume is writable by UID 10001 while the root filesystem remains read-only.

See the [feature design](docs/k-index-feature.md) and [source research](docs/research/leirvogur-k-index.md), including the documented uncertainty around the provider's terms for automated use of this derived public product.

## Develop

Python 3.12 or later:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

To run locally, export `DISCORD_TOKEN` and `DISCORD_GUILD_ID`, then run `.venv/bin/elmar` from this directory. The entry point does not load `.env` automatically; Compose does. Set `ELMAR_REGISTER_PATH` to override `data/callsigns.json`.

Local K-index state defaults to `state/kindex.sqlite3` (ignored by Git). Set `ELMAR_K_STATE_PATH` to use a different writable location. Source polling starts after the Discord gateway is ready and is cancelled on shutdown.

`registry.py` owns callsign validation and selection; `messages.py` owns callsign wording. `kindex.py` owns source parsing and interval/alert policy, `kindex_service.py` owns HTTP, durable state and polling, and `kindex_discord.py` owns the private query command and wording. `bot.py` owns Discord lifecycle and channel delivery. There is no message-content monitoring or AI service in this version.

See [project decisions](docs/project-decisions.md).

## License

The project's code and documentation are licensed under the [MIT License](LICENSE).

The callsign register in `data/callsigns.json` is derived from [ÍRA's callsign register](https://www.ira.is/kallmerki/), based on Fjarskiptastofa data. The MIT license does not grant rights to third-party source material; any applicable rights remain with their respective holders. Source provenance is recorded in the JSON.

Live geomagnetic data is provided by Leirvogur magnetic observatory/Háskóli Íslands through UiT/TGO. The code's MIT licence does not relicense that source data; see [TGO's data-access notice](https://flux.phys.uit.no/div/DataAccess.html).
