import os

from dotenv import load_dotenv
import interactions


load_dotenv()


client = interactions.Client(token=os.getenv('TOKEN'), intents=interactions.Intents.DEFAULT)

# load all cogs in cogs/ folder
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load(f"cogs.{filename[:-3]}")    # cogs/cog1.py -> cogs.cog1

client.start()
