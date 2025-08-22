"""Discord embed generation for the Overwatch bot."""

import discord
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from core import models, timeutil

def session_embed(session_data: Dict[str, Any], queue_count: int = 0, 
                 role_counts: Optional[Dict[str, int]] = None) -> discord.Embed:
    """
    Create a rich embed for displaying session information.
    
    Args:
        session_data: Dictionary containing session information from database
        queue_count: Number of users in queue
        role_counts: Current role distribution (tank, dps, support counts)
    
    Returns:
        Discord embed object
    """
    if role_counts is None:
        role_counts = {"tank": 0, "dps": 0, "support": 0}
    
    # Parse session data
    session_id = session_data.get('id', 'N/A')
    game_mode = session_data.get('game_mode', 'Unknown')
    description = session_data.get('description') or "No description provided."
    status = session_data.get('status', 'UNKNOWN')
    scheduled_time = session_data.get('scheduled_time')
    timezone_str = session_data.get('timezone', 'UTC')
    max_rank_diff = session_data.get('max_rank_diff')
    
    # Create embed
    color = discord.Color.green() if status == 'OPEN' else discord.Color.red()
    embed = discord.Embed(
        title=f"🎮 Overwatch {game_mode} Session #{session_id}",
        description=description,
        color=color,
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
                value=f"Invalid time format",
                inline=False
            )
    
    # Add status field
    status_emoji = "🟢" if status == 'OPEN' else "🔴" if status == 'CLOSED' else "⚫"
    embed.add_field(
        name="📊 Status",
        value=f"{status_emoji} {status.title()}",
        inline=True
    )
    
    # Add queue count
    embed.add_field(
        name="👥 Queue",
        value=f"{queue_count} waiting",
        inline=True
    )
    
    # Add rank restriction if applicable
    if max_rank_diff and max_rank_diff > 0:
        embed.add_field(
            name="🏆 Rank Limit",
            value=f"Max difference: {max_rank_diff}",
            inline=True
        )
    
    # Add role requirements
    if game_mode in models.GAME_MODE_REQUIREMENTS:
        requirements = models.GAME_MODE_REQUIREMENTS[game_mode]
        role_info = []
        
        for role, needed in requirements.items():
            if needed > 0:
                current = role_counts.get(role, 0)
                role_emoji = models.ROLE_EMOJIS.get(role, "")
                status_emoji = "✅" if current >= needed else "❌"
                role_info.append(f"{status_emoji} {role_emoji} {role.title()}: {current}/{needed}")
        
        if role_info:
            embed.add_field(
                name="🎯 Role Requirements",
                value="\n".join(role_info),
                inline=False
            )
    
    # Add footer
    embed.set_footer(text="Use the buttons below to join, leave, or manage this session.")
    
    return embed

def profile_embed(user_data: Dict[str, Any], accounts: List[Dict[str, Any]]) -> discord.Embed:
    """
    Create an embed for displaying user profile information.
    
    Args:
        user_data: Dictionary containing user profile data
        accounts: List of user accounts with ranks
    
    Returns:
        Discord embed object
    """
    username = user_data.get('username', 'Unknown User')
    timezone_str = user_data.get('timezone', 'Not set')
    preferred_roles = models.parse_json_field(user_data.get('preferred_roles'))
    
    embed = discord.Embed(
        title=f"👤 Profile: {username}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    # Add timezone
    embed.add_field(
        name="🌍 Timezone",
        value=timezone_str,
        inline=True
    )
    
    # Add preferred roles
    if preferred_roles:
        role_display = []
        for role in preferred_roles:
            emoji = models.ROLE_EMOJIS.get(role, "")
            role_display.append(f"{emoji} {role.title()}")
        embed.add_field(
            name="🎯 Preferred Roles",
            value="\n".join(role_display) if role_display else "None set",
            inline=True
        )
    else:
        embed.add_field(
            name="🎯 Preferred Roles",
            value="None set",
            inline=True
        )
    
    # Add accounts
    if accounts:
        for i, account in enumerate(accounts):
            account_name = account.get('account_name', f'Account {i+1}')
            is_primary = account.get('is_primary', False)
            
            account_title = f"🎮 {account_name}"
            if is_primary:
                account_title += " (Primary)"
            
            account_info = []
            
            # Add ranks for each role
            for role in ['tank', 'dps', 'support']:
                rank = account.get(f'{role}_rank')
                division = account.get(f'{role}_division')
                
                if rank and division:
                    rank_display = models.get_rank_display(rank)
                    emoji = models.ROLE_EMOJIS.get(role, "")
                    account_info.append(f"{emoji} {role.title()}: {rank_display} {division}")
            
            embed.add_field(
                name=account_title,
                value="\n".join(account_info) if account_info else "No ranks set",
                inline=False
            )
    else:
        embed.add_field(
            name="🎮 Accounts",
            value="No accounts added. Use `/add-account` to add your Battle.net account.",
            inline=False
        )
    
    embed.set_footer(text="Use /edit-account to update your ranks or /add-account for more accounts.")
    
    return embed

def session_list_embed(sessions: List[Dict[str, Any]], guild_name: str = None) -> discord.Embed:
    """
    Create an embed for listing active sessions.
    
    Args:
        sessions: List of session data dictionaries
        guild_name: Name of the Discord guild
    
    Returns:
        Discord embed object
    """
    title = "🎮 Active Overwatch Sessions"
    if guild_name:
        title += f" in {guild_name}"
    
    embed = discord.Embed(
        title=title,
        color=discord.Color.gold(),
        timestamp=datetime.utcnow()
    )
    
    if not sessions:
        embed.description = "No active sessions found. Use `/create-session` to start one!"
        return embed
    
    for session in sessions[:10]:  # Limit to 10 sessions to avoid embed limits
        session_id = session.get('id', 'N/A')
        game_mode = session.get('game_mode', 'Unknown')
        status = session.get('status', 'UNKNOWN')
        scheduled_time = session.get('scheduled_time')
        
        status_emoji = "🟢" if status == 'OPEN' else "🔴"
        
        session_info = f"{status_emoji} {game_mode}"
        
        if scheduled_time:
            try:
                if isinstance(scheduled_time, str):
                    scheduled_dt = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                else:
                    scheduled_dt = scheduled_time
                
                if scheduled_dt.tzinfo is None:
                    scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
                
                time_str = timeutil.format_discord_timestamp(scheduled_dt, 'R')
                session_info += f" • {time_str}"
            except Exception:
                pass
        
        embed.add_field(
            name=f"Session #{session_id}",
            value=session_info,
            inline=True
        )
    
    if len(sessions) > 10:
        embed.set_footer(text=f"Showing 10 of {len(sessions)} active sessions.")
    
    return embed

def error_embed(title: str, message: str, error_type: str = "Error") -> discord.Embed:
    """
    Create an embed for displaying errors.
    
    Args:
        title: Error title
        message: Error message
        error_type: Type of error (Error, Warning, etc.)
    
    Returns:
        Discord embed object
    """
    color = discord.Color.red() if error_type == "Error" else discord.Color.orange()
    
    embed = discord.Embed(
        title=f"❌ {title}",
        description=message,
        color=color
    )
    
    return embed

def success_embed(title: str, message: str) -> discord.Embed:
    """
    Create an embed for displaying success messages.
    
    Args:
        title: Success title
        message: Success message
    
    Returns:
        Discord embed object
    """
    embed = discord.Embed(
        title=f"✅ {title}",
        description=message,
        color=discord.Color.green()
    )
    
    return embed
