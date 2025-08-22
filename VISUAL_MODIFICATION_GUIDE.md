# Visual Modification Guide for Overwatch Discord Bot

This guide provides detailed instructions on how to modify the visual aspects of the Overwatch Discord bot, including layout, button options, and icons.

## Table of Contents
1. [Understanding the Architecture](#understanding-the-architecture)
2. [Modifying Embeds](#modifying-embeds)
3. [Customizing UI Components](#customizing-ui-components)
4. [Changing Icons and Emojis](#changing-icons-and-emojis)
5. [Layout and Styling](#layout-and-styling)
6. [Button Customization](#button-customization)
7. [Color Schemes](#color-schemes)

## Understanding the Architecture

The bot's visual components are organized into several key files:

- **`core/embeds.py`** - Contains all Discord embed generation functions
- **`core/ui.py`** - Contains Discord UI components (buttons, selects, modals)
- **`core/models.py`** - Contains display constants (emojis, colors, formatting)
- **`cogs/*.py`** - Contains command logic that uses the visual components

## Modifying Embeds

### Session Embeds

Location: `core/embeds.py` → `session_embed()` function

#### Customizing Session Embed Layout

```python
# In core/embeds.py, line ~35
embed = discord.Embed(
    title=f"🎮 Overwatch {game_mode} Session #{session_id}",  # Modify title format
    description=description,
    color=color,  # Change color scheme
    timestamp=datetime.utcnow()
)
```

**Examples:**
- Change title format: `title=f"🚀 {game_mode} Battle #{session_id}"`
- Remove session ID: `title=f"🎮 Overwatch {game_mode} Session"`
- Add custom prefix: `title=f"[COMMUNITY] {game_mode} Session #{session_id}"`

#### Adding Custom Fields

```python
# Add after line ~90 in session_embed()
embed.add_field(
    name="🏆 Tournament Mode",  # Custom field
    value="Competitive Play",
    inline=True
)
```

#### Modifying Role Requirements Display

```python
# In core/embeds.py, around line 122
# Current 6v6 display:
embed.add_field(
    name="👥 Team Composition",
    value=f"{status_emoji} Players: {total_players}/{team_size}",
    inline=False
)

# Customized version:
embed.add_field(
    name="⭐ Squad Status",  # Changed name
    value=f"{status_emoji} Squad Members: {total_players}/{team_size} 🔥",  # Added emoji
    inline=True  # Changed to inline
)
```

### Profile Embeds

Location: `core/embeds.py` → `profile_embed()` function

#### Customizing Profile Layout

```python
# Modify profile header (line ~160)
embed = discord.Embed(
    title=f"🌟 Player Profile: {username}",  # Changed icon
    color=discord.Color.purple(),  # Changed color
    timestamp=datetime.utcnow()
)
```

#### Adding Custom Profile Fields

```python
# Add after timezone field (line ~170)
embed.add_field(
    name="🎯 Skill Level",
    value="Experienced Player",
    inline=True
)

embed.add_field(
    name="🏅 Achievements",
    value="Top 500 Player",
    inline=True
)
```

## Customizing UI Components

### Buttons

Location: `core/ui.py` - various View classes

#### Modifying Button Styles and Labels

```python
# Example: Changing join/leave buttons in SessionView
@discord.ui.button(
    label="Join Squad",  # Changed from "Join Session"
    style=discord.ButtonStyle.success,  # Green button
    emoji="⚡"  # Changed emoji
)
async def join_session(self, interaction: Interaction, button: discord.ui.Button):
    # ... existing code ...

@discord.ui.button(
    label="Leave Squad",  # Changed from "Leave Session"
    style=discord.ButtonStyle.danger,  # Red button
    emoji="❌"  # Changed emoji
)
async def leave_session(self, interaction: Interaction, button: discord.ui.Button):
    # ... existing code ...
```

#### Button Style Options

```python
# Available button styles:
discord.ButtonStyle.primary    # Blue (default)
discord.ButtonStyle.secondary  # Gray
discord.ButtonStyle.success    # Green
discord.ButtonStyle.danger     # Red
discord.ButtonStyle.link       # Link button (requires URL)
```

### Dropdown Menus

#### Customizing Role Selection

```python
# In PlayerAcceptanceView class (core/ui.py, line ~695)
@discord.ui.select(
    placeholder="Choose your role...",  # Changed placeholder
    options=[
        discord.SelectOption(
            label="Tank Specialist", 
            emoji="🛡️", 
            value="tank",
            description="Lead the charge!"  # Added description
        ),
        discord.SelectOption(
            label="Damage Dealer", 
            emoji="⚔️", 
            value="dps",
            description="Eliminate enemies!"
        ),
        discord.SelectOption(
            label="Support Hero", 
            emoji="💉", 
            value="support",
            description="Keep team alive!"
        )
    ]
)
```

## Changing Icons and Emojis

### Global Emoji Configuration

Location: `core/models.py` - emoji dictionaries

#### Role Emojis

```python
# Line ~48 in core/models.py
ROLE_EMOJIS = {
    Role.TANK: "🛡️",      # Change to "🔰" or "🟢"
    Role.DPS: "⚔️",       # Change to "🔴" or "💥"
    Role.SUPPORT: "💉",   # Change to "💚" or "🩹"
}
```

#### Rank Emojis

```python
# Line ~37 in core/models.py
RANK_EMOJIS = {
    Rank.BRONZE: "🟫",     # Change to "🥉"
    Rank.SILVER: "⚪",     # Change to "🥈"
    Rank.GOLD: "🟨",      # Change to "🥇"
    Rank.PLATINUM: "🟦",  # Change to "💎"
    Rank.DIAMOND: "💎",   # Change to "💠"
    Rank.MASTER: "🟧",    # Change to "🔶"
    Rank.GRANDMASTER: "🔺", # Change to "🔸"
    Rank.CHAMPION: "👑"   # Change to "🏆"
}
```

#### Adding Custom Emojis

```python
# Add custom emoji for 6v6 mode
GAME_MODE_EMOJIS = {
    "5v5": "🎮",
    "6v6": "🎯",  # Current 6v6 emoji
    "Stadium": "🏟️"
}

# Usage in embeds:
emoji = GAME_MODE_EMOJIS.get(game_mode, "🎮")
title = f"{emoji} Overwatch {game_mode} Session #{session_id}"
```

### Discord Custom Emojis

If you have custom Discord emojis in your server:

```python
# Using custom Discord emojis (requires emoji ID)
RANK_EMOJIS = {
    Rank.BRONZE: "<:bronze_rank:123456789>",  # Custom emoji
    Rank.SILVER: "<:silver_rank:987654321>",
    # ... etc
}
```

## Layout and Styling

### Embed Colors

#### Dynamic Colors Based on Game Mode

```python
# In session_embed() function
def get_game_mode_color(game_mode: str, status: str):
    if status != 'OPEN':
        return discord.Color.red()
    
    color_map = {
        "5v5": discord.Color.blue(),
        "6v6": discord.Color.purple(),    # Special color for 6v6
        "Stadium": discord.Color.orange()
    }
    return color_map.get(game_mode, discord.Color.green())

# Usage:
color = get_game_mode_color(game_mode, status)
embed = discord.Embed(title=title, color=color)
```

#### Custom Color Palette

```python
# Define your custom colors
class CustomColors:
    PRIMARY = discord.Color.from_rgb(88, 101, 242)    # Discord Blurple
    SUCCESS = discord.Color.from_rgb(87, 242, 135)    # Green
    WARNING = discord.Color.from_rgb(254, 231, 92)    # Yellow
    DANGER = discord.Color.from_rgb(237, 66, 69)      # Red
    SIXV6 = discord.Color.from_rgb(255, 165, 0)       # Orange for 6v6
```

### Field Organization

#### Inline vs Block Fields

```python
# Inline fields (appear side by side)
embed.add_field(name="Status", value="Open", inline=True)
embed.add_field(name="Queue", value="5 waiting", inline=True)

# Block fields (full width)
embed.add_field(name="Description", value="Long description...", inline=False)
```

#### Custom Field Layouts

```python
# Create a compact status layout
status_info = f"🟢 {status} | 👥 {queue_count} waiting | ⏰ {time_str}"
embed.add_field(
    name="📊 Session Info", 
    value=status_info, 
    inline=False
)
```

## Button Customization

### Advanced Button Configurations

#### Conditional Button Display

```python
# In your View class
def __init__(self, session_data):
    super().__init__()
    
    # Only show manage button for session creator
    if user_id == session_data['creator_id']:
        self.add_item(self.create_manage_button())
    
    # Show different buttons based on game mode
    if session_data['game_mode'] == '6v6':
        self.add_item(self.create_sixv6_button())

def create_manage_button(self):
    button = discord.ui.Button(
        label="⚙️ Manage",
        style=discord.ButtonStyle.secondary,
        custom_id="manage_session"
    )
    button.callback = self.manage_callback
    return button
```

#### Custom Button Interactions

```python
@discord.ui.button(
    label="🎯 Quick Join 6v6",
    style=discord.ButtonStyle.primary,
    emoji="⚡"
)
async def quick_join_sixv6(self, interaction: Interaction, button: discord.ui.Button):
    """Quick join button specifically for 6v6 sessions."""
    # Custom logic for 6v6 quick join
    await self.handle_quick_join(interaction, "6v6")
```

## Color Schemes

### Creating Theme Presets

```python
# Define theme presets
class Themes:
    DEFAULT = {
        'primary': discord.Color.blue(),
        'success': discord.Color.green(),
        'warning': discord.Color.orange(),
        'error': discord.Color.red()
    }
    
    DARK = {
        'primary': discord.Color.from_rgb(54, 57, 63),
        'success': discord.Color.from_rgb(67, 181, 129),
        'warning': discord.Color.from_rgb(250, 166, 26),
        'error': discord.Color.from_rgb(240, 71, 71)
    }
    
    GAMING = {
        'primary': discord.Color.from_rgb(255, 105, 180),  # Hot pink
        'success': discord.Color.from_rgb(0, 255, 127),   # Spring green
        'warning': discord.Color.from_rgb(255, 215, 0),   # Gold
        'error': discord.Color.from_rgb(220, 20, 60)      # Crimson
    }

# Apply theme
current_theme = Themes.GAMING
embed = discord.Embed(color=current_theme['primary'])
```

## Example: Complete 6v6 Visual Customization

Here's a complete example of customizing the 6v6 experience:

```python
# 1. Custom 6v6 colors and emojis (in models.py)
SIXV6_COLOR = discord.Color.from_rgb(255, 165, 0)  # Orange
SIXV6_EMOJI = "🎯"

# 2. Custom session embed for 6v6 (in embeds.py)
if game_mode == "6v6":
    embed = discord.Embed(
        title=f"{SIXV6_EMOJI} 6v6 CHAOS MODE #{session_id}",
        description=f"🔥 **NO ROLE LIMITS** 🔥\n{description}",
        color=SIXV6_COLOR,
        timestamp=datetime.utcnow()
    )
    
    # Special 6v6 team display
    embed.add_field(
        name="🚀 Squad Assembly",
        value=f"{'🟢' if total_players >= 6 else '🔴'} Warriors Ready: {total_players}/6",
        inline=False
    )

# 3. Custom 6v6 buttons (in ui.py)
@discord.ui.button(
    label="⚡ Join Chaos",
    style=discord.ButtonStyle.danger,  # Red for intensity
    emoji="🎯"
)
async def join_sixv6_session(self, interaction: Interaction, button: discord.ui.Button):
    # Custom 6v6 join logic
    pass
```

This guide should give you complete control over the visual aspects of your bot. Remember to restart your bot after making changes to see them take effect!