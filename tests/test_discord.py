import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from elmar.bot import Callsigns, Elmar
from elmar.registry import Registry


def registry():
    return Registry.load(Path(__file__).resolve().parents[1] / "data/callsigns.json")


def test_commands_always_reply_privately():
    async def run():
        group = Callsigns(registry())
        interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()))
        await group.check.callback(group, interaction, "TF9IRA")
        assert "Ekki laust" in interaction.response.send_message.call_args.args[0]
        assert interaction.response.send_message.call_args.kwargs["ephemeral"] is True
        await group.check.callback(group, interaction, "ABC", "English")
        assert "Appears available" in interaction.response.send_message.call_args.args[0]
        await group.suggest.callback(group, interaction, 2, "English")
        assert "Suggested suffix" in interaction.response.send_message.call_args.args[0]
        assert interaction.response.send_message.call_args.kwargs["ephemeral"] is True
    asyncio.run(run())


def test_discord_registration_payload_and_sync():
    async def run():
        async with Elmar(registry(), 123456789) as client:
            commands = client.tree.get_commands(guild=client.guild)
            payload = commands[0].to_dict(client.tree)
            assert payload["name"] == "kallmerki"
            assert {c["name"] for c in payload["options"]} == {"athuga", "velja"}
            choose = next(c for c in payload["options"] if c["name"] == "velja")
            length = next(p for p in choose["options"] if p["name"] == "lengd")
            assert {c["value"] for c in length["choices"]} == {2, 3}
            assert client.intents.value == 0
            client.tree.sync = AsyncMock(return_value=commands)
            await client.setup_hook()
            client.tree.sync.assert_awaited_once_with(guild=client.guild)
    asyncio.run(run())
