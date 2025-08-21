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

INTENTS = discord.Intents.default()
INTENTS.message_content = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

@bot.event
async def on_ready():
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    await db.connect()
    print(f"✓ Database connected")
    print(f"✓ {bot.user} online")
    
    # Load cogs
    await load_cogs()
    
    # Sync commands
    await bot.tree.sync()
    print("✓ Commands synced")

# Load cogs
async def load_cogs():
    """Load all available cogs."""
    try:
        await bot.load_extension("cogs.session_cog")
        print("✓ session_cog loaded")
    except Exception as e:
        print(f"✗ Failed to load session_cog: {e}")

if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))