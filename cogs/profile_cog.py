"""Profile management cog for the Overwatch Discord bot."""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional, List
import json

from core import database, models, embeds, errors, timeutil, ui

class ProfileCog(commands.Cog):
    """Cog for user profile management commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="setup-profile")
    @app_commands.describe(
        timezone="Your timezone (e.g., America/New_York, Europe/London)"
    )
    async def setup_profile(self, interaction: Interaction, timezone: str):
        """Set up your user profile with timezone and preferred roles."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate timezone
            if not timeutil.validate_timezone(timezone):
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Invalid Timezone",
                        f"'{timezone}' is not a valid timezone. Please use an IANA timezone like 'America/New_York'."
                    ),
                    ephemeral=True
                )
                return
            
            # Check if profile already exists
            existing = await database.db.fetchrow(
                "SELECT * FROM users WHERE discord_id = ?",
                interaction.user.id
            )
            
            if existing:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Profile Already Exists",
                        "You already have a profile set up. Use `/my-profile` to view it."
                    ),
                    ephemeral=True
                )
                return
            
            # Create role selection view
            async def role_callback(role_interaction: Interaction, selected_roles: List[str]):
                try:
                    # Create user profile
                    await database.db.execute(
                        """INSERT INTO users (discord_id, username, preferred_roles, timezone)
                           VALUES (?, ?, ?, ?)""",
                        interaction.user.id,
                        interaction.user.display_name,
                        models.serialize_json_field(selected_roles),
                        timezone
                    )
                    
                    await role_interaction.response.send_message(
                        embed=embeds.success_embed(
                            "Profile Created",
                            f"Your profile has been created successfully!\n"
                            f"🌍 Timezone: {timezone}\n"
                            f"🎯 Preferred Roles: {', '.join(role.title() for role in selected_roles)}\n\n"
                            f"Next, add your Battle.net account with `/add-account`."
                        ),
                        ephemeral=True
                    )
                except Exception as e:
                    await role_interaction.response.send_message(
                        embed=embeds.error_embed("Setup Error", f"Failed to create profile: {str(e)}"),
                        ephemeral=True
                    )
            
            view = ui.RoleSelectView(role_callback)
            await interaction.followup.send(
                embed=discord.Embed(
                    title="🎯 Select Your Preferred Roles",
                    description="Choose the roles you prefer to play in Overwatch:",
                    color=discord.Color.blue()
                ),
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Setup Error", f"An error occurred: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="add-account")
    @app_commands.describe(
        account_name="Your Battle.net account name",
        is_primary="Whether this is your primary account",
        tank_rank="Your tank rank",
        tank_div="Your tank division (1-5)",
        dps_rank="Your DPS rank", 
        dps_div="Your DPS division (1-5)",
        support_rank="Your support rank",
        support_div="Your support division (1-5)",
        sixv6_rank="Your 6v6 rank",
        sixv6_div="Your 6v6 division (1-5)"
    )
    async def add_account(self, interaction: Interaction, account_name: str, is_primary: bool,
                         tank_rank: Optional[str] = None, tank_div: Optional[int] = None,
                         dps_rank: Optional[str] = None, dps_div: Optional[int] = None,
                         support_rank: Optional[str] = None, support_div: Optional[int] = None,
                         sixv6_rank: Optional[str] = None, sixv6_div: Optional[int] = None):
        """Add a new Battle.net account to your profile with its ranks."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if profile exists
            user_profile = await database.db.fetchrow(
                "SELECT * FROM users WHERE discord_id = ?",
                interaction.user.id
            )
            if not user_profile:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Profile Not Found",
                        "You need to set up your profile first. Use `/setup-profile`."
                    ),
                    ephemeral=True
                )
                return
            
            # Validate ranks and divisions
            ranks_to_validate = [
                (tank_rank, tank_div, "tank"),
                (dps_rank, dps_div, "dps"),
                (support_rank, support_div, "support"),
                (sixv6_rank, sixv6_div, "6v6")
            ]
            
            for rank, div, role in ranks_to_validate:
                if rank and not models.validate_rank(rank):
                    await interaction.followup.send(
                        embed=embeds.error_embed(
                            "Invalid Rank",
                            f"'{rank}' is not a valid rank for {role}. Valid ranks: {', '.join(models.get_all_ranks())}"
                        ),
                        ephemeral=True
                    )
                    return
                
                if div and not models.validate_division(div):
                    await interaction.followup.send(
                        embed=embeds.error_embed(
                            "Invalid Division",
                            f"'{div}' is not a valid division. Valid divisions: 1-5"
                        ),
                        ephemeral=True
                    )
                    return
            
            # Check if account name already exists for this user
            existing = await database.db.fetchrow(
                "SELECT * FROM user_accounts WHERE discord_id = ? AND account_name = ?",
                interaction.user.id, account_name
            )
            if existing:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Account Exists",
                        f"You already have an account named '{account_name}'. Use `/edit-account` to modify it."
                    ),
                    ephemeral=True
                )
                return
            
            # If this is marked as primary, unset other primary accounts
            if is_primary:
                await database.db.execute(
                    "UPDATE user_accounts SET is_primary = 0 WHERE discord_id = ?",
                    interaction.user.id
                )
            
            # Insert new account
            await database.db.execute(
                """INSERT INTO user_accounts 
                   (discord_id, account_name, is_primary, tank_rank, tank_division,
                    dps_rank, dps_division, support_rank, support_division, 
                    sixv6_rank, sixv6_division)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                interaction.user.id, account_name, is_primary,
                tank_rank.lower() if tank_rank else None, tank_div,
                dps_rank.lower() if dps_rank else None, dps_div,
                support_rank.lower() if support_rank else None, support_div,
                sixv6_rank.lower() if sixv6_rank else None, sixv6_div
            )
            
            # Build success message
            rank_info = []
            for rank, div, role in ranks_to_validate:
                if rank and div:
                    rank_display = models.get_rank_display(rank)
                    if role == "6v6":
                        emoji = "🎯"  # Special emoji for 6v6
                    else:
                        emoji = models.ROLE_EMOJIS.get(role, "")
                    rank_info.append(f"{emoji} {role.title()}: {rank_display} {div}")
            
            success_msg = f"Account '{account_name}' added successfully!"
            if is_primary:
                success_msg += " (Set as primary)"
            if rank_info:
                success_msg += f"\n\n**Ranks:**\n" + "\n".join(rank_info)
            
            await interaction.followup.send(
                embed=embeds.success_embed("Account Added", success_msg),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Error", f"Failed to add account: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="edit-account")
    @app_commands.describe(
        account_name="The account name to edit",
        new_account_name="New account name (leave blank to keep current)",
        is_primary="Whether this should be your primary account",
        tank_rank="Your tank rank",
        tank_div="Your tank division (1-5)",
        dps_rank="Your DPS rank",
        dps_div="Your DPS division (1-5)", 
        support_rank="Your support rank",
        support_div="Your support division (1-5)",
        sixv6_rank="Your 6v6 rank",
        sixv6_div="Your 6v6 division (1-5)"
    )
    async def edit_account(self, interaction: Interaction, account_name: str,
                          new_account_name: Optional[str] = None, is_primary: Optional[bool] = None,
                          tank_rank: Optional[str] = None, tank_div: Optional[int] = None,
                          dps_rank: Optional[str] = None, dps_div: Optional[int] = None,
                          support_rank: Optional[str] = None, support_div: Optional[int] = None,
                          sixv6_rank: Optional[str] = None, sixv6_div: Optional[int] = None):
        """Edit the details of one of your existing accounts."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if account exists
            account = await database.db.fetchrow(
                "SELECT * FROM user_accounts WHERE discord_id = ? AND account_name = ?",
                interaction.user.id, account_name
            )
            if not account:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Account Not Found",
                        f"You don't have an account named '{account_name}'. Use `/my-profile` to see your accounts."
                    ),
                    ephemeral=True
                )
                return
            
            # Validate ranks and divisions if provided
            ranks_to_validate = [
                (tank_rank, tank_div, "tank"),
                (dps_rank, dps_div, "dps"),
                (support_rank, support_div, "support"),
                (sixv6_rank, sixv6_div, "6v6")
            ]
            
            for rank, div, role in ranks_to_validate:
                if rank and not models.validate_rank(rank):
                    await interaction.followup.send(
                        embed=embeds.error_embed(
                            "Invalid Rank",
                            f"'{rank}' is not a valid rank for {role}. Valid ranks: {', '.join(models.get_all_ranks())}"
                        ),
                        ephemeral=True
                    )
                    return
                
                if div and not models.validate_division(div):
                    await interaction.followup.send(
                        embed=embeds.error_embed(
                            "Invalid Division",
                            f"'{div}' is not a valid division. Valid divisions: 1-5"
                        ),
                        ephemeral=True
                    )
                    return
            
            # If setting as primary, unset other primary accounts
            if is_primary:
                await database.db.execute(
                    "UPDATE user_accounts SET is_primary = 0 WHERE discord_id = ? AND account_name != ?",
                    interaction.user.id, account_name
                )
            
            # Build update query
            updates = []
            params = []
            
            if new_account_name:
                updates.append("account_name = ?")
                params.append(new_account_name)
            
            if is_primary is not None:
                updates.append("is_primary = ?")
                params.append(is_primary)
            
            if tank_rank is not None:
                updates.append("tank_rank = ?")
                params.append(tank_rank.lower() if tank_rank else None)
            
            if tank_div is not None:
                updates.append("tank_division = ?")
                params.append(tank_div)
            
            if dps_rank is not None:
                updates.append("dps_rank = ?")
                params.append(dps_rank.lower() if dps_rank else None)
            
            if dps_div is not None:
                updates.append("dps_division = ?")
                params.append(dps_div)
            
            if support_rank is not None:
                updates.append("support_rank = ?")
                params.append(support_rank.lower() if support_rank else None)
            
            if support_div is not None:
                updates.append("support_division = ?")
                params.append(support_div)
            
            if sixv6_rank is not None:
                updates.append("sixv6_rank = ?")
                params.append(sixv6_rank.lower() if sixv6_rank else None)
            
            if sixv6_div is not None:
                updates.append("sixv6_division = ?")
                params.append(sixv6_div)
            
            if not updates:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "No Changes",
                        "You didn't specify any changes to make."
                    ),
                    ephemeral=True
                )
                return
            
            # Add WHERE clause parameters
            params.extend([interaction.user.id, account_name])
            
            # Execute update
            query = f"UPDATE user_accounts SET {', '.join(updates)} WHERE discord_id = ? AND account_name = ?"
            await database.db.execute(query, *params)
            
            await interaction.followup.send(
                embed=embeds.success_embed(
                    "Account Updated",
                    f"Account '{account_name}' has been updated successfully!"
                ),
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Error", f"Failed to update account: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="my-profile")
    async def my_profile(self, interaction: Interaction):
        """View your complete profile in an ephemeral message."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user profile
            user_data = await database.db.fetchrow(
                "SELECT * FROM users WHERE discord_id = ?",
                interaction.user.id
            )
            if not user_data:
                await interaction.followup.send(
                    embed=embeds.error_embed(
                        "Profile Not Found",
                        "You haven't set up your profile yet. Use `/setup-profile` to get started."
                    ),
                    ephemeral=True
                )
                return
            
            # Get user accounts
            accounts = await database.db.fetch(
                "SELECT * FROM user_accounts WHERE discord_id = ? ORDER BY is_primary DESC, account_name ASC",
                interaction.user.id
            )
            
            # Convert to dictionaries
            user_dict = dict(user_data)
            accounts_list = [dict(account) for account in accounts]
            
            # Create and send embed
            embed = embeds.profile_embed(user_dict, accounts_list)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                embed=embeds.error_embed("Error", f"Failed to retrieve profile: {str(e)}"),
                ephemeral=True
            )

    @add_account.autocomplete('tank_rank')
    @add_account.autocomplete('dps_rank')
    @add_account.autocomplete('support_rank')
    @add_account.autocomplete('sixv6_rank')
    @edit_account.autocomplete('tank_rank')
    @edit_account.autocomplete('dps_rank')
    @edit_account.autocomplete('support_rank')
    @edit_account.autocomplete('sixv6_rank')
    async def rank_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for rank fields."""
        ranks = models.get_all_ranks()
        return [
            app_commands.Choice(name=rank.title(), value=rank)
            for rank in ranks
            if current.lower() in rank.lower()
        ][:25]  # Discord limits to 25 choices

    @setup_profile.autocomplete('timezone')
    async def timezone_autocomplete(self, interaction: Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for timezone field."""
        timezones = timeutil.get_common_timezones()
        return [
            app_commands.Choice(name=tz, value=tz)
            for tz in timezones
            if current.lower() in tz.lower()
        ][:25]  # Discord limits to 25 choices

async def setup(bot: commands.Bot):
    """Set up the profile cog."""
    await bot.add_cog(ProfileCog(bot))