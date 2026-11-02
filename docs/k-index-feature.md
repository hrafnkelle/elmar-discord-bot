# Leirvogur K-index feature — design interview

Status: implemented and reviewed.

## Confirmed intent

- Add Leirvogur magnetic observatory's local K-index to Elmar.
- “Current” means the latest available published value, labelled with its observation interval.
- Use an inclusive, configurable local-K alert threshold: `ELMAR_K_THRESHOLD`, an integer from 0 to 9, defaulting to 5. Invalid configured values must fail configuration validation. Adjusting the environment and recreating the container changes the threshold.
- Post alerts in one configured server channel without mentions. Members manage notifications or mute the channel through Discord; subscriptions are deferred.
- Notify on increases where the new K reaches or exceeds the configured threshold; equal or falling values produce no notification. At the default threshold of 5, the user's example `4, 5, 5, 6, 6, 5, 4` produces two notifications, at the first 5 and the first 6. At a threshold of 6, it produces one notification, at the first 6. Startup, missing-data and correction rules are settled below.
- `/kindex nuna` replies are private to the requester (updated at the user’s request after implementation).
- `/kindex nuna` includes a link to the official [Leirvogur K-index graph](https://flux.phys.uit.no/Kindice/k_lrv1a.gif), explicitly requested by the user.
- Research numerical data access starting at https://flux.phys.uit.no/Kindice/.
- Keep Icelandic as the default with an English option, consistent with existing commands.

Source investigation: [Leirvogur numerical data research](research/leirvogur-k-index.md). Vocabulary: [glossary](../GLOSSARY.md).

## Design tree

### Round 1 — settled

1. Threshold: **settled — K >= configured threshold**, default 5, configurable through `ELMAR_K_THRESHOLD`.
2. Recipients: **settled — one server channel without mentions**, superseding the earlier role-based plan.
3. Query interface: **settled — private replies**, using `/kindex nuna` with the existing Icelandic default and English option. The exact selection of the latest observation depends on source semantics.

### Round 2 — answers and wording review

4. Source/current meaning: **settled — latest available value** from the published provisional local-K series, with its observation interval.
5. Subscription management: **deferred** — members control channel notification settings; no roles, subscription commands or subscriber records in this version.
6. Alert event: **settled — increases to values >= the configured threshold**, not one notification per high-activity episode. With the default threshold of 5, `4 -> 5` alerts, `5 -> 5` does not, `5 -> 6` alerts, `6 -> 5` does not. Startup, missing intervals, recovery and revisions follow round 3 below.
7. Presentation: **settled — user approved the example below**, including the short HF explanation, provisional status, observation interval, graph and source links.

Example detailed private reply (`itarlegt:true`), using hypothetical example data (not a live report):

> **K-stuðull í Leirvogi: 6 af 9**
>
> Tímabil: 1. nóvember 2026, kl. 18:00–21:00 UTC. Bráðabirgðagildi, það nýjasta sem hefur verið birt.
>
> Gildið bendir til aukinnar segultruflunar við Leirvog. Slíkar truflanir geta haft áhrif á útbreiðslu á HF-böndum, en K-stuðullinn einn segir ekki til um skilyrði á tiltekinni leið eða tíðni.
>
> [Sjá línurit](https://flux.phys.uit.no/Kindice/k_lrv1a.gif) · [Gögn frá UiT/TGO](https://flux.phys.uit.no/Kindice/k_lrv1a.txt)

The number/date above illustrate presentation only. The user approved this explanatory style; source metadata and the value must come from the actual retrieved observation at runtime.

### Round 3 — settled

8. Startup/restarts: **accepted** — establish a baseline without an alert on the first run, and persist the last processed observation and notification state across restarts to prevent duplicate alerts.
9. Missing/delayed data: **accepted** — retain timestamped last-known data for display with a warning; consider the source stale if a newly completed interval remains absent after a 30-minute publication grace period. Suppress stale/historical alerts, and reset comparisons after an actual observation gap until two consecutive valid intervals are available.
10. Corrections: **accepted** — update displayed values for corrections to an already processed interval but generate increase notifications only for new three-hour intervals.
11. Fetch/configuration: **accepted** — shared background fetch every 10 minutes, cached command replies, and an alert channel ID configured in the environment. Keep alerts disabled until the channel is configured while allowing the query command to work. No role ID is required after the scope simplification.

### Subscription alternatives — resolved

The final choice is a dedicated alert channel without subscriptions. Members can enable all-message notifications or mute it. Role mentions and personal subscriptions can be added later. Alternatives considered:

- Direct messages: opt-in/out commands, stored subscriber IDs, individual delivery, and handling members whose privacy settings block messages.
- A dedicated alert channel: post without mentions and let members choose all-message channel notifications through Discord. The bot does not manage individual subscriptions.
- Bot-managed individual mentions: keep an opt-in list and mention users in the shared channel, requiring retained user IDs and handling long recipient lists. Less suitable for growing groups than a role mention.

### Approved implementation summary

Add a separate K-index command group and source adapter, plus a shared 10-minute polling task. Read the public TGO LRV numerical file directly over HTTPS; parse dated intervals rather than chart images. Private query replies include the latest available value, UTC interval, provisional/local label, source, graph, and approved explanation, with the existing English option. Scheduled channel messages use Icelandic.

Keep last-known display data and alert progress in durable storage on a Docker volume. First startup establishes a baseline quietly; subsequent restarts reuse progress. Process new observations chronologically, apply the freshness and consecutive-interval rules, and avoid historical catch-up notifications. An already processed interval's correction updates display data without a new alert.

Configure the alert channel ID and `ELMAR_K_THRESHOLD` (default 5) through `.env`. A threshold change applies to new observations and does not generate retroactive alerts. Posting requires View Channel and Send Messages in that channel; retain disabled mentions and require no role-management permission or privileged gateway intents. The user will choose the actual channel at deployment. The data source's access/attribution uncertainty remains documented in the research memo; no open data licence or provider permission is asserted.

The user explicitly requested implementation after agreeing these choices. Deliver code, tests, setup documentation and deployment configuration, and run the code-review skill in a sub-agent, addressing its findings. No subscription or notification-policy question is pending.

Delivery uses a durable processed-interval cursor recorded before a send attempt. This prevents replay on ordinary restarts, including after a send failure, but permits a lost alert if the send fails or the process exits between committing progress and delivery. This trade-off avoids claiming exactly-once delivery across SQLite and Discord. Failures are logged; there is no historical retry queue.

## Existing constraints

The current bot uses a single configured server, private slash replies, no gateway intents and disabled mentions by default. It has no source polling or persistent alert state. Compose makes the root filesystem and callsign register read-only, with only temporary storage available otherwise. Persistent alert state needs explicit durable storage; both K-index and callsign queries reply privately.

These are design inputs, not decisions to change existing configuration. No role, channel, live alert or deployment has been created by this interview.

## Query output detail

The query defaults to the value, UTC interval and graph link, retaining stale/source warnings. The optional boolean `itarlegt` includes the explanation, full source information and check time. Both modes are private. Scheduled channel alerts retain the full format.
