import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord
from discord import app_commands

from elmar.bot import Callsigns, Elmar
from elmar.kindex_service import KIndexConfig
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


def test_skipanir_is_private_and_tracks_new_nested_commands(tmp_path):
    async def run():
        async with Elmar(registry(), 123, KIndexConfig(str(tmp_path / "k.sqlite3"))) as client:
            command = client.tree.get_command("skipanir", guild=client.guild)
            interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()), followup=SimpleNamespace(send=AsyncMock()))
            await command._do_call(interaction, {})
            first = interaction.response.send_message.call_args
            for name in ("skipanir", "kallmerki athuga", "kallmerki velja", "kindex nuna", "fof2 nuna"):
                assert f"`/{name}`" in first.args[0]
            assert first.kwargs["ephemeral"] is True
            assert first.kwargs["allowed_mentions"].to_dict() == {"parse": []}

            async def future_command(interaction: discord.Interaction):
                pass

            group = app_commands.Group(name="nytt", description="Nýr flokkur")
            subgroup = app_commands.Group(name="undir", description="Undirflokkur")
            subgroup.add_command(app_commands.Command(name="prufa", description="Ný prófunarskipun", callback=future_command))
            group.add_command(subgroup)
            client.tree.add_command(group, guild=client.guild)
            await command._do_call(interaction, {})
            assert "`/nytt undir prufa` — Ný prófunarskipun" in interaction.response.send_message.call_args.args[0]
            client.tree.remove_command("nytt", guild=client.guild)
            await command._do_call(interaction, {})
            assert "/nytt" not in interaction.response.send_message.call_args.args[0]
    asyncio.run(run())


def test_skipanir_splits_long_lists_into_private_messages():
    async def run():
        async with Elmar(registry(), 123) as client:
            async def future_command(interaction: discord.Interaction):
                pass

            for i in range(30):
                client.tree.add_command(app_commands.Command(name=f"prufa{i:02}", description="x" * 100,
                                                             callback=future_command), guild=client.guild)
            interaction = SimpleNamespace(response=SimpleNamespace(send_message=AsyncMock()), followup=SimpleNamespace(send=AsyncMock()))
            await client.tree.get_command("skipanir", guild=client.guild)._do_call(interaction, {})
            replies = [interaction.response.send_message.call_args, *interaction.followup.send.call_args_list]
            assert len(replies) > 1
            assert all(len(reply.args[0]) <= 2000 and reply.kwargs["ephemeral"] is True for reply in replies)
            combined = "\n".join(reply.args[0] for reply in replies)
            for i in range(30):
                assert f"`/prufa{i:02}`" in combined
    asyncio.run(run())
