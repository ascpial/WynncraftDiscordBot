import discord

from utils import Client, Configuration


def start():
    try:
        config = Configuration()
    except FileNotFoundError:
        print("Please create and fill the configuration file first.")
        return

    bot = Client(
        config=config,
        #proxy="http://172.19.255.254:3128"
    )

    @bot.event
    async def on_ready():
        await bot.load_extension("ext.wynncraft")
        await bot.tree.sync()
    
    bot.run()

if __name__ == "__main__":
    start()