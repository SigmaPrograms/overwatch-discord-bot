"""Discord UI components for the Overwatch bot."""

import discord
from discord import Interaction
from discord.ext import commands
from typing import Dict, Any, Optional, List
import json
import asyncio

from core import database, models, embeds, errors, timeutil

class SessionView(discord.ui.View):
    """Persistent view for session management with join/leave buttons."""
    
    def __init__(self, bot: commands.Bot, session_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.session_id = session_id
        
        # Set custom_id for persistence across bot restarts
        for item in self.children:
            if hasattr(item, 'custom_id') and item.custom_id:
                item.custom_id = f"{item.custom_id}:{session_id}"
    
    async def get_session_data(self) -> Optional[Dict[str, Any]]:
        """Get current session data from database."""
        try:
            row = await database.db.fetchrow(
                "SELECT * FROM sessions WHERE id = ?", 
                self.session_id
            )
            if row:
                return dict(row)
            return None
        except Exception:
            return None
    
    async def get_queue_info(self) -> tuple[int, Dict[str, int]]:
        """Get queue count and role distribution."""
        try:
            # Get queue count
            queue_rows = await database.db.fetch(
                "SELECT COUNT(*) as count FROM session_queue WHERE session_id = ?",
                self.session_id
            )
            queue_count = queue_rows[0]['count'] if queue_rows else 0
            
            # Get role distribution (simplified - would need more complex logic for actual implementation)
            role_counts = {"tank": 0, "dps": 0, "support": 0}
            
            return queue_count, role_counts
        except Exception:
            return 0, {"tank": 0, "dps": 0, "support": 0}
    
    async def update_embed(self, interaction: Interaction):
        """Update the session embed with current data."""
        try:
            session_data = await self.get_session_data()
            if not session_data:
                await interaction.followup.send("Session not found.", ephemeral=True)
                return
            
            queue_count, role_counts = await self.get_queue_info()
            embed = embeds.session_embed(session_data, queue_count, role_counts)
            
            await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e:
            await interaction.followup.send(f"Error updating session: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.green, emoji="✅", custom_id="join")
    async def join_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle join button clicks."""
        await interaction.response.defer()
        
        try:
            # Check if session exists and is open
            session_data = await self.get_session_data()
            if not session_data:
                await interaction.followup.send("Session not found.", ephemeral=True)
                return
            
            if session_data['status'] != 'OPEN':
                await interaction.followup.send("This session is no longer open.", ephemeral=True)
                return
            
            # Check if user has a profile
            user_row = await database.db.fetchrow(
                "SELECT * FROM users WHERE discord_id = ?",
                interaction.user.id
            )
            if not user_row:
                await interaction.followup.send(
                    "You need to set up your profile first. Use `/setup-profile`.",
                    ephemeral=True
                )
                return
            
            # Check if already in queue
            existing = await database.db.fetchrow(
                "SELECT * FROM session_queue WHERE session_id = ? AND user_id = ?",
                self.session_id, interaction.user.id
            )
            if existing:
                await interaction.followup.send("You're already in this session queue.", ephemeral=True)
                return
            
            # Get user's accounts
            accounts = await database.db.fetch(
                "SELECT * FROM user_accounts WHERE discord_id = ?",
                interaction.user.id
            )
            if not accounts:
                await interaction.followup.send(
                    "You need to add at least one account. Use `/add-account`.",
                    ephemeral=True
                )
                return
            
            # Add to queue
            account_ids = [str(acc['id']) for acc in accounts]
            preferred_roles = models.parse_json_field(user_row['preferred_roles'])
            
            await database.db.execute(
                """INSERT INTO session_queue 
                   (session_id, user_id, account_ids, preferred_roles, is_streaming, note)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                self.session_id, interaction.user.id, 
                models.serialize_json_field(account_ids),
                models.serialize_json_field(preferred_roles),
                False, None
            )
            
            await interaction.followup.send("✅ You've joined the session queue!", ephemeral=True)
            await self.update_embed(interaction)
            
        except Exception as e:
            await interaction.followup.send(f"Error joining session: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red, emoji="❌", custom_id="leave")
    async def leave_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle leave button clicks."""
        await interaction.response.defer()
        
        try:
            # Remove from queue
            rowcount = await database.db.execute(
                "DELETE FROM session_queue WHERE session_id = ? AND user_id = ?",
                self.session_id, interaction.user.id
            )
            
            if rowcount == 0:
                await interaction.followup.send("You're not in this session queue.", ephemeral=True)
                return
            
            await interaction.followup.send("❌ You've left the session queue.", ephemeral=True)
            await self.update_embed(interaction)
            
        except Exception as e:
            await interaction.followup.send(f"Error leaving session: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Toggle Streaming", style=discord.ButtonStyle.secondary, emoji="📺", custom_id="streaming")
    async def streaming_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle streaming toggle button clicks."""
        await interaction.response.defer()
        
        try:
            # Check if user is in queue
            queue_entry = await database.db.fetchrow(
                "SELECT * FROM session_queue WHERE session_id = ? AND user_id = ?",
                self.session_id, interaction.user.id
            )
            
            if not queue_entry:
                await interaction.followup.send("You need to join the queue first.", ephemeral=True)
                return
            
            # Toggle streaming status
            new_streaming = not queue_entry['is_streaming']
            await database.db.execute(
                "UPDATE session_queue SET is_streaming = ? WHERE session_id = ? AND user_id = ?",
                new_streaming, self.session_id, interaction.user.id
            )
            
            status = "enabled" if new_streaming else "disabled"
            await interaction.followup.send(f"📺 Streaming {status}.", ephemeral=True)
            await self.update_embed(interaction)
            
        except Exception as e:
            await interaction.followup.send(f"Error toggling streaming: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="refresh")
    async def refresh_button(self, interaction: Interaction, button: discord.ui.Button):
        """Handle refresh button clicks."""
        await interaction.response.defer()
        await self.update_embed(interaction)
        await interaction.followup.send("🔄 Session refreshed.", ephemeral=True)

class ManageSessionView(discord.ui.View):
    """Ephemeral view for session management (creator only)."""
    
    def __init__(self, bot: commands.Bot, session_id: int, creator_id: int):
        super().__init__(timeout=300)  # 5 minute timeout for management view
        self.bot = bot
        self.session_id = session_id
        self.creator_id = creator_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Ensure only the session creator can use this view."""
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "Only the session creator can use these controls.", 
                ephemeral=True
            )
            return False
        return True
    
    async def get_session_data(self) -> Optional[Dict[str, Any]]:
        """Get current session data from database."""
        try:
            row = await database.db.fetchrow(
                "SELECT * FROM sessions WHERE id = ?", 
                self.session_id
            )
            if row:
                return dict(row)
            return None
        except Exception:
            return None
    
    @discord.ui.button(label="Open/Close Session", style=discord.ButtonStyle.primary, emoji="🔒")
    async def toggle_session(self, interaction: Interaction, button: discord.ui.Button):
        """Toggle session open/closed status."""
        await interaction.response.defer()
        
        try:
            session_data = await self.get_session_data()
            if not session_data:
                await interaction.followup.send("Session not found.", ephemeral=True)
                return
            
            new_status = "CLOSED" if session_data['status'] == 'OPEN' else "OPEN"
            
            await database.db.execute(
                "UPDATE sessions SET status = ? WHERE id = ?",
                new_status, self.session_id
            )
            
            await interaction.followup.send(f"Session {new_status.lower()}.", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"Error updating session: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Cancel Session", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def cancel_session(self, interaction: Interaction, button: discord.ui.Button):
        """Cancel the session permanently."""
        await interaction.response.defer()
        
        try:
            await database.db.execute(
                "UPDATE sessions SET status = 'CANCELLED' WHERE id = ?",
                self.session_id
            )
            
            # Clear the queue
            await database.db.execute(
                "DELETE FROM session_queue WHERE session_id = ?",
                self.session_id
            )
            
            await interaction.followup.send("Session cancelled.", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"Error cancelling session: {str(e)}", ephemeral=True)

class RoleSelectView(discord.ui.View):
    """View for selecting preferred roles during profile setup."""
    
    def __init__(self, callback_func):
        super().__init__(timeout=60)
        self.callback_func = callback_func
        self.selected_roles = []
    
    @discord.ui.select(
        placeholder="Select your preferred roles...",
        min_values=1,
        max_values=3,
        options=[
            discord.SelectOption(
                label="Tank",
                description="Protect your team and control space",
                emoji="🛡️",
                value="tank"
            ),
            discord.SelectOption(
                label="DPS",
                description="Deal damage and eliminate enemies",
                emoji="⚔️",
                value="dps"
            ),
            discord.SelectOption(
                label="Support",
                description="Heal and enable your teammates",
                emoji="💉",
                value="support"
            )
        ]
    )
    async def role_select(self, interaction: Interaction, select: discord.ui.Select):
        """Handle role selection."""
        self.selected_roles = select.values
        await self.callback_func(interaction, self.selected_roles)

# Helper function to register persistent views
async def setup_persistent_views(bot: commands.Bot):
    """Register persistent views after bot startup."""
    try:
        # Get all active sessions with message IDs
        sessions = await database.db.fetch(
            "SELECT id, message_id FROM sessions WHERE status IN ('OPEN', 'CLOSED') AND message_id IS NOT NULL"
        )
        
        for session in sessions:
            session_id = session['id']
            view = SessionView(bot, session_id)
            bot.add_view(view)
        
        print(f"✓ Registered {len(sessions)} persistent session views")
        
    except Exception as e:
        print(f"✗ Error setting up persistent views: {e}")