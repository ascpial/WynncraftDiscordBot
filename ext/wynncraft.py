"""This class contains the logic for the Wynncraft functionality to work."""

from __future__ import annotations

from typing import Optional, Iterator
import urllib.error # to catch 400 errors (user does not exists)
import datetime

import discord
from discord.ext import commands
from discord import app_commands

import wynncraft

from utils import Client, Storage, convert_timedelta

EMOJIS = {
    "assassin": "<:assassin:1047260394227499098>",
    "warrior": "<:warrior:1047261013621346366>",
}

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

class Class:
    def __init__(self, data: dict):
        self.data = data
    
    def get(self, id: str):
        indexs = id.split(".")
        data = self.data
        for index in indexs:
            data = data.get(index)
            if data is None:
                return None
        
        return data
    
    @property
    def type(self) -> str:
        return self.get("type").lower()
    @property
    def total_level(self) -> int:
        return self.get("level")
    @property
    def combat_level(self) -> int:
        return self.get("professions.combat.level")

class Stats:
    def __init__(self, data: dict):
        self.data = data
    
    def get(self, id: str):
        indexs = id.split(".")
        data = self.data
        for index in indexs:
            data = data.get(index)
            if data is None:
                return None
        
        return data
    
    @property
    def first_join(self) -> datetime.datetime:
        """First time the player joined"""
        raw_date = self.get("meta.firstJoin")
        return datetime.datetime.strptime(
            raw_date,
            "%Y-%m-%dT%H:%M:%S.%fZ", # ISO Format
        )
    @property
    def last_join(self) -> datetime.datetime:
        """Last time the player has been seen on the server"""
        raw_date = self.get("meta.firstJoin")
        return datetime.datetime.strptime(
            raw_date,
            "%Y-%m-%dT%H:%M:%S.%fZ", # ISO Format
        )
    
    @property
    def online(self) -> bool:
        """Whether the player is online or not"""
        return self.get("meta.location.online")
    @property
    def server(self) -> str:
        """If online, the server the player is on, else None"""
        return self.get("meta.location.server")

    @property
    def total_levels(self) -> int:
        """The total levels the player has
        (Combat and professions)
        """
        return self.get("global.totalLevel.combined")
    @property
    def total_playtime(self) -> datetime.timedelta:
        return datetime.timedelta(
            hours=self.get("meta.playtime")/12 # for some weird reason it seems like there is 12 minutes in one hour...
        )
    @property
    def total_mob_kills(self) -> int:
        return self.get("global.mobsKilled")
    
    @property
    def guild_name(self) -> str | None:
        return self.get("guild.name")
    
    @property
    def classes(self) -> list[Class]:
        classes = []

        for class_ in self.get("characters").values():
            classes.append(Class(class_))
        
        return classes

class Player:
    def __init__(self, data: dict, parent: Players):
        self.data = data
        self.parent = parent
        self.load_stats()

    def load_stats(self):
        self.stats = Stats(self.data.get("stats", {}))
    
    @property
    def name(self) -> str | None:
        return self.data.get("name", self.uuid)

    @name.setter
    def name(self, new_name: str):
        self.data["name"] = new_name
    
    @property
    def uuid(self) -> str | None:
        return self.data.get("uuid")
    
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
            self.load_stats()
    
    def get_embed(self) -> discord.Embed:
        description = f"""**Total levels** {self.stats.total_levels}
        **Total playtime** {convert_timedelta(self.stats.total_playtime)}

        **Guild** {self.stats.guild_name or "No guild"}"""
        embed = discord.Embed(
            title=self.name,
            description=description,
            color=12233344, # wynncraft website background
        )

        embed.set_thumbnail(url=f"https://visage.surgeplay.com/bust/{self.uuid}")

        if not self.stats.online:
            embed.set_footer(
                text="Last seen",
            )
            embed.timestamp = self.stats.last_join
        
        return embed
    
    def get_large_embed(self) -> discord.Embed:
        embed = self.get_embed()
        embed.description += """
        
        **Characters**"""

        for i, class_ in enumerate(self.stats.classes):
            class_name = EMOJIS.get(class_.type, "") + " " + class_.type.capitalize()
            embed.add_field(
                name=class_name,
                value=f"""Combat: {class_.combat_level}
                Total: {class_.total_level}""",
                inline=i%3!=0 or i==0, # go to the next line each 3 classes
            )
        
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
        name="show",
        description="Show the stats of a player",
    )
    @app_commands.describe(
        name="The player to lookup",
    )
    #@app_commands.autocomplete()
    async def show(
        self,
        inter: discord.Interaction,
        name: str,
    ):
        for player in self.players:
            if player.name.lower() == name.lower():
                break
        else:
            await inter.response.send_message("User not found")
            return
        
        await inter.response.send_message(
            embed = player.get_large_embed(),
        )
    
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
                embed=player.get_large_embed(),
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