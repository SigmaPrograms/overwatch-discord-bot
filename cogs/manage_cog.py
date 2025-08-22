"""Session management cog for session creators."""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core import database, models, embeds, errors, timeutil, ui

class ManageCog(commands.Cog):
    """Cog for session administration commands available to creators."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="manage-session")
    @app_commands.describe(
        session_id="The ID of the session to manage"
    )
    async def manage_session(self, interaction: Interaction, session_id: int):
        """Open an ephemeral dashboard to manage your session."""
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
                        "You can only manage sessions that you created."
                    ),
                    ephemeral=True
                )
                return
            
            # Get queue information
            queue_entries = await database.db.fetch(
                """SELECT sq.*, u.username, ua.account_name 
                   FROM session_queue sq
                   JOIN users u ON sq.user_id = u.discord_id
                   LEFT JOIN user_accounts ua ON u.discord_id = ua.discord_id AND ua.is_primary = 1
                   WHERE sq.session_id = ?
                   ORDER BY sq.joined_at ASC""",
                session_id
            )
            
            # Create management embed
            embed = await self._create_management_embed(dict(session), queue_entries)
            
            # Create management view
            view = ui.ManageSessionView(self.bot, session_id, interaction.user.id)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Error", f"Failed to open management dashboard: {str(e)}"),
                ephemeral=True
            )
    
    async def _create_management_embed(self, session_data: Dict[str, Any], queue_entries: List[Any]) -> discord.Embed:
        """Create the management dashboard embed."""
        session_id = session_data.get('id', 'N/A')
        game_mode = session_data.get('game_mode', 'Unknown')
        status = session_data.get('status', 'UNKNOWN')
        scheduled_time = session_data.get('scheduled_time')
        description = session_data.get('description') or "No description"
        
        # Create embed
        embed = discord.Embed(
            title=f"🛠️ Managing Session #{session_id}",
            description=f"**Game Mode:** {game_mode}\n**Status:** {status}\n**Description:** {description}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        # Add time field
        if scheduled_time:
            try:
                if isinstance(scheduled_time, str):
                    scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                else:
                    scheduled_dt = scheduled_time
                
                if scheduled_dt.tzinfo is None:
                    scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                
                time_str = timeutil.format_discord_timestamp(scheduled_dt, 'F')
                relative_str = timeutil.format_discord_timestamp(scheduled_dt, 'R')
                embed.add_field(
                    name="⏰ Scheduled Time",
                    value=f"{time_str}\n({relative_str})",
                    inline=False
                )
            except Exception:
                embed.add_field(
                    name="⏰ Scheduled Time",
                    value="Invalid time format",
                    inline=False
                )
        
        # Add queue information
        if queue_entries:
            queue_info = []
            role_counts = {"tank": 0, "dps": 0, "support": 0}
            
            for entry in queue_entries:
                username = entry['username'] or "Unknown User"
                account_name = entry['account_name'] or "No Primary Account"
                is_streaming = entry['is_streaming']
                preferred_roles = models.parse_json_field(entry['preferred_roles'])
                
                # Count preferred roles (simplified)
                for role in preferred_roles:
                    if role in role_counts:
                        role_counts[role] += 1
                
                streaming_indicator = "📺 " if is_streaming else ""
                roles_str = ", ".join(preferred_roles) if preferred_roles else "No preference"
                
                queue_info.append(f"{streaming_indicator}**{username}** ({account_name}) - {roles_str}")
            
            embed.add_field(
                name=f"👥 Queue ({len(queue_entries)} players)",
                value="\n".join(queue_info[:10]) if queue_info else "No players in queue",
                inline=False
            )
            
            if len(queue_entries) > 10:
                embed.add_field(
                    name="...",
                    value=f"And {len(queue_entries) - 10} more players",
                    inline=False
                )
            
            # Add role distribution
            if game_mode in models.GAME_MODE_REQUIREMENTS:
                requirements = models.GAME_MODE_REQUIREMENTS[game_mode]
                role_distribution = []
                
                for role, needed in requirements.items():
                    if needed > 0:
                        available = role_counts.get(role, 0)
                        emoji = models.ROLE_EMOJIS.get(role, "")
                        role_distribution.append(f"{emoji} {role.title()}: {available} available (need {needed})")
                
                if role_distribution:
                    embed.add_field(
                        name="🎯 Role Distribution",
                        value="\n".join(role_distribution),
                        inline=False
                    )
        else:
            embed.add_field(
                name="👥 Queue",
                value="No players in queue",
                inline=False
            )
        
        embed.set_footer(text="Use the buttons below to manage your session.")
        
        return embed
    
    @manage_session.autocomplete('session_id')
    async def session_id_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[int]]:
        """Autocomplete for session ID field (user's own sessions only)."""
        try:
            sessions = await database.db.fetch(
                """SELECT id, game_mode, scheduled_time, status FROM sessions 
                   WHERE creator_id = ? AND status IN ('OPEN', 'CLOSED')
                   ORDER BY scheduled_time ASC LIMIT 25""",
                interaction.user.id
            )
            
            choices = []
            for session in sessions:
                session_id = session['id']
                game_mode = session['game_mode']
                status = session['status']
                
                # Try to format the time nicely
                try:
                    scheduled_time = session['scheduled_time']
                    if isinstance(scheduled_time, str):
                        dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                    else:
                        dt = scheduled_time
                    time_str = dt.strftime("%m/%d %H:%M")
                    name = f"#{session_id} - {game_mode} ({status}) at {time_str}"
                except:
                    name = f"#{session_id} - {game_mode} ({status})"
                
                if current == "" or current in str(session_id):
                    choices.append(app_commands.Choice(name=name, value=session_id))
            
            return choices
        except:
            return []

async def setup(bot: commands.Bot):
    """Set up the manage cog."""
    await bot.add_cog(ManageCog(bot))