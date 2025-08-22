import os
import asyncio
import aiosqlite
from typing import Optional, Any, List, Dict

DB_FILE = os.getenv("DB_PATH", "data/overwatch.db")

CREATE_STATEMENTS = """
-- Users table for Discord user profiles
CREATE TABLE IF NOT EXISTS users (
    discord_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    preferred_roles TEXT, -- JSON array of preferred roles
    timezone TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User accounts table for multiple Battle.net accounts per user
CREATE TABLE IF NOT EXISTS user_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER NOT NULL,
    account_name TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT 0,
    tank_rank TEXT,
    tank_division INTEGER,
    dps_rank TEXT,
    dps_division INTEGER,
    support_rank TEXT,
    support_division INTEGER,
    sixv6_rank TEXT,
    sixv6_division INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (discord_id) REFERENCES users(discord_id) ON DELETE CASCADE,
    UNIQUE(discord_id, account_name)
);

-- Sessions table for game sessions
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    creator_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    game_mode TEXT NOT NULL, -- '5v5', '6v6', 'Stadium'
    scheduled_time TIMESTAMP NOT NULL, -- UTC timestamp
    timezone TEXT NOT NULL, -- Original timezone for display
    description TEXT,
    max_rank_diff INTEGER, -- Maximum rank difference allowed (NULL = no limit)
    status TEXT NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'CLOSED', 'CANCELLED', 'COMPLETED'
    message_id INTEGER, -- Discord message ID for the session embed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(discord_id)
);

-- Session queue table for users waiting to join
CREATE TABLE IF NOT EXISTS session_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    account_ids TEXT, -- JSON array of account IDs to use
    preferred_roles TEXT, -- JSON array of preferred roles for this session
    is_streaming BOOLEAN DEFAULT 0,
    note TEXT,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    UNIQUE(session_id, user_id)
);

-- Session participants table for final selected team
CREATE TABLE IF NOT EXISTS session_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    role TEXT NOT NULL, -- 'tank', 'dps', 'support'
    is_streaming BOOLEAN DEFAULT 0,
    selected_by INTEGER, -- Who selected this participant
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    FOREIGN KEY (account_id) REFERENCES user_accounts(id),
    FOREIGN KEY (selected_by) REFERENCES users(discord_id),
    UNIQUE(session_id, user_id, role)
);
"""

class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Open or create the SQLite DB with WAL mode for concurrency."""
        # Only create directory if path contains a directory component
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        
        self.conn = await aiosqlite.connect(self.db_path, isolation_level=None)
        
        # Set row factory to return Row objects (allows dict-like access)
        self.conn.row_factory = aiosqlite.Row
        
        # Enable WAL mode for better concurrency
        await self.conn.execute("PRAGMA journal_mode=WAL;")
        
        # Enable foreign key constraints
        await self.conn.execute("PRAGMA foreign_keys=ON;")
        
        # Create tables
        await self.conn.executescript(CREATE_STATEMENTS)
        
        # Run migrations
        await self._run_migrations()
        
        await self.conn.commit()

    async def _run_migrations(self):
        """Run database migrations for schema updates."""
        # Check if 6v6 rank columns exist
        cursor = await self.conn.execute("PRAGMA table_info(user_accounts)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'sixv6_rank' not in column_names:
            await self.conn.execute("ALTER TABLE user_accounts ADD COLUMN sixv6_rank TEXT")
            
        if 'sixv6_division' not in column_names:
            await self.conn.execute("ALTER TABLE user_accounts ADD COLUMN sixv6_division INTEGER")

    async def close(self):
        """Close database connection."""
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def fetchrow(self, query: str, *args) -> Optional[aiosqlite.Row]:
        """Fetch a single row."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        async with self.conn.execute(query, args) as cursor:
            return await cursor.fetchone()

    async def fetch(self, query: str, *args) -> List[aiosqlite.Row]:
        """Fetch multiple rows."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        async with self.conn.execute(query, args) as cursor:
            return await cursor.fetchall()

    async def execute(self, query: str, *args) -> int:
        """Execute a query and return the number of affected rows."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        cursor = await self.conn.execute(query, args)
        await self.conn.commit()
        return cursor.rowcount

    async def executemany(self, query: str, args_list: List[tuple]) -> int:
        """Execute a query multiple times with different parameters."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        cursor = await self.conn.executemany(query, args_list)
        await self.conn.commit()
        return cursor.rowcount

    async def get_last_insert_id(self) -> int:
        """Get the ID of the last inserted row."""
        if not self.conn:
            raise RuntimeError("Database not connected")
        
        cursor = await self.conn.execute("SELECT last_insert_rowid()")
        row = await cursor.fetchone()
        return row[0] if row else 0

# Global database instance
db = Database()
