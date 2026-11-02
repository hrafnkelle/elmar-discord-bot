import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import aiohttp
import pytest

from elmar.qrz import QRZEntry, QRZError
from elmar.qrz_discord import QRZCommands, entry_text


def test_format_and_missing_fields():
    assert entry_text(QRZEntry("TF3IRA", "First", "Last", "Reykjavík", "Iceland")) == (
        "[TF3IRA](<https://www.qrz.com/db/TF3IRA>) - First Last - Reykjavík Iceland")
    assert entry_text(None) == "Fann ekki kallmerki á qrz.com"
    assert entry_text(QRZEntry("TF3IRA/P", "", "Club", "", "Iceland")) == (
        "[TF3IRA/P](<https://www.qrz.com/db/TF3IRA%2FP>) - Club - Iceland")
    assert r"\*Name\*" in entry_text(QRZEntry("TF3IRA", "*Name*", "", "", ""))


@pytest.mark.parametrize("firstname, addr2", [
    ("First", "x" * 2000),
    ("x" * 2000, "Reykjavík"),
    ("*" * 2000, "*" * 2000),
])
def test_long_fields_fit_discord_message_limit(firstname, addr2):
    text = entry_text(QRZEntry("TF3IRA", firstname, "Last", addr2, "Iceland"))
    assert len(text) <= 2000
    assert text.startswith("[TF3IRA](<https://www.qrz.com/db/TF3IRA>) - ")
    assert text.count(" - ") == 2
    assert "…" in text
    if firstname == "First":
        assert " - First Last - " in text
    if addr2 == "Reykjavík":
        assert text.endswith(" - Reykjavík Iceland")


def test_oversized_callsign_link_is_a_service_error():
    with pytest.raises(QRZError, match="message limit"):
        entry_text(QRZEntry("X" * 2000, "First", "Last", "City", "Country"))


@pytest.mark.parametrize("result", [
    None, QRZEntry("TF3IRA", "First", "Last", "Reykjavík", "Iceland"),
    QRZError("service failed"), aiohttp.ClientConnectionError(), TimeoutError(),
])
def test_command_defers_and_replies_privately(result):
    async def run():
        client = SimpleNamespace(lookup=AsyncMock())
        if isinstance(result, Exception):
            client.lookup.side_effect = result
        else:
            client.lookup.return_value = result
        command = QRZCommands(client)
        interaction = SimpleNamespace(response=SimpleNamespace(defer=AsyncMock()),
                                      followup=SimpleNamespace(send=AsyncMock()))
        await command.lookup(interaction, "tf3ira")
        interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        client.lookup.assert_awaited_once_with("tf3ira")
        reply = interaction.followup.send.call_args
        assert reply.kwargs["ephemeral"] is True
        assert reply.kwargs["suppress_embeds"] is True
        assert reply.kwargs["allowed_mentions"].to_dict() == {"parse": []}
        if isinstance(result, Exception):
            assert reply.args[0] == "Ekki tókst að fletta upp á qrz.com. Reyndu aftur síðar."
        else:
            assert reply.args[0] == entry_text(result)
    asyncio.run(run())
