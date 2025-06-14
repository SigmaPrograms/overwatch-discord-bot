class BotError(Exception):
    """Base exception for bot errors"""
    pass

class DuplicateEntry(BotError):
    """User already in queue"""
    pass

class SessionFull(BotError):
    """Session has no available slots"""
    pass

class MissingRanks(BotError):
    """User hasn't set up their ranks"""
    pass

class InvalidRank(BotError):
    """Invalid rank or division"""
    pass