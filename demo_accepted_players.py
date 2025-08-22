#!/usr/bin/env python3
"""
Demo script to show what the session embed looks like with accepted players.

This demonstrates the new functionality that shows accepted player names and roles.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import database, models, embeds, timeutil

def print_embed_demo(embed, title):
    """Print a formatted representation of a Discord embed."""
    print(f"\n{title}")
    print("=" * len(title))
    print(f"📌 **{embed.title}**")
    if embed.description:
        print(f"📝 {embed.description}")
    
    for field in embed.fields:
        print(f"\n**{field.name}**")
        for line in field.value.split('\n'):
            print(f"   {line}")
    
    if embed.footer:
        print(f"\n💡 {embed.footer.text}")
    print("-" * 50)

async def demo_session_with_accepted_players():
    """Demo the session embed with accepted players."""
    print("🎮 Session Display Demo - Before and After Accepting Players")
    
    # Use test database
    test_db = database.Database("demo_session.db")
    await test_db.connect()
    
    try:
        # Create test data
        await test_db.execute(
            "INSERT OR IGNORE INTO users (discord_id, username, preferred_roles, timezone) VALUES (?, ?, ?, ?)",
            123456789, "SessionCreator", '["tank", "support"]', "America/New_York"
        )
        
        await test_db.execute(
            "INSERT OR IGNORE INTO users (discord_id, username, preferred_roles, timezone) VALUES (?, ?, ?, ?)",
            987654321, "AwesomeDPS", '["dps"]', "America/New_York"
        )
        
        await test_db.execute(
            "INSERT OR IGNORE INTO users (discord_id, username, preferred_roles, timezone) VALUES (?, ?, ?, ?)",
            111222333, "FlexPlayer", '["tank", "support"]', "Europe/London"
        )
        
        # Create accounts
        await test_db.execute(
            """INSERT OR IGNORE INTO user_accounts 
               (discord_id, account_name, is_primary, dps_rank, dps_division)
               VALUES (?, ?, ?, ?, ?)""",
            987654321, "AwesomeDPS#1337", True, "grandmaster", 1
        )
        
        await test_db.execute(
            """INSERT OR IGNORE INTO user_accounts 
               (discord_id, account_name, is_primary, tank_rank, tank_division, support_rank, support_division)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            111222333, "FlexPlayer#9999", True, "diamond", 2, "platinum", 3
        )
        
        # Create session
        utc_time = timeutil.now_utc()
        await test_db.execute(
            """INSERT INTO sessions 
               (creator_id, guild_id, channel_id, game_mode, scheduled_time, timezone, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            123456789, 987654321, 111222333, "5v5", utc_time.isoformat(), 
            "America/New_York", "Competitive 5v5 - Looking for skilled players!", "OPEN"
        )
        
        session_id = await test_db.get_last_insert_id()
        session_data = await test_db.fetchrow("SELECT * FROM sessions WHERE id = ?", session_id)
        session_dict = dict(session_data)
        
        # Show session with no accepted players
        embed_empty = embeds.session_embed(session_dict, 3, {"tank": 0, "dps": 0, "support": 0}, [])
        print_embed_demo(embed_empty, "🔶 NEW SESSION (No Accepted Players Yet)")
        
        # Add some accepted players
        await test_db.execute(
            """INSERT INTO session_participants 
               (session_id, user_id, account_id, role, is_streaming, selected_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            session_id, 987654321, 1, "dps", True, 123456789  # AwesomeDPS as DPS (streaming)
        )
        
        await test_db.execute(
            """INSERT INTO session_participants 
               (session_id, user_id, account_id, role, is_streaming, selected_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            session_id, 111222333, 2, "tank", False, 123456789  # FlexPlayer as Tank
        )
        
        # Get participants data
        participants = await test_db.fetch(
            """SELECT sp.role, sp.is_streaming, u.username, ua.account_name
               FROM session_participants sp
               JOIN users u ON sp.user_id = u.discord_id
               JOIN user_accounts ua ON sp.account_id = ua.id
               WHERE sp.session_id = ?
               ORDER BY sp.selected_at ASC""",
            session_id
        )
        
        # Calculate new role counts
        role_counts = {"tank": 0, "dps": 0, "support": 0}
        participants_list = []
        for participant in participants:
            role = participant['role']
            if role in role_counts:
                role_counts[role] += 1
            participants_list.append(dict(participant))
        
        # Show session with accepted players
        embed_with_players = embeds.session_embed(session_dict, 1, role_counts, participants_list)
        print_embed_demo(embed_with_players, "🔶 SESSION WITH ACCEPTED PLAYERS")
        
        print("\n🎯 Key Changes:")
        print("   ✅ Now shows accepted player names and their Battle.net accounts")
        print("   ✅ Displays role emojis (🛡️ Tank, ⚔️ DPS, 💉 Support)")
        print("   ✅ Shows streaming status with 📺 emoji")
        print("   ✅ Updates role requirements to reflect accepted players")
        print("   ✅ Queue count shows remaining players waiting")
        
    finally:
        await test_db.close()
        # Clean up
        for file in ["demo_session.db", "demo_session.db-wal", "demo_session.db-shm"]:
            if os.path.exists(file):
                os.remove(file)

async def main():
    """Run the demo."""
    await demo_session_with_accepted_players()

if __name__ == "__main__":
    asyncio.run(main())