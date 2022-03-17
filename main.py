import os
import logging

from dotenv import load_dotenv
import interactions


logging.basicConfig(level=logging.INFO)
load_dotenv()


client = interactions.Client(token=os.getenv('TOKEN'),
                             intents=interactions.Intents.DEFAULT | interactions.Intents.GUILD_PRESENCES)

# load all cogs in cogs/ folder
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load(f"cogs.{filename[:-3]}")    # cogs/cog1.py -> cogs.cog1

client.start()
