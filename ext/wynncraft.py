"""This class contains the logic for the Wynncraft functionality to work."""

from __future__ import annotations

from typing import Optional, Iterator
import urllib.error # to catch 400 errors (user does not exists)

import discord
from discord.ext import commands
from discord import app_commands

import wynncraft

from utils import Client, Storage

class Targets:
    def __init__(self, player: Player):
        self.player = player
        self.bot = self.player.parent.cog.bot
    
    @property
    def raw_targets(self) -> list[dict]:
        return self.player.data.get("targets", [])

    async def get_target(self, index: int) -> discord.abc.Messageable | None:
        data = self.raw_targets[index]

        type = data.get("type", 0)

        if type == 0: # normal text channel
            textchannel = self.bot.get_channel(data["id"])
            if textchannel is not None:
                return textchannel
            else:
                return None
        elif type == 1: # direct message (using the user ID)
            user = self.bot.get_user(data["id"])
            if user is None:
                try:
                    user = await self.bot.fetch_user(data["id"])
                except discord.NotFound:
                    return None
            
            return user.dm_channel

    async def __iter__(self) -> Iterator[discord.abc.Messageable]:
        failed = []

        for n in range(len(self.raw_targets)):
            target = await self.get_target(n)
            if target is None:
                failed.append(n)
            else:
                yield target
        
        # remove all invalids targets
        for n in sorted(failed, reverse=True):
            del self.player.data.get("targets", [])[n]

class Player:
    def __init__(self, data: dict, parent: Players):
        self.data = data
        self.parent = parent
    
    @property
    def name(self) -> str | None:
        return self.data.get("name", self.uuid)

    @name.setter
    def name(self, new_name: str):
        self.data["name"] = new_name
    
    @property
    def uuid(self) -> str | None:
        return self.data.get("uuid")
    
    @uuid.setter
    def uuid(self, value: str):
        if self.uuid is None:
            self.data["uuid"] = value
        else:
            raise ValueError("You cannot edit the UUID")
    
    @property
    def wynncraft_stats(self) -> dict:
        return self.data.get("stats", {})
    
    def refresh(self):
        identifier = self.uuid or self.name
        try:
            # the response contains metadata and the data is in a list
            stats = wynncraft.Player.stats(identifier)["data"][0]
        except urllib.error.HTTPError:
            raise ValueError("The username or UUID is invalid")
        else:
            self.data["stats"] = stats
            self.data["name"] = stats.get("username")
            self.data["uuid"] = stats.get("uuid")
    
    def get_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"{self.name or self.uuid}"
        )
        if self.data.get("stats", {}).get("uuid") is not None:
            embed.add_field(name="UUID", value=self.data.get("stats", {}).get("uuid"))
        return embed

class Players(Storage):
    players: list[Player]
    data: list[dict]

    def __init__(self, cog: Wynncraft):
        super().__init__("./players.json", default=[])
        self.cog = cog
    
    def add_player(self, player: Player):
        self.data.append(player.data)
        self.players.append(player)

    def load_players(self):
        players = []

        for player in self.data:
            players.append(Player(player, self))
        
        self.players = players
    
    def load(self):
        super().load()
        self.load_players()
    
    def load_or_empty(self):
        super().load_or_empty()
        if not hasattr(self, "players"):
            self.players = []
    
    def __iter__(self):
        return iter(self.players)

class PlayerCommandGroup(app_commands.Group):
    def __init__(self, bot: Client, cog: Wynncraft):
        super().__init__(
            name="players",
            description="Manager tracked players",
        )
        self.bot = bot
        self.cog = cog
        self.players = self.cog.players
    
    @app_commands.command(
        name="list",
        description="List all tracked players",
    )
    async def list(self, inter: discord.Interaction):
        embeds = []
        for player in self.players:
            embeds.append(player.get_embed())
        
        if len(embeds) > 0:
            await inter.response.send_message(embeds=embeds)
        else:
            await inter.response.send_message("Nothing to show here...")
    
    @app_commands.command(
        name="create",
        description="Create a new player",
    )
    @app_commands.describe(
        name="The name of the player to track.",
        uuid="The UUID of the player to track.",
        target="The channel in which to send notifications.",
        dm="Whether to send notifications in private messages or not."
    )
    async def create(
        self,
        inter: discord.Interaction,
        name: Optional[str] = None,
        uuid: Optional[str] = None,
        target: Optional[discord.TextChannel] = None,
        dm: bool = False,
    ):
        if (name is None and uuid is None) or (name is not None and uuid is not None):
            await self.bot.send_error(
                inter,
                "Specify only name or only UUID.",
            )
            return
        
        # TODO add regex check for UUID : xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        # should be simple lol
        
        if target is None and dm is False:
            await self.bot.send_error(
                inter,
                "Specify at least one target (DM or channel).",
            )
            return
        
        await inter.response.defer(ephemeral=True)
        
        targets = []

        if target is not None:
            targets.append(
                {
                    "type": 0,
                    "id": target.id,
                }
            )
        
        if dm:
            targets.append(
                {
                    "type": 1,
                    "id": inter.user.id,
                }
            )
        
        data = {
            "targets": targets
        }
        if name is not None:
            data["name"] = name
        if uuid is not None:
            data["uuid"] = uuid
        
        player = Player(data, self.players)

        try:
            player.refresh()
        except ValueError: # the username or UUID is invalid
            await inter.edit_original_response(
                content=":negative_squared_cross_mark: The player could not be found.",
            )
        else:
            self.players.add_player(player)

            self.players.save()

            await inter.edit_original_response(
                content=":white_check_mark: The player has been created!",
                embed=player.get_embed(),
            )

class Wynncraft(commands.Cog):
    def __init__(
        self,
        bot: Client,
    ):
        self.bot = bot

        self.players = Players(self)
        self.players.load_or_empty()

        self.player_commands = PlayerCommandGroup(self.bot, self)
        self.bot.tree.add_command(self.player_commands)
    

async def setup(bot: Client):
    await bot.add_cog(Wynncraft(bot))