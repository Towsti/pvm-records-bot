import os
import logging

from dotenv import load_dotenv
import interactions

from utils.bot_settings import BOT_SETTINGS


logging.basicConfig(level=logging.DEBUG)
load_dotenv()


client = interactions.Client(token=os.getenv('TOKEN'),
                             intents=interactions.Intents.DEFAULT | interactions.Intents.GUILD_PRESENCES | interactions.Intents.GUILD_MESSAGE_CONTENT)

client.load("interactions.ext.enhanced", debug_scope=BOT_SETTINGS.guild)


# load all cogs in cogs/ folder
for filename in os.listdir("./cogs"):
    if filename.endswith(".py"):
        client.load(f"cogs.{filename[:-3]}")    # cogs/cog1.py -> cogs.cog1

client.start()
