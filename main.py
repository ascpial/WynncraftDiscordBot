import argparse
import logging

from utils import Client, Configuration

def start(
    sync_commands: bool = False,
    proxy: str | None = None,
):
    try:
        config = Configuration()
    except FileNotFoundError:
        print("Please create and fill the configuration file first.")
        return

    bot = Client(
        config=config,
        proxy=proxy,
    )

    @bot.event
    async def on_ready():
        await bot.load_extension("ext.wynncraft")
        cog = bot.get_cog("Wynncraft")
        
        if sync_commands:
            await bot.tree.sync()
            logging.info("Application commands synced")
        
        await cog.refresh.start()
    
    bot.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sync",
        help="add this argument to sync the application commands",
        action="store_true",
    )
    parser.add_argument(
        "--proxy",
        help="the proxy to use with the discord client",
        type=str,
        required=False,
    )

    args = parser.parse_args()
    
    start(sync_commands=args.sync, proxy=args.proxy)
