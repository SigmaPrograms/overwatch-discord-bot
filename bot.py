import os
import logging
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from core.database import db

# Load environment variables
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables!")

INTENTS = discord.Intents.none()
INTENTS.guilds = True
INTENTS.guild_messages = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

@bot.event
async def on_ready():
    await db.connect()
    print(f"✓ Database connected")
    print(f"✓ {bot.user} online")
    await bot.tree.sync()
    print("✓ Commands synced")

# Load cogs (we'll create these next)
# for cog in ("profile_cog", "session_cog", "manage_cog"):
#     bot.load_extension(f"cogs.{cog}")

if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))