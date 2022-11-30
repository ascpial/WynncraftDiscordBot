"""This class contains the logic for the Wynncraft functionality to work."""

from __future__ import annotations

from typing import Optional, Generator, Union
import urllib.error # to catch 400 errors (user does not exists)
import datetime
import logging

import discord
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands

import wynncraft

from utils import Client, Storage, convert_timedelta

# Setup logging

from discord.utils import setup_logging

setup_logging() # colored output like discord.py

EMOJIS = {
    "assassin": "<:assassin:1047260394227499098>",
    "warrior": "<:warrior:1047261013621346366>",
    "archer": "<:archer:1047429598075437108>",
    "mage": "<:mage:1047429596926201906>",
    "shaman": "<:shaman:1047429595323965451>",
}

class Targets:
    def __init__(self, player: Player):
        self.player = player
        self.bot = self.player.parent.cog.bot
    
    @property
    def raw_targets(self) -> list[dict]:
        return self.player.data.get("targets", [])

    async def get_target(self, index: int) -> discord.TextChannel | discord.DMChannel | None:
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

    async def __iter__(
        self
    ) -> Generator[Union[discord.TextChannel, discord.DMChannel]]:
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
        return datetime.datetime.fromisoformat(raw_date)
        # return datetime.datetime.strptime(
        #     raw_date,
        #     "%Y-%m-%dT%H:%M:%S.%fZ", # ISO Format
        # )
    @property
    def last_join(self) -> datetime.datetime:
        """Last time the player has been seen on the server"""
        raw_date = self.get("meta.firstJoin")
        return datetime.datetime.fromisoformat(raw_date)
        # return datetime.datetime.strptime(
        #     raw_date,
        #     "%Y-%m-%dT%H:%M:%S.%fZ", # ISO Format
        # )
    
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
            hours=self.get("meta.playtime")/60*4.7 # see https://github.com/Wynncraft/WynncraftAPI/issues/56
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
        self.targets = Targets(self)
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
    
    @property
    def last_fetched(self) -> datetime.datetime:
        last_timestamp = self.data.get("last_fetched")
        if last_timestamp is not None:
            return datetime.datetime.fromtimestamp(last_timestamp)
        else:
            return None
    @last_fetched.setter
    def last_fetched(self, new_date: datetime.datetime):
        self.data["last_fetched"] = int(new_date.timestamp())
    
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
            self.last_fetched = datetime.datetime.now()
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
    
    def new_player(self, name_or_uuid: str) -> Player:
        """Fetch and create a new player in the database.
        Returns the value from the database if the player is already in it.
        """
        
        for player in self.players:
            if player.name == name_or_uuid or player.uuid == name_or_uuid: # the user has already been fetched
                return player

        logging.info(f"Fetching the new user `{name_or_uuid}`")

        player = Player({"uuid": name_or_uuid}, self) # for now the field being name or uuid doesn't matters, it will be overwritten when fetched

        try:
            player.refresh()
        except ValueError: # the username or UUID is invalid
            raise ValueError("The player name or UUID is invalid or the player doesn't exists.")

        self.add_player(player) # we don't need to handle the "already exist error" as the check as already been done

        self.save()

        return player

    def add_player(self, player: Player):
        for player_ in self.data:
            if player_.get("uuid") == player.uuid:
                raise ValueError("A user with this UUID already exists")

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
        name="show",
        description="Show the stats of a player.",
    )
    @app_commands.describe(
        name="The player to lookup",
    )
    async def show(
        self,
        inter: discord.Interaction,
        name: str,
    ):
        await inter.response.defer(thinking=True)
        try:
            player = self.players.new_player(name) # the function returns the player from the database if it has already been fetched
        except ValueError:
            await inter.edit_original_response(
                content=f":confused: I found no user corresponding to the search `{name}`..."
            )
        else:
            await inter.edit_original_response(
                embed=player.get_large_embed(),
            )
    
    @show.autocomplete("name")
    async def player_autotomplete(
        self,
        inter: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice(str)]:
        choices = []
        
        if len(current) > 0:
            choices.append(
                app_commands.Choice(
                    name=f"Fetch player: {current}",
                    value=current,
                )
            )
        
        for player in self.players:
            if current.lower() in player.name.lower():
                choices.append(
                    app_commands.Choice(
                        name=player.name,
                        value=player.name,
                    )
                )
        
        return choices

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
    
    @tasks.loop(seconds=30) # as the wynncraft API cache is 5 minutes, 30 seconds loop is more than enough
    async def refresh(self):
        """Refresh one player at a time."""
        # 5 minutes ago (to calculate wynncraft cache)
        last_refreshed = datetime.datetime.fromtimestamp(
            datetime.datetime.now().timestamp() - 5*60 # 5 minutes ago
        )

        for player in self.players:
            if len(player.targets.raw_targets) == 0: # we skip if the user is not tracked
                continue
            if player.last_fetched > last_refreshed: # we skip if we fetched the player less than 5 minutes ago
                continue
            was_online = player.stats.online

            player.refresh()

            logging.info(f"Player {player.name} refreshed")

            if was_online is not player.stats.online: # the user connected or disconnected
                if player.stats.online:
                    message = f"{player.name} just logged into {player.stats.server}!"
                else:
                    message = f"{player.name} logged out."
                embed = await player.get_embed()
                for channel in player.targets:
                    await channel.send(
                        content=message,
                        embed=embed,
                    )

async def setup(bot: Client):
    await bot.add_cog(Wynncraft(bot))