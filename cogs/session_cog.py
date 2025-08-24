"""Session management cog for the Overwatch Discord bot."""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional, List
from datetime import datetime

from core import database, models, embeds, errors, timeutil, ui

class SessionCog(commands.Cog):
    """Cog for public session commands and interactions."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="create-session-ui")
    async def create_session_ui(self, interaction: Interaction):
        """Create a new game session using an interactive interface."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate user has profile
            user_profile = await database.db.fetchrow(
                "SELECT * FROM users WHERE discord_id = ?",
                interaction.user.id
            )
            if not user_profile:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Profile Required",
                        "You need to set up your profile first. Use `/setup-profile`."
                    ),
                    ephemeral=True
                )
                return
            
            # Get user's timezone from profile
            user_timezone = user_profile['timezone']
            
            # Create initial embed
            embed = discord.Embed(
                title="🎮 Create New Session",
                description=f"Let's create your Overwatch session step by step!\n\n"
                           f"**Your Timezone:** {user_timezone}\n"
                           f"First, select the game mode you want to play:",
                color=discord.Color.green()
            )
            
            # Create the session creation view
            view = ui.SessionCreationView(self.bot, interaction.user.id, user_timezone)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Error", f"Failed to start session creation: {str(e)}"),
                ephemeral=True
            )

    @app_commands.command(name="view-sessions")
    async def view_sessions(self, interaction: Interaction):
        """List all currently open sessions in the server."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get active sessions for this guild
            sessions = await database.db.fetch(
                """SELECT * FROM sessions 
                   WHERE guild_id = ? AND status IN ('OPEN', 'CLOSED') 
                   ORDER BY scheduled_time ASC""",
                interaction.guild_id
            )
            
            # Convert to dictionaries
            sessions_list = [dict(session) for session in sessions]
            
            # Create and send embed
            embed = embeds.session_list_embed(sessions_list, interaction.guild.name)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Error", f"Failed to retrieve sessions: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="cancel-session")
    @app_commands.describe(
        session_id="The ID of the session to cancel"
    )
    async def cancel_session(self, interaction: Interaction, session_id: int):
        """Cancel a session you created."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if session exists and user is the creator
            session = await database.db.fetchrow(
                "SELECT * FROM sessions WHERE id = ?", session_id
            )
            
            if not session:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Session Not Found",
                        f"Session #{session_id} does not exist."
                    ),
                    ephemeral=True
                )
                return
            
            if session['creator_id'] != interaction.user.id:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Permission Denied",
                        "You can only cancel sessions that you created."
                    ),
                    ephemeral=True
                )
                return
            
            if session['status'] == 'CANCELLED':
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Already Cancelled",
                        "This session has already been cancelled."
                    ),
                    ephemeral=True
                )
                return
            
            # Cancel the session
            await database.db.execute(
                "UPDATE sessions SET status = 'CANCELLED' WHERE id = ?",
                session_id
            )
            
            # Clear the queue
            await database.db.execute(
                "DELETE FROM session_queue WHERE session_id = ?",
                session_id
            )
            
            # Try to update the original message if possible
            try:
                if session['message_id'] and session['channel_id']:
                    channel = self.bot.get_channel(session['channel_id'])
                    if channel:
                        message = await channel.fetch_message(session['message_id'])
                        
                        # Create cancelled embed
                        cancelled_embed = discord.Embed(
                            title=f"🚫 Session #{session_id} Cancelled",
                            description="This session has been cancelled by the creator.",
                            color=discord.Color.red()
                        )
                        
                        await message.edit(embed=cancelled_embed, view=None)
            except Exception:
                pass  # If we can't update the message, that's okay
            
            await interaction.followup.send(
                embed=embeds.success_embed(
                    "Session Cancelled",
                    f"Session #{session_id} has been cancelled successfully."
                ),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Error", f"Failed to cancel session: {str(e)}"),
                ephemeral=True
            )

    @cancel_session.autocomplete('session_id')
    async def session_id_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[int]]:
        """Autocomplete for session ID field (user's own sessions only)."""
        try:
            sessions = await database.db.fetch(
                """SELECT id, game_mode, scheduled_time FROM sessions 
                   WHERE creator_id = ? AND status IN ('OPEN', 'CLOSED')
                   ORDER BY scheduled_time ASC LIMIT 25""",
                interaction.user.id
            )
            
            choices = []
            for session in sessions:
                session_id = session['id']
                game_mode = session['game_mode']
                
                # Try to format the time nicely
                try:
                    scheduled_time = session['scheduled_time']
                    if isinstance(scheduled_time, str):
                        dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                    else:
                        dt = scheduled_time
                    time_str = dt.strftime("%m/%d %H:%M")
                    name = f"#{session_id} - {game_mode} at {time_str}"
                except:
                    name = f"#{session_id} - {game_mode}"
                
                if current == "" or current in str(session_id):
                    choices.append(app_commands.Choice(name=name, value=session_id))
            
            return choices
        except:
            return []

async def setup(bot: commands.Bot):
    """Set up the session cog."""
    await bot.add_cog(SessionCog(bot))
