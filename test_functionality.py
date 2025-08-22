#!/usr/bin/env python3
"""
Overwatch Discord Bot - Functionality Test Script

This script demonstrates the core functionality of the bot without requiring
a Discord connection. It tests database operations, models, and utilities.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import database, models, timeutil, embeds

async def test_database():
    """Test database functionality."""
    print("🗄️  Testing Database Functionality...")
    
    # Use test database
    test_db = database.Database("test_overwatch.db")
    await test_db.connect()
    
    try:
        # Test user creation
        await test_db.execute(
            "INSERT OR IGNORE INTO users (discord_id, username, preferred_roles, timezone) VALUES (?, ?, ?, ?)",
            123456789, "TestUser", '["tank", "support"]', "America/New_York"
        )
        
        # Test user retrieval
        user = await test_db.fetchrow("SELECT * FROM users WHERE discord_id = ?", 123456789)
        print(f"  ✓ Created user: {user['username']}")
        
        # Test account creation
        await test_db.execute(
            """INSERT OR IGNORE INTO user_accounts 
               (discord_id, account_name, is_primary, tank_rank, tank_division, dps_rank, dps_division)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            123456789, "TestPlayer#1234", True, "gold", 3, "platinum", 1
        )
        
        accounts = await test_db.fetch("SELECT * FROM user_accounts WHERE discord_id = ?", 123456789)
        print(f"  ✓ Created account: {accounts[0]['account_name']}")
        
        # Test session creation
        utc_time = timeutil.now_utc()
        await test_db.execute(
            """INSERT INTO sessions 
               (creator_id, guild_id, channel_id, game_mode, scheduled_time, timezone, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            123456789, 987654321, 111222333, "5v5", utc_time.isoformat(), "America/New_York", "Test session", "OPEN"
        )
        
        sessions = await test_db.fetch("SELECT * FROM sessions WHERE creator_id = ?", 123456789)
        print(f"  ✓ Created session: {sessions[0]['game_mode']} session")
        
        print("  ✓ Database tests passed!")
        
    finally:
        await test_db.close()
        # Clean up test database
        if os.path.exists("test_overwatch.db"):
            os.remove("test_overwatch.db")
        if os.path.exists("test_overwatch.db-wal"):
            os.remove("test_overwatch.db-wal") 
        if os.path.exists("test_overwatch.db-shm"):
            os.remove("test_overwatch.db-shm")

def test_models():
    """Test model functionality."""
    print("\n🎮 Testing Models Functionality...")
    
    # Test rank validation
    assert models.validate_rank("gold") == True
    assert models.validate_rank("invalid") == False
    print("  ✓ Rank validation works")
    
    # Test rank display
    display = models.get_rank_display("gold")
    assert "Gold" in display and "🟨" in display
    print("  ✓ Rank display formatting works")
    
    # Test role display
    role_display = models.get_role_display("tank")
    assert "🛡️" in role_display and "Tank" in role_display
    print("  ✓ Role display formatting works")
    
    # Test rank difference calculation
    diff = models.calculate_rank_difference("gold", 3, "platinum", 1)
    assert diff > 0
    print("  ✓ Rank difference calculation works")
    
    # Test game mode requirements
    requirements = models.GAME_MODE_REQUIREMENTS["5v5"]
    assert requirements["tank"] == 1
    assert requirements["dps"] == 2
    assert requirements["support"] == 2
    print("  ✓ Game mode requirements correct")
    
    print("  ✓ Model tests passed!")

def test_timeutil():
    """Test time utility functionality."""
    print("\n⏰ Testing Time Utilities...")
    
    # Test datetime parsing
    dt = timeutil.parse_iso_datetime("2024-12-25T19:30")
    assert dt.year == 2024 and dt.month == 12 and dt.day == 25
    print("  ✓ ISO datetime parsing works")
    
    # Test timezone validation
    assert timeutil.validate_timezone("America/New_York") == True
    assert timeutil.validate_timezone("Invalid/Timezone") == False
    print("  ✓ Timezone validation works")
    
    # Test UTC conversion
    naive_dt = datetime(2024, 12, 25, 19, 30)
    utc_dt = timeutil.local_to_utc(naive_dt, "America/New_York")
    assert utc_dt.tzinfo is not None
    print("  ✓ UTC conversion works")
    
    # Test Discord timestamp formatting
    timestamp = timeutil.format_discord_timestamp(utc_dt, 'F')
    assert timestamp.startswith("<t:") and timestamp.endswith(":F>")
    print("  ✓ Discord timestamp formatting works")
    
    print("  ✓ Time utility tests passed!")

def test_embeds():
    """Test embed functionality."""
    print("\n📋 Testing Embed Generation...")
    
    # Test session embed
    session_data = {
        'id': 1,
        'game_mode': '5v5',
        'description': 'Test session',
        'status': 'OPEN',
        'scheduled_time': '2024-12-25T19:30:00+00:00',
        'timezone': 'America/New_York',
        'max_rank_diff': 5
    }
    
    embed = embeds.session_embed(session_data, 3, {"tank": 1, "dps": 1, "support": 1})
    assert embed.title.startswith("🎮 Overwatch")
    assert "Session #1" in embed.title
    print("  ✓ Session embed generation works")
    
    # Test profile embed
    user_data = {
        'username': 'TestUser',
        'timezone': 'America/New_York',
        'preferred_roles': '["tank", "support"]'
    }
    
    accounts = [{
        'account_name': 'TestPlayer#1234',
        'is_primary': True,
        'tank_rank': 'gold',
        'tank_division': 3,
        'dps_rank': None,
        'dps_division': None,
        'support_rank': 'platinum',
        'support_division': 1
    }]
    
    profile_embed = embeds.profile_embed(user_data, accounts)
    assert profile_embed.title.startswith("👤 Profile:")
    print("  ✓ Profile embed generation works")
    
    # Test error embed
    error_embed = embeds.error_embed("Test Error", "This is a test error message")
    assert error_embed.title.startswith("❌")
    print("  ✓ Error embed generation works")
    
    print("  ✓ Embed tests passed!")

async def main():
    """Run all tests."""
    print("🚀 Starting Overwatch Discord Bot Functionality Tests\n")
    
    try:
        # Run tests
        await test_database()
        test_models()
        test_timeutil()
        test_embeds()
        
        print("\n🎉 All tests passed! The bot is ready to deploy!")
        print("\n📝 Next steps:")
        print("   1. Set your BOT_TOKEN in .env file")
        print("   2. Invite the bot to your Discord server")
        print("   3. Run: python bot.py")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)