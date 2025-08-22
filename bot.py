"""
Overwatch Discord Bot - Main Entry Point

A comprehensive Discord bot for scheduling and managing Overwatch 2 game sessions.
Features user profiles with multiple accounts, rank tracking, real-time session 
management via interactive buttons, SQLite persistence, and Docker/Railway deployment.
"""

import os
import logging
import discord
import asyncio
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timezone

from core import database, ui, timeutil

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables! Please set it in your .env file.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot setup with minimal intents (no message content needed for slash commands)
INTENTS = discord.Intents.none()
INTENTS.guilds = True
INTENTS.guild_messages = True  # Needed for sending messages

class OverwatchBot(commands.Bot):
    """Custom bot class with enhanced functionality."""
    
    def __init__(self):
        super().__init__(
            command_prefix="!",  # Not used since we only use slash commands
            intents=INTENTS,
            help_command=None  # Disable default help command
        )
        self.initial_extensions = [
            'cogs.profile_cog',
            'cogs.session_cog', 
            'cogs.manage_cog'
        ]
    
    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Setting up bot...")
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Connect to database
        try:
            await database.db.connect()
            logger.info("✓ Database connected successfully")
        except Exception as e:
            logger.error(f"✗ Failed to connect to database: {e}")
            raise
        
        # Load all cogs
        await self.load_cogs()
        
        # Start background task for session management
        self.session_cleanup_task.start()
        logger.info("✓ Background task started")
        
        # Sync commands globally (this will take a moment)
        try:
            synced = await self.tree.sync()
            logger.info(f"✓ Synced {len(synced)} command(s) globally")
        except Exception as e:
            logger.error(f"✗ Failed to sync commands: {e}")
        
        # Set up persistent views for existing sessions
        try:
            await ui.setup_persistent_views(self)
        except Exception as e:
            logger.error(f"✗ Failed to setup persistent views: {e}")
    
    async def load_cogs(self):
        """Load all cogs."""
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"✓ Loaded {extension}")
            except Exception as e:
                logger.error(f"✗ Failed to load {extension}: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"✓ {self.user} is online and ready!")
        logger.info(f"✓ Connected to {len(self.guilds)} guild(s)")
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="for Overwatch sessions | /setup-profile to start"
        )
        await self.change_presence(activity=activity)
    
    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
    
    async def on_guild_remove(self, guild):
        """Called when the bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
    
    async def on_application_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Global error handler for application commands."""
        logger.error(f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}")
        
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please try again later.",
                ephemeral=True
            )
    
    @tasks.loop(minutes=1)
    async def session_cleanup_task(self):
        """Background task that runs every minute to close expired sessions."""
        try:
            now_utc = timeutil.now_utc()
            
            # Find sessions that should be closed (start time has passed)
            expired_sessions = await database.db.fetch(
                """SELECT * FROM sessions 
                   WHERE status = 'OPEN' 
                   AND scheduled_time <= ? 
                   AND datetime(scheduled_time) <= datetime(?)""",
                now_utc.isoformat(),
                now_utc.isoformat()
            )
            
            for session in expired_sessions:
                try:
                    session_id = session['id']
                    
                    # Update session status to completed
                    await database.db.execute(
                        "UPDATE sessions SET status = 'COMPLETED' WHERE id = ?",
                        session_id
                    )
                    
                    # Try to update the session message if it exists
                    try:
                        channel_id = session['channel_id']
                        message_id = session['message_id']
                        
                        if channel_id and message_id:
                            channel = self.get_channel(channel_id)
                            if channel:
                                message = await channel.fetch_message(message_id)
                                
                                # Create completed embed
                                completed_embed = discord.Embed(
                                    title=f"✅ Session #{session_id} Started",
                                    description="This session has started. Have fun playing!",
                                    color=discord.Color.green()
                                )
                                
                                await message.edit(embed=completed_embed, view=None)
                    except Exception as e:
                        logger.warning(f"Could not update message for session {session_id}: {e}")
                    
                    logger.info(f"Automatically completed session #{session_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing expired session {session.get('id', 'unknown')}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")
    
    @session_cleanup_task.before_loop
    async def before_session_cleanup(self):
        """Wait until the bot is ready before starting the cleanup task."""
        await self.wait_until_ready()
    
    async def close(self):
        """Clean shutdown of the bot."""
        logger.info("Shutting down bot...")
        
        # Cancel background tasks
        if hasattr(self, 'session_cleanup_task'):
            self.session_cleanup_task.cancel()
        
        # Close database connection
        try:
            await database.db.close()
            logger.info("✓ Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        
        await super().close()

# Create bot instance
bot = OverwatchBot()

async def main():
    """Main entry point."""
    try:
        logger.info("Starting Overwatch Discord Bot...")
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    asyncio.run(main())