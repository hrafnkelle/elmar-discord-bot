# Initial release validation

Validated on 2026-11-01 with Python 3.12 and discord.py 2.7.1:

- 42 tests passed: suffix checks across digits, unusual source entries, input and JSON validation, both languages, complete candidate pools, exhausted pools, private responses, and Discord command serialization/registration with a mocked API.
- Docker Compose configuration validated using dummy credentials.
- Docker image built successfully.
- Container smoke test passed with networking disabled, root filesystem read-only, all capabilities dropped, and the register bind-mounted read-only. Confirmed UID 10001, register loading, occupied lookup, random suggestion, and command group construction.
- All seven source PDF pages visually reviewed; two local extractors agreed on all 475 rows, yielding 442 distinct suffixes. Extraction/rendering tools were used only for preparing this snapshot and are not runtime dependencies or maintained import scripts.

A live Discord login, command sync, and in-server invocation have not been tested: the owner's bot token and server ID have not been configured. Complete that check on deployment using the README. No bot has been deployed, and no GitHub remote has been added.
