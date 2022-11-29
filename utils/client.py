import discord
from discord.ext import commands

from .configuration import Configuration

__all__ = [
    "Client",
]

INTENTS = discord.Intents.default()

class Client(commands.Bot):
    def __init__(
        self,
        config: Configuration,
        **kwargs,
    ):
        super().__init__(command_prefix=":", intents=INTENTS, **kwargs)

        self.config = config
    
    def run(self):
        """Runs the bot with the token specified in the configuration"""
        super().run(self.config.token)
    
    def get_error_embed(self, error_message: str) -> discord.Embed:
        return discord.Embed(
            colour=0xff0000,
            title=error_message,
        )
    
    async def send_error(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(
            embed=self.get_error_embed(message),
            ephemeral=True,
        )