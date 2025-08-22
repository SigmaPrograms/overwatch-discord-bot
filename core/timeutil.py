from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional
import re

def parse_iso_datetime(date_str: str) -> datetime:
    """
    Parse an ISO 8601 datetime string (YYYY-MM-DDTHH:MM) into a naive datetime object.
    
    Args:
        date_str: ISO 8601 formatted datetime string
        
    Returns:
        Naive datetime object
        
    Raises:
        ValueError: If the datetime string is invalid
    """
    # Support both YYYY-MM-DDTHH:MM and YYYY-MM-DD HH:MM formats
    date_str = date_str.replace(' ', 'T')
    
    # Validate format
    pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$'
    if not re.match(pattern, date_str):
        raise ValueError(f"Invalid datetime format: {date_str}. Expected YYYY-MM-DDTHH:MM")
    
    try:
        return datetime.fromisoformat(date_str)
    except ValueError as e:
        raise ValueError(f"Invalid datetime: {date_str}. {str(e)}")

def local_to_utc(naive_dt: datetime, tz_str: str) -> datetime:
    """
    Convert a naive datetime to UTC using the specified timezone.
    
    Args:
        naive_dt: Naive datetime object (assumed to be in the specified timezone)
        tz_str: IANA timezone string (e.g., 'America/New_York')
        
    Returns:
        UTC datetime object
        
    Raises:
        ValueError: If the timezone string is invalid
    """
    try:
        local_tz = ZoneInfo(tz_str)
        localized_dt = naive_dt.replace(tzinfo=local_tz)
        return localized_dt.astimezone(timezone.utc)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {tz_str}. {str(e)}")

def utc_to_local(utc_dt: datetime, tz_str: str) -> datetime:
    """
    Convert a UTC datetime to local time in the specified timezone.
    
    Args:
        utc_dt: UTC datetime object
        tz_str: IANA timezone string (e.g., 'America/New_York')
        
    Returns:
        Localized datetime object
        
    Raises:
        ValueError: If the timezone string is invalid
    """
    try:
        if utc_dt.tzinfo is None:
            # Assume UTC if no timezone info
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        local_tz = ZoneInfo(tz_str)
        return utc_dt.astimezone(local_tz)
    except Exception as e:
        raise ValueError(f"Invalid timezone: {tz_str}. {str(e)}")

def format_discord_timestamp(dt: datetime, style: str = 'F') -> str:
    """
    Format a datetime object as a Discord timestamp.
    
    Args:
        dt: datetime object (should be timezone-aware)
        style: Discord timestamp style
            - 't': Short time (e.g., 16:20)
            - 'T': Long time (e.g., 16:20:30)
            - 'd': Short date (e.g., 20/04/2021)
            - 'D': Long date (e.g., 20 April 2021)
            - 'f': Short date/time (e.g., 20 April 2021 16:20)
            - 'F': Long date/time (e.g., Tuesday, 20 April 2021 16:20)
            - 'R': Relative time (e.g., 2 months ago)
    
    Returns:
        Discord timestamp string (e.g., '<t:1234567890:F>')
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:{style}>"

def now_utc() -> datetime:
    """Get the current UTC datetime."""
    return datetime.now(timezone.utc)

def is_past(dt: datetime) -> bool:
    """Check if a datetime is in the past (compared to UTC now)."""
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt < now_utc()

def validate_timezone(tz_str: str) -> bool:
    """
    Validate that a timezone string is a valid IANA timezone.
    
    Args:
        tz_str: IANA timezone string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        ZoneInfo(tz_str)
        return True
    except Exception:
        return False

def get_common_timezones() -> list[str]:
    """Get a list of commonly used timezone strings."""
    return [
        "UTC",
        "America/New_York",
        "America/Chicago",
        "America/Denver", 
        "America/Los_Angeles",
        "America/Toronto",
        "America/Vancouver",
        "Europe/London",
        "Europe/Paris",
        "Europe/Berlin",
        "Europe/Rome",
        "Asia/Tokyo",
        "Asia/Shanghai",
        "Asia/Seoul",
        "Australia/Sydney",
        "Australia/Melbourne"
    ]