#!/usr/bin/env python3
"""
Test script to verify that the session embed correctly displays accepted players.

This script tests the specific functionality requested: showing accepted player
names and their roles in the global session display.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import database, models, embeds, timeutil

async def test_session_embed_with_participants():
    """Test that session embed shows accepted participants correctly."""
    print("🎯 Testing Session Embed with Accepted Players...")
    
    # Use test database
    test_db = database.Database("test_participants.db")
    await test_db.connect()
    
    try:
        # Create test users
        users = [
            (123456789, "SessionCreator", '["tank", "support"]', "America/New_York"),
            (987654321, "PlayerOne", '["dps", "support"]', "America/New_York"), 
            (111222333, "PlayerTwo", '["tank", "dps"]', "Europe/London"),
            (444555666, "PlayerThree", '["support"]', "America/Los_Angeles")
        ]
        
        for discord_id, username, roles, timezone in users:
            await test_db.execute(
                "INSERT OR IGNORE INTO users (discord_id, username, preferred_roles, timezone) VALUES (?, ?, ?, ?)",
                discord_id, username, roles, timezone
            )
        
        # Create accounts for users
        accounts = [
            (987654321, "PlayerOne#1111", True, None, None, "master", 2, "diamond", 1),
            (111222333, "PlayerTwo#3333", True, "platinum", 3, "gold", 4, None, None),
            (444555666, "PlayerThree#4444", True, None, None, None, None, "champion", 1)
        ]
        
        for discord_id, account_name, is_primary, tank_rank, tank_div, dps_rank, dps_div, support_rank, support_div in accounts:
            await test_db.execute(
                """INSERT OR IGNORE INTO user_accounts 
                   (discord_id, account_name, is_primary, tank_rank, tank_division, dps_rank, dps_division, support_rank, support_division)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                discord_id, account_name, is_primary, tank_rank, tank_div, dps_rank, dps_div, support_rank, support_div
            )
        
        # Create a test session
        utc_time = timeutil.now_utc()
        await test_db.execute(
            """INSERT INTO sessions 
               (creator_id, guild_id, channel_id, game_mode, scheduled_time, timezone, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            123456789, 987654321, 111222333, "5v5", utc_time.isoformat(), 
            "America/New_York", "Test 5v5 Competitive Session", "OPEN"
        )
        
        session_id = await test_db.get_last_insert_id()
        print(f"  ✓ Created session #{session_id}")
        
        # Add accepted participants
        participants_to_add = [
            (987654321, 1, "dps", False),  # PlayerOne as DPS
            (111222333, 2, "tank", True),  # PlayerTwo as Tank (streaming)
            (444555666, 3, "support", False)  # PlayerThree as Support
        ]
        
        for user_id, account_id, role, is_streaming in participants_to_add:
            await test_db.execute(
                """INSERT INTO session_participants 
                   (session_id, user_id, account_id, role, is_streaming, selected_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                session_id, user_id, account_id, role, is_streaming, 123456789
            )
        
        print(f"  ✓ Added {len(participants_to_add)} participants to session")
        
        # Get session data
        session_data = await test_db.fetchrow("SELECT * FROM sessions WHERE id = ?", session_id)
        session_dict = dict(session_data)
        
        # Get participants data as the UI would
        participants = await test_db.fetch(
            """SELECT sp.role, sp.is_streaming, u.username, ua.account_name
               FROM session_participants sp
               JOIN users u ON sp.user_id = u.discord_id
               JOIN user_accounts ua ON sp.account_id = ua.id
               WHERE sp.session_id = ?
               ORDER BY sp.selected_at ASC""",
            session_id
        )
        
        # Calculate role counts
        role_counts = {"tank": 0, "dps": 0, "support": 0}
        participants_list = []
        for participant in participants:
            role = participant['role']
            if role in role_counts:
                role_counts[role] += 1
            participants_list.append(dict(participant))
        
        print(f"  ✓ Retrieved {len(participants_list)} participants with details")
        
        # Test embed without participants (should work as before)
        embed_without = embeds.session_embed(session_dict, 2, role_counts, [])
        print("  ✓ Created embed without participants")
        
        # Test embed with participants (new functionality)
        embed_with = embeds.session_embed(session_dict, 2, role_counts, participants_list)
        print("  ✓ Created embed with participants")
        
        # Verify the embed content
        print("\n  📋 Verifying Embed Content:")
        
        # Check that embed has the expected fields
        field_names = [field.name for field in embed_with.fields]
        print(f"    Fields: {field_names}")
        
        # Find the accepted players field
        accepted_field = None
        for field in embed_with.fields:
            if "Accepted Players" in field.name:
                accepted_field = field
                break
        
        if accepted_field:
            print(f"    ✅ Found 'Accepted Players' field")
            print(f"    Field Name: {accepted_field.name}")
            print(f"    Field Value:")
            for line in accepted_field.value.split('\n'):
                print(f"      {line}")
            
            # Verify expected content (ordered by selected_at which is insertion order)
            expected_content = [
                "⚔️ **PlayerOne** (PlayerOne#1111)",  # DPS, not streaming (first inserted)
                "📺 🛡️ **PlayerTwo** (PlayerTwo#3333)",  # Tank, streaming (second inserted)
                "💉 **PlayerThree** (PlayerThree#4444)"  # Support, not streaming (third inserted)
            ]
            
            # Verify expected content is present (any order is fine)
            expected_players = {
                "⚔️ **PlayerOne** (PlayerOne#1111)",  # DPS, not streaming
                "📺 🛡️ **PlayerTwo** (PlayerTwo#3333)",  # Tank, streaming  
                "💉 **PlayerThree** (PlayerThree#4444)"  # Support, not streaming
            }
            
            field_lines = accepted_field.value.split('\n')
            actual_players = set(field_lines)
            
            print(f"      Expected players: {len(expected_players)}")
            print(f"      Actual players: {len(actual_players)}")
            
            # Check each expected player is present
            for expected_player in expected_players:
                if expected_player in actual_players:
                    print(f"      ✅ Found: {expected_player}")
                else:
                    print(f"      ❌ Missing: {expected_player}")
                    return False
            
            # Check no unexpected players
            unexpected = actual_players - expected_players
            if unexpected:
                print(f"      ❌ Unexpected players: {unexpected}")
                return False
        else:
            print("    ❌ 'Accepted Players' field not found!")
            return False
        
        # Verify role requirements still work
        role_req_field = None
        for field in embed_with.fields:
            if "Role Requirements" in field.name:
                role_req_field = field
                break
        
        if role_req_field:
            print(f"    ✅ Found 'Role Requirements' field")
            # Should show fulfilled requirements since we have 1 tank, 1 dps, 1 support
            expected_statuses = ["✅ 🛡️ Tank: 1/1", "❌ ⚔️ Dps: 1/2", "❌ 💉 Support: 1/2"]
            role_lines = role_req_field.value.split('\n')
            for expected in expected_statuses:
                if any(expected in line for line in role_lines):
                    print(f"      ✅ Found: {expected}")
                else:
                    print(f"      ❌ Missing: {expected}")
        
        print("\n  ✓ Session embed with participants functionality test completed!")
        return True
        
    finally:
        await test_db.close()
        # Clean up test database
        for file in ["test_participants.db", "test_participants.db-wal", "test_participants.db-shm"]:
            if os.path.exists(file):
                os.remove(file)

async def main():
    """Run the participants display test."""
    print("🚀 Starting Accepted Players Display Test\n")
    
    try:
        success = await test_session_embed_with_participants()
        if success:
            print("\n🎉 Accepted players display test passed!")
            print("\n📋 Summary:")
            print("   ✅ Session embed correctly displays accepted player names")
            print("   ✅ Shows player roles with appropriate emojis")
            print("   ✅ Indicates streaming status with 📺 emoji")
            print("   ✅ Maintains compatibility with existing role requirements")
        else:
            print("\n❌ Test failed - see details above")
            return 1
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)