"""Custom exception classes for the Overwatch Discord bot."""

class BotError(Exception):
    """Base exception for bot errors."""
    pass

class DatabaseError(BotError):
    """Database-related errors."""
    pass

class ValidationError(BotError):
    """Input validation errors."""
    pass

class UserError(BotError):
    """User-related errors (profile not found, etc.)."""
    pass

class SessionError(BotError):
    """Session-related errors."""
    pass

class DuplicateEntry(BotError):
    """User already in queue or duplicate data."""
    pass

class SessionFull(SessionError):
    """Session has no available slots."""
    pass

class SessionClosed(SessionError):
    """Session is closed to new participants."""
    pass

class SessionNotFound(SessionError):
    """Session does not exist."""
    pass

class SessionPermissionError(SessionError):
    """User doesn't have permission to modify this session."""
    pass

class ProfileNotFound(UserError):
    """User hasn't set up their profile."""
    pass

class AccountNotFound(UserError):
    """User account not found."""
    pass

class MissingRanks(UserError):
    """User hasn't set up their ranks for required roles."""
    pass

class InvalidRank(ValidationError):
    """Invalid rank or division specified."""
    pass

class InvalidRole(ValidationError):
    """Invalid role specified."""
    pass

class InvalidGameMode(ValidationError):
    """Invalid game mode specified."""
    pass

class InvalidTimezone(ValidationError):
    """Invalid timezone specified."""
    pass

class InvalidDatetime(ValidationError):
    """Invalid datetime format or value."""
    pass

class RankCompatibilityError(SessionError):
    """User's rank is not compatible with session requirements."""
    pass

class QueueError(SessionError):
    """Queue-related errors."""
    pass

class NotInQueue(QueueError):
    """User is not in the session queue."""
    pass

class AlreadyInQueue(QueueError):
    """User is already in the session queue."""
    pass