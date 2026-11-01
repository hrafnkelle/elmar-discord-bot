# Elmar

A Discord bot for the Elmar amateur radio community, helping newly licensed operators get started.

Elmar is named for the amateur radio tradition of mentoring newly licensed operators.

## Commands

- `/kallmerki athuga vidskeyti:IRA` — check a suffix; `TF3IRA` also works. Occupied suffixes reply **Ekki laust**, regardless of digit.
- `/kallmerki velja` — suggest a random three-letter suffix.
- `/kallmerki velja lengd:2` — suggest a two-letter suffix.
- Both commands accept `tungumal:English`. Replies default to Icelandic and are visible only to the person invoking the command.

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

The bot registers commands only in the configured server. The JSON register is mounted read-only and loaded at startup. No inbound port, database, or runtime access to ÍRA is needed. The server needs outbound HTTPS/WebSocket access to Discord. The container runs as UID 10001; ensure the JSON file and its parent directories are readable by it.

To update the register, follow [the manual update guide](docs/register-updates.md), then run `docker compose up -d --force-recreate elmar`. Recreating the container also handles a replaced bind-mounted file correctly.

## Develop

Python 3.12 or later:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

To run locally, export `DISCORD_TOKEN` and `DISCORD_GUILD_ID`, then run `.venv/bin/elmar` from this directory. The entry point does not load `.env` automatically; Compose does. Set `ELMAR_REGISTER_PATH` to override `data/callsigns.json`.

`registry.py` owns validation and selection, `messages.py` owns response wording, and `bot.py` owns Discord interactions. Add separate command groups for future propagation, geomagnetic storm, and event features. There is no message-content monitoring or AI service in this version.

See [project decisions](docs/project-decisions.md). This repository is local; no GitHub remote is configured yet.
