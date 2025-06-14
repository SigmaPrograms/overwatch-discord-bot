import os, asyncio, aiosqlite, importlib.resources as pkg
DB_FILE = os.getenv("DB_PATH", "data/overwatch.db")

CREATE_STATEMENTS = """
-- users
CREATE TABLE IF NOT EXISTS users (
  discord_id     INTEGER PRIMARY KEY,
  username       TEXT,
  preferred_roles TEXT,
  timezone       TEXT,
  created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- user_accounts
CREATE TABLE IF NOT EXISTS user_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  discord_id INTEGER REFERENCES users(discord_id),
  account_name TEXT,
  tank_rank TEXT, tank_division INTEGER,
  dps_rank  TEXT, dps_division  INTEGER,
  support_rank TEXT, support_division INTEGER,
  is_primary BOOLEAN DEFAULT 0
);
-- sessions
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creator_id INTEGER, guild_id INTEGER, channel_id INTEGER,
  game_mode TEXT, scheduled_time TIMESTAMP, timezone TEXT,
  description TEXT, max_rank_diff INTEGER, status TEXT,
  message_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- session_queue
CREATE TABLE IF NOT EXISTS session_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER, user_id INTEGER,
  account_ids TEXT, preferred_roles TEXT,
  is_streaming BOOLEAN DEFAULT 0, note TEXT, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- session_participants
CREATE TABLE IF NOT EXISTS session_participants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER, user_id INTEGER, account_id INTEGER,
  role TEXT, is_streaming BOOLEAN,
  selected_by INTEGER, selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        """Open or create the SQLite DB with WAL for concurrency."""
        self.conn = await aiosqlite.connect(self.db_path, isolation_level=None)
        await self.conn.executescript(CREATE_STATEMENTS)
        await self.conn.execute("PRAGMA journal_mode=WAL;")

    async def fetchrow(self, query: str, *args):
        async with self.conn.execute(query, args) as c:
            return await c.fetchone()

    async def fetch(self, query: str, *args):
        async with self.conn.execute(query, args) as c:
            return await c.fetchall()

    async def execute(self, query: str, *args):
        await self.conn.execute(query, args)

db = Database()
