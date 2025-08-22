#!/usr/bin/env python3
"""Test script for new 6v6 functionality."""

import asyncio
import os
import tempfile
import sys
from datetime import datetime, timezone, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import database, models, embeds


async def test_6v6_database_migration():
    """Test that the database migration adds 6v6 rank columns."""
    print("🔧 Testing 6v6 database migration...")
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        temp_db_path = tmp_file.name
    
    try:
        # Initialize database with migrations
        test_db = database.Database(temp_db_path)
        await test_db.connect()
        
        # Check if 6v6 columns exist
        cursor = await test_db.conn.execute("PRAGMA table_info(user_accounts)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        assert 'sixv6_rank' in column_names, "sixv6_rank column missing"
        assert 'sixv6_division' in column_names, "sixv6_division column missing"
        
        # Test inserting a user account with 6v6 rank
        await test_db.execute(
            """INSERT INTO users (discord_id, username, preferred_roles, timezone)
               VALUES (?, ?, ?, ?)""",
            123456789, "TestUser", "[]", "UTC"
        )
        
        await test_db.execute(
            """INSERT INTO user_accounts 
               (discord_id, account_name, is_primary, tank_rank, tank_division,
                dps_rank, dps_division, support_rank, support_division, 
                sixv6_rank, sixv6_division)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            123456789, "TestPlayer#1234", True,
            "gold", 3, "platinum", 2, "silver", 4,
            "diamond", 1
        )
        
        # Verify the data was inserted correctly
        account = await test_db.fetchrow(
            "SELECT * FROM user_accounts WHERE discord_id = ?",
            123456789
        )
        
        assert account is not None, "Account not found"
        assert account['sixv6_rank'] == "diamond", f"Expected diamond, got {account['sixv6_rank']}"
        assert account['sixv6_division'] == 1, f"Expected 1, got {account['sixv6_division']}"
        
        await test_db.close()
        print("  ✓ Database migration works correctly")
        print("  ✓ 6v6 rank storage works correctly")
        
    finally:
        # Clean up
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


async def test_6v6_models():
    """Test the new 6v6 model functions."""
    print("🎮 Testing 6v6 model functions...")
    
    # Test game mode team size
    assert models.get_game_mode_team_size("5v5") == 5
    assert models.get_game_mode_team_size("6v6") == 6
    assert models.get_game_mode_team_size("Stadium") == 6
    
    # Test role restriction check
    assert models.is_role_restricted_mode("5v5") == True
    assert models.is_role_restricted_mode("6v6") == False
    assert models.is_role_restricted_mode("Stadium") == True
    
    # Test game mode requirements for 6v6 (should be empty)
    sixv6_requirements = models.GAME_MODE_REQUIREMENTS.get("6v6", {})
    assert len(sixv6_requirements) == 0, "6v6 should have no role requirements"
    
    print("  ✓ Game mode team sizes correct")
    print("  ✓ Role restriction checks work")
    print("  ✓ 6v6 requirements are empty (not role-restricted)")


async def test_6v6_embeds():
    """Test that embeds handle 6v6 sessions correctly."""
    print("📋 Testing 6v6 embed generation...")
    
    # Test session data for 6v6
    session_data = {
        'id': 1,
        'game_mode': '6v6',
        'description': 'Test 6v6 session',
        'status': 'OPEN',
        'scheduled_time': datetime.now(timezone.utc).isoformat(),
        'timezone': 'UTC',
        'max_rank_diff': None
    }
    
    # Test participants for 6v6 (no roles)
    participants = [
        {
            'username': 'Player1',
            'account_name': 'Account1#1234',
            'role': 'player',  # 6v6 uses 'player' instead of specific roles
            'is_streaming': False
        },
        {
            'username': 'Player2',
            'account_name': 'Account2#5678',
            'role': 'player',
            'is_streaming': True
        }
    ]
    
    # Generate embed
    embed = embeds.session_embed(session_data, queue_count=3, participants=participants)
    
    # Check that the embed was created
    assert embed is not None, "Embed should not be None"
    assert "6v6" in embed.title, "Title should contain 6v6"
    
    # Check that team composition shows player count instead of roles
    found_team_composition = False
    for field in embed.fields:
        if field.name == "👥 Team Composition":
            found_team_composition = True
            assert "Players: 2/6" in field.value, f"Expected 'Players: 2/6', got '{field.value}'"
            break
    
    assert found_team_composition, "Should have Team Composition field for 6v6"
    
    # Check that participants don't show role emojis
    for field in embed.fields:
        if field.name.startswith("✅ Accepted Players"):
            # Should not contain role emojis like 🛡️ ⚔️ 💉
            assert "🛡️" not in field.value, "Should not show tank emoji for 6v6"
            assert "⚔️" not in field.value, "Should not show DPS emoji for 6v6"
            assert "💉" not in field.value, "Should not show support emoji for 6v6"
            break
    
    print("  ✓ 6v6 session embed generates correctly")
    print("  ✓ Team composition shows player count instead of roles")
    print("  ✓ Participants don't show role emojis")


async def test_6v6_profile_display():
    """Test that user profiles display 6v6 ranks."""
    print("👤 Testing 6v6 profile display...")
    
    user_data = {
        'username': 'TestUser',
        'timezone': 'America/New_York',
        'preferred_roles': '["tank", "dps"]'
    }
    
    accounts = [
        {
            'account_name': 'MainAccount#1234',
            'is_primary': True,
            'tank_rank': 'gold',
            'tank_division': 3,
            'dps_rank': 'platinum',
            'dps_division': 2,
            'support_rank': 'silver',
            'support_division': 4,
            'sixv6_rank': 'diamond',
            'sixv6_division': 1
        }
    ]
    
    embed = embeds.profile_embed(user_data, accounts)
    
    # Check that the embed contains 6v6 rank
    found_sixv6_rank = False
    for field in embed.fields:
        if "MainAccount#1234" in field.name:
            assert "🎯 6v6: Diamond💎 1" in field.value, f"Should show 6v6 rank, got: {field.value}"
            found_sixv6_rank = True
            break
    
    assert found_sixv6_rank, "Should display 6v6 rank in profile"
    
    print("  ✓ Profile displays 6v6 ranks correctly")


async def main():
    """Run all 6v6 functionality tests."""
    print("🚀 Starting 6v6 Enhancement Tests\n")
    
    try:
        await test_6v6_database_migration()
        print()
        
        await test_6v6_models()
        print()
        
        await test_6v6_embeds()
        print()
        
        await test_6v6_profile_display()
        print()
        
        print("🎉 All 6v6 enhancement tests passed!")
        print("\n📝 6v6 Features tested:")
        print("   ✓ Database migration adds 6v6 rank columns")
        print("   ✓ 6v6 rank storage and retrieval")
        print("   ✓ Game mode team size calculations")
        print("   ✓ Role restriction detection (6v6 = not restricted)")
        print("   ✓ Session embeds show player count instead of roles")
        print("   ✓ Participant display without role emojis")
        print("   ✓ Profile embeds include 6v6 ranks")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)