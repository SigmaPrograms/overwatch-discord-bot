"""Discord UI components for the Overwatch bot."""

import discord
from discord import Interaction
from discord.ext import commands
from typing import Dict, Any, Optional, List
import json
import asyncio
from datetime import datetime

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
    
    @discord.ui.button(label="Manage Queue", style=discord.ButtonStyle.secondary, emoji="👥")
    async def manage_queue(self, interaction: Interaction, button: discord.ui.Button):
        """Show detailed queue management interface."""
        await interaction.response.defer()
        
        try:
            # Get queue information with full details
            queue_entries = await database.db.fetch(
                """SELECT sq.*, u.username, ua.account_name 
                   FROM session_queue sq
                   JOIN users u ON sq.user_id = u.discord_id
                   LEFT JOIN user_accounts ua ON u.discord_id = ua.discord_id AND ua.is_primary = 1
                   WHERE sq.session_id = ?
                   ORDER BY sq.joined_at ASC""",
                self.session_id
            )
            
            if not queue_entries:
                await interaction.followup.send("No players in queue to manage.", ephemeral=True)
                return
            
            # Create queue management view
            view = QueueManagementView(self.bot, self.session_id, self.creator_id, queue_entries)
            embed = await view.create_queue_embed()
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"Error showing queue: {str(e)}", ephemeral=True)

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

class QueueManagementView(discord.ui.View):
    """View for managing the session queue with detailed player information."""
    
    def __init__(self, bot: commands.Bot, session_id: int, creator_id: int, queue_entries: List[Any]):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        self.session_id = session_id
        self.creator_id = creator_id
        self.queue_entries = queue_entries
        self.current_page = 0
        self.players_per_page = 5
        
        # Initialize player select dropdown
        self.update_player_select()
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Ensure only the session creator can use this view."""
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "Only the session creator can use these controls.", 
                ephemeral=True
            )
            return False
        return True
    
    async def create_queue_embed(self) -> discord.Embed:
        """Create the queue management embed."""
        embed = discord.Embed(
            title=f"👥 Queue Management - Session #{self.session_id}",
            description="Review players in queue and accept them into the session.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        if not self.queue_entries:
            embed.add_field(
                name="Queue Status",
                value="No players in queue",
                inline=False
            )
            return embed
        
        start_idx = self.current_page * self.players_per_page
        end_idx = min(start_idx + self.players_per_page, len(self.queue_entries))
        page_entries = self.queue_entries[start_idx:end_idx]
        
        for i, entry in enumerate(page_entries, start=start_idx + 1):
            username = entry['username'] or "Unknown User"
            is_streaming = entry['is_streaming']
            preferred_roles = models.parse_json_field(entry['preferred_roles'])
            
            # Get user's accounts with ranks
            user_accounts = await database.db.fetch(
                """SELECT * FROM user_accounts 
                   WHERE discord_id = ? 
                   ORDER BY is_primary DESC, account_name ASC""",
                entry['user_id']
            )
            
            field_value = ""
            
            # Show streaming status
            if is_streaming:
                field_value += "📺 Streaming\n"
            
            # Show preferred roles
            if preferred_roles:
                role_str = ", ".join([f"{models.ROLE_EMOJIS.get(r, '')} {r.title()}" for r in preferred_roles])
                field_value += f"🎯 Roles: {role_str}\n"
            
            # Show accounts and ranks
            if user_accounts:
                field_value += "\n🎮 **Accounts:**\n"
                for account in user_accounts[:3]:  # Limit to 3 accounts to avoid embed limits
                    account_name = account['account_name']
                    is_primary = account['is_primary']
                    primary_marker = " (Primary)" if is_primary else ""
                    
                    field_value += f"• **{account_name}**{primary_marker}\n"
                    
                    # Show ranks
                    ranks = []
                    for role in ['tank', 'dps', 'support']:
                        rank = account[f'{role}_rank']
                        division = account[f'{role}_division']
                        if rank and division:
                            emoji = models.ROLE_EMOJIS.get(role, "")
                            rank_display = models.get_rank_display(rank)
                            ranks.append(f"  {emoji} {rank_display} {division}")
                    
                    if ranks:
                        field_value += "\n".join(ranks) + "\n"
                    else:
                        field_value += "  No ranks set\n"
                    field_value += "\n"
            else:
                field_value += "\n🎮 No accounts found"
            
            embed.add_field(
                name=f"{i}. {username}",
                value=field_value,
                inline=False
            )
        
        # Add pagination info
        total_pages = (len(self.queue_entries) + self.players_per_page - 1) // self.players_per_page
        if total_pages > 1:
            embed.set_footer(
                text=f"Page {self.current_page + 1}/{total_pages} • {len(self.queue_entries)} total players"
            )
        else:
            embed.set_footer(text=f"{len(self.queue_entries)} players in queue")
        
        return embed
    
    @discord.ui.select(
        placeholder="Select a player to accept...",
        min_values=0,
        max_values=1
    )
    async def player_select(self, interaction: Interaction, select: discord.ui.Select):
        """Handle player selection for acceptance."""
        if not select.values:
            await interaction.response.defer()
            return
        
        player_index = int(select.values[0])
        selected_entry = self.queue_entries[player_index]
        
        # Show player details and account selection
        view = PlayerAcceptanceView(self.bot, self.session_id, self.creator_id, selected_entry)
        embed = await view.create_player_embed()
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def previous_page(self, interaction: Interaction, button: discord.ui.Button):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            embed = await self.create_queue_embed()
            self.update_player_select()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="➡️")
    async def next_page(self, interaction: Interaction, button: discord.ui.Button):
        """Go to next page."""
        total_pages = (len(self.queue_entries) + self.players_per_page - 1) // self.players_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            embed = await self.create_queue_embed()
            self.update_player_select()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh_queue(self, interaction: Interaction, button: discord.ui.Button):
        """Refresh the queue data."""
        await interaction.response.defer()
        
        # Refresh queue entries
        self.queue_entries = await database.db.fetch(
            """SELECT sq.*, u.username, ua.account_name 
               FROM session_queue sq
               JOIN users u ON sq.user_id = u.discord_id
               LEFT JOIN user_accounts ua ON u.discord_id = ua.discord_id AND ua.is_primary = 1
               WHERE sq.session_id = ?
               ORDER BY sq.joined_at ASC""",
            self.session_id
        )
        
        # Reset to first page if current page is now invalid
        total_pages = (len(self.queue_entries) + self.players_per_page - 1) // self.players_per_page
        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)
        
        embed = await self.create_queue_embed()
        self.update_player_select()
        await interaction.edit_original_response(embed=embed, view=self)
    
    def update_player_select(self):
        """Update the player select dropdown with current page players."""
        start_idx = self.current_page * self.players_per_page
        end_idx = min(start_idx + self.players_per_page, len(self.queue_entries))
        page_entries = self.queue_entries[start_idx:end_idx]
        
        options = []
        for i, entry in enumerate(page_entries, start=start_idx):
            username = entry['username'] or "Unknown User"
            is_streaming = entry['is_streaming']
            
            label = f"{i + 1}. {username}"
            if is_streaming:
                label += " 📺"
            
            description = "Click to view accounts and accept"
            if len(label) > 25:
                label = label[:22] + "..."
            
            options.append(discord.SelectOption(
                label=label,
                description=description,
                value=str(i)
            ))
        
        # Update the select component
        if options:
            self.player_select.options = options
            self.player_select.disabled = False
        else:
            self.player_select.options = [discord.SelectOption(label="No players", value="none")]
            self.player_select.disabled = True


class PlayerAcceptanceView(discord.ui.View):
    """View for accepting a specific player into the session."""
    
    def __init__(self, bot: commands.Bot, session_id: int, creator_id: int, queue_entry: Dict[str, Any]):
        super().__init__(timeout=300)
        self.bot = bot
        self.session_id = session_id
        self.creator_id = creator_id
        self.queue_entry = queue_entry
        self.selected_account = None
        self.selected_role = None
        
        # Initialize account select with placeholder
        self.account_select.options = [discord.SelectOption(label="Loading accounts...", value="loading")]
        self.account_select.disabled = True
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        """Ensure only the session creator can use this view."""
        if interaction.user.id != self.creator_id:
            await interaction.response.send_message(
                "Only the session creator can use these controls.", 
                ephemeral=True
            )
            return False
        return True
    
    async def create_player_embed(self) -> discord.Embed:
        """Create embed showing player details for acceptance."""
        username = self.queue_entry['username'] or "Unknown User"
        user_id = self.queue_entry['user_id']
        is_streaming = self.queue_entry['is_streaming']
        preferred_roles = models.parse_json_field(self.queue_entry['preferred_roles'])
        
        embed = discord.Embed(
            title=f"👤 Accept Player: {username}",
            description="Select an account and role to accept this player.",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        # Show streaming status
        if is_streaming:
            embed.add_field(name="📺 Status", value="Currently streaming", inline=True)
        
        # Show preferred roles
        if preferred_roles:
            role_str = ", ".join([f"{models.ROLE_EMOJIS.get(r, '')} {r.title()}" for r in preferred_roles])
            embed.add_field(name="🎯 Preferred Roles", value=role_str, inline=True)
        
        # Get and show accounts
        user_accounts = await database.db.fetch(
            """SELECT * FROM user_accounts 
               WHERE discord_id = ? 
               ORDER BY is_primary DESC, account_name ASC""",
            user_id
        )
        
        if user_accounts:
            account_info = []
            for account in user_accounts:
                account_name = account['account_name']
                is_primary = account['is_primary']
                primary_marker = " (Primary)" if is_primary else ""
                
                account_info.append(f"**{account_name}**{primary_marker}")
                
                # Show ranks
                ranks = []
                for role in ['tank', 'dps', 'support']:
                    rank = account[f'{role}_rank']
                    division = account[f'{role}_division']
                    if rank and division:
                        emoji = models.ROLE_EMOJIS.get(role, "")
                        rank_display = models.get_rank_display(rank)
                        ranks.append(f"  {emoji} {rank_display} {division}")
                
                if ranks:
                    account_info.extend(ranks)
                else:
                    account_info.append("  No ranks set")
                account_info.append("")  # Empty line
            
            embed.add_field(
                name="🎮 Available Accounts",
                value="\n".join(account_info),
                inline=False
            )
            
            # Initialize account select if not done yet
            if self.account_select.options[0].value == "loading":
                await self.update_selects()
                
        else:
            embed.add_field(
                name="🎮 Accounts",
                value="No accounts found",
                inline=False
            )
            
            # Disable account select if no accounts
            self.account_select.options = [discord.SelectOption(label="No accounts", value="none")]
            self.account_select.disabled = True
        
        # Show current selection
        if self.selected_account or self.selected_role:
            selection_info = []
            if self.selected_account:
                selection_info.append(f"Account: {self.selected_account['account_name']}")
            if self.selected_role:
                emoji = models.ROLE_EMOJIS.get(self.selected_role, "")
                selection_info.append(f"Role: {emoji} {self.selected_role.title()}")
            
            embed.add_field(
                name="✅ Current Selection",
                value="\n".join(selection_info),
                inline=False
            )
        
        return embed
    
    @discord.ui.select(
        placeholder="Select account...",
        min_values=0,
        max_values=1
    )
    async def account_select(self, interaction: Interaction, select: discord.ui.Select):
        """Handle account selection."""
        await interaction.response.defer()
        
        if select.values:
            account_id = int(select.values[0])
            self.selected_account = await database.db.fetchrow(
                "SELECT * FROM user_accounts WHERE id = ?", account_id
            )
        else:
            self.selected_account = None
        
        embed = await self.create_player_embed()
        self.update_selects()
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.select(
        placeholder="Select role...",
        min_values=0,
        max_values=1,
        options=[
            discord.SelectOption(label="Tank", emoji="🛡️", value="tank"),
            discord.SelectOption(label="DPS", emoji="⚔️", value="dps"),
            discord.SelectOption(label="Support", emoji="💉", value="support")
        ]
    )
    async def role_select(self, interaction: Interaction, select: discord.ui.Select):
        """Handle role selection."""
        await interaction.response.defer()
        
        if select.values:
            self.selected_role = select.values[0]
        else:
            self.selected_role = None
        
        embed = await self.create_player_embed()
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Accept Player", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_player(self, interaction: Interaction, button: discord.ui.Button):
        """Accept the player into the session."""
        await interaction.response.defer()
        
        if not self.selected_account or not self.selected_role:
            await interaction.followup.send(
                "Please select both an account and a role before accepting.",
                ephemeral=True
            )
            return
        
        try:
            # Check if player is already accepted in this role
            existing = await database.db.fetchrow(
                """SELECT * FROM session_participants 
                   WHERE session_id = ? AND user_id = ? AND role = ?""",
                self.session_id, self.queue_entry['user_id'], self.selected_role
            )
            
            if existing:
                await interaction.followup.send(
                    f"Player is already accepted as {self.selected_role}.",
                    ephemeral=True
                )
                return
            
            # Add to session participants
            await database.db.execute(
                """INSERT INTO session_participants 
                   (session_id, user_id, account_id, role, is_streaming, selected_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                self.session_id, self.queue_entry['user_id'], self.selected_account['id'],
                self.selected_role, self.queue_entry['is_streaming'], self.creator_id
            )
            
            # Remove from queue
            await database.db.execute(
                "DELETE FROM session_queue WHERE session_id = ? AND user_id = ?",
                self.session_id, self.queue_entry['user_id']
            )
            
            username = self.queue_entry['username']
            account_name = self.selected_account['account_name']
            role_emoji = models.ROLE_EMOJIS.get(self.selected_role, "")
            
            await interaction.followup.send(
                f"✅ Accepted **{username}** ({account_name}) as {role_emoji} {self.selected_role.title()}!",
                ephemeral=True
            )
            
            # Disable the view since player is now accepted
            for item in self.children:
                item.disabled = True
            
            await interaction.edit_original_response(view=self)
            
        except Exception as e:
            await interaction.followup.send(
                f"Error accepting player: {str(e)}",
                ephemeral=True
            )
    
    @discord.ui.button(label="Reject Player", style=discord.ButtonStyle.red, emoji="❌")
    async def reject_player(self, interaction: Interaction, button: discord.ui.Button):
        """Reject/remove the player from queue."""
        await interaction.response.defer()
        
        try:
            # Remove from queue
            await database.db.execute(
                "DELETE FROM session_queue WHERE session_id = ? AND user_id = ?",
                self.session_id, self.queue_entry['user_id']
            )
            
            username = self.queue_entry['username']
            await interaction.followup.send(
                f"❌ Rejected **{username}** and removed from queue.",
                ephemeral=True
            )
            
            # Disable the view since player is now rejected
            for item in self.children:
                item.disabled = True
            
            await interaction.edit_original_response(view=self)
            
        except Exception as e:
            await interaction.followup.send(
                f"Error rejecting player: {str(e)}",
                ephemeral=True
            )
    
    async def update_selects(self):
        """Update the account select dropdown with user's accounts."""
        user_accounts = await database.db.fetch(
            """SELECT * FROM user_accounts 
               WHERE discord_id = ? 
               ORDER BY is_primary DESC, account_name ASC""",
            self.queue_entry['user_id']
        )
        
        options = []
        for account in user_accounts:
            label = account['account_name']
            if account['is_primary']:
                label += " (Primary)"
            
            # Show highest rank as description
            ranks = []
            for role in ['tank', 'dps', 'support']:
                rank = account[f'{role}_rank']
                if rank:
                    ranks.append(f"{role}: {rank.title()}")
            
            description = ", ".join(ranks[:2]) if ranks else "No ranks"
            if len(description) > 50:
                description = description[:47] + "..."
            
            options.append(discord.SelectOption(
                label=label[:25],
                description=description,
                value=str(account['id'])
            ))
        
        if options:
            self.account_select.options = options
            self.account_select.disabled = False
        else:
            self.account_select.options = [discord.SelectOption(label="No accounts", value="none")]
            self.account_select.disabled = True


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