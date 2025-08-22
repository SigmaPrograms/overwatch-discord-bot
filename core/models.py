from enum import StrEnum, IntEnum
import json
from typing import Dict, List, Optional

class Rank(StrEnum):
    """Overwatch rank tiers with emoji representations."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    CHAMPION = "champion"

class Division(IntEnum):
    """Rank divisions (5 is lowest, 1 is highest within a rank)."""
    FIVE = 5
    FOUR = 4
    THREE = 3
    TWO = 2
    ONE = 1

class Role(StrEnum):
    """Overwatch roles."""
    TANK = "tank"
    DPS = "dps"
    SUPPORT = "support"

class GameMode(StrEnum):
    """Available game modes."""
    FIVE_V_FIVE = "5v5"
    SIX_V_SIX = "6v6"
    STADIUM = "Stadium"

# Emoji mappings for display
RANK_EMOJIS = {
    Rank.BRONZE: "🟫",
    Rank.SILVER: "⚪",
    Rank.GOLD: "🟨",
    Rank.PLATINUM: "🟦",
    Rank.DIAMOND: "💎",
    Rank.MASTER: "🟧",
    Rank.GRANDMASTER: "🔺",
    Rank.CHAMPION: "👑"
}

ROLE_EMOJIS = {
    Role.TANK: "🛡️",
    Role.DPS: "⚔️",
    Role.SUPPORT: "💉"
}

# Game mode requirements (role -> count needed)
GAME_MODE_REQUIREMENTS = {
    GameMode.FIVE_V_FIVE: {
        Role.TANK: 1,
        Role.DPS: 2,
        Role.SUPPORT: 2
    },
    GameMode.SIX_V_SIX: {
        Role.TANK: 2,
        Role.DPS: 2,
        Role.SUPPORT: 2
    },
    GameMode.STADIUM: {
        Role.TANK: 0,
        Role.DPS: 6,
        Role.SUPPORT: 0
    }
}

# Rank order for comparison (lower index = higher rank)
RANK_ORDER = [
    Rank.CHAMPION,
    Rank.GRANDMASTER,
    Rank.MASTER,
    Rank.DIAMOND,
    Rank.PLATINUM,
    Rank.GOLD,
    Rank.SILVER,
    Rank.BRONZE
]

def get_rank_display(rank: str) -> str:
    """Get the display string for a rank with emoji."""
    try:
        rank_enum = Rank(rank.lower())
        emoji = RANK_EMOJIS.get(rank_enum, "")
        return f"{rank.title()}{emoji}"
    except ValueError:
        return rank.title()

def get_role_display(role: str) -> str:
    """Get the display string for a role with emoji."""
    try:
        role_enum = Role(role.lower())
        emoji = ROLE_EMOJIS.get(role_enum, "")
        return f"{emoji} {role.title()}"
    except ValueError:
        return role.title()

def calculate_rank_difference(rank1: str, div1: int, rank2: str, div2: int) -> int:
    """
    Calculate the difference between two ranks.
    Returns the absolute difference in "rank points".
    Each rank has 5 divisions, so the difference is calculated as:
    (rank_index_diff * 5) + division_diff
    """
    try:
        rank1_enum = Rank(rank1.lower())
        rank2_enum = Rank(rank2.lower())
        
        rank1_index = RANK_ORDER.index(rank1_enum)
        rank2_index = RANK_ORDER.index(rank2_enum)
        
        # Calculate rank points (higher rank = lower points)
        rank1_points = rank1_index * 5 + (6 - div1)  # Division 1 = 5 points, Division 5 = 1 point
        rank2_points = rank2_index * 5 + (6 - div2)
        
        return abs(rank1_points - rank2_points)
    except (ValueError, IndexError):
        # If we can't compare ranks, assume they're compatible
        return 0

def is_rank_compatible(creator_rank: str, creator_div: int, 
                      participant_rank: str, participant_div: int, 
                      max_diff: Optional[int]) -> bool:
    """
    Check if a participant's rank is compatible with the session creator's rank.
    If max_diff is None or 0, all ranks are compatible.
    """
    if max_diff is None or max_diff <= 0:
        return True
    
    diff = calculate_rank_difference(creator_rank, creator_div, participant_rank, participant_div)
    return diff <= max_diff

def parse_json_field(field_value: Optional[str], default=None) -> any:
    """Safely parse a JSON field from the database."""
    if not field_value:
        return default or []
    
    try:
        return json.loads(field_value)
    except (json.JSONDecodeError, TypeError):
        return default or []

def serialize_json_field(data: any) -> str:
    """Serialize data to JSON for database storage."""
    if data is None:
        return "[]"
    return json.dumps(data)

# Validation helpers
def validate_rank(rank: str) -> bool:
    """Check if a rank string is valid."""
    try:
        Rank(rank.lower())
        return True
    except ValueError:
        return False

def validate_division(division: int) -> bool:
    """Check if a division number is valid."""
    try:
        Division(division)
        return True
    except ValueError:
        return False

def validate_role(role: str) -> bool:
    """Check if a role string is valid."""
    try:
        Role(role.lower())
        return True
    except ValueError:
        return False

def validate_game_mode(game_mode: str) -> bool:
    """Check if a game mode string is valid."""
    try:
        GameMode(game_mode)
        return True
    except ValueError:
        return False

def get_all_ranks() -> List[str]:
    """Get all available rank names."""
    return [rank.value for rank in Rank]

def get_all_roles() -> List[str]:
    """Get all available role names."""
    return [role.value for role in Role]

def get_all_game_modes() -> List[str]:
    """Get all available game mode names."""
    return [mode.value for mode in GameMode]