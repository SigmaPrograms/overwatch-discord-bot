#!/usr/bin/env python3
"""
Test script for the new queue management functionality.

This script demonstrates the complete workflow:
1. Create users with accounts and ranks
2. Create a session
3. Add users to the queue  
4. Test the acceptance workflow
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import database, models, timeutil

async def test_queue_management():
    """Test the new queue management functionality."""
    print("🎯 Testing Queue Management Functionality...")
    
    # Use test database
    test_db = database.Database("test_queue.db")
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
        
        print(f"  ✓ Created {len(users)} test users")
        
        # Create accounts for users
        accounts = [
            # Session creator accounts
            (123456789, "Creator#1234", True, "gold", 2, "platinum", 1, "diamond", 3),
            (123456789, "CreatorAlt#5678", False, "silver", 4, None, None, "gold", 2),
            
            # Player One accounts
            (987654321, "PlayerOne#1111", True, None, None, "master", 2, "diamond", 1),
            (987654321, "PlayerOneAlt#2222", False, "bronze", 5, "grandmaster", 1, "platinum", 4),
            
            # Player Two accounts  
            (111222333, "PlayerTwo#3333", True, "platinum", 3, "gold", 4, None, None),
            
            # Player Three accounts
            (444555666, "PlayerThree#4444", True, None, None, None, None, "champion", 1)
        ]
        
        for discord_id, account_name, is_primary, tank_rank, tank_div, dps_rank, dps_div, support_rank, support_div in accounts:
            await test_db.execute(
                """INSERT OR IGNORE INTO user_accounts 
                   (discord_id, account_name, is_primary, tank_rank, tank_division, dps_rank, dps_division, support_rank, support_division)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                discord_id, account_name, is_primary, tank_rank, tank_div, dps_rank, dps_div, support_rank, support_div
            )
        
        print(f"  ✓ Created {len(accounts)} test accounts with ranks")
        
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
        
        # Add players to queue
        queue_players = [
            (987654321, '[1, 2]', '["dps", "support"]', False, "Looking for DPS primarily"),
            (111222333, '[3]', '["tank", "dps"]', True, "Can flex tank/dps"),
            (444555666, '[4]', '["support"]', False, None)
        ]
        
        for user_id, account_ids, preferred_roles, is_streaming, note in queue_players:
            await test_db.execute(
                """INSERT INTO session_queue 
                   (session_id, user_id, account_ids, preferred_roles, is_streaming, note)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                session_id, user_id, account_ids, preferred_roles, is_streaming, note
            )
        
        print(f"  ✓ Added {len(queue_players)} players to queue")
        
        # Test queue retrieval with full details
        queue_entries = await test_db.fetch(
            """SELECT sq.*, u.username, ua.account_name 
               FROM session_queue sq
               JOIN users u ON sq.user_id = u.discord_id
               LEFT JOIN user_accounts ua ON u.discord_id = ua.discord_id AND ua.is_primary = 1
               WHERE sq.session_id = ?
               ORDER BY sq.joined_at ASC""",
            session_id
        )
        
        print(f"  ✓ Retrieved queue with {len(queue_entries)} entries")
        
        # Display queue information
        print("\n  📋 Queue Details:")
        for i, entry in enumerate(queue_entries, 1):
            username = entry['username']
            account_name = entry['account_name'] or "No Primary Account"
            preferred_roles = models.parse_json_field(entry['preferred_roles'])
            is_streaming = entry['is_streaming']
            note = entry['note']
            
            streaming_indicator = "📺" if is_streaming else "  "
            roles_str = ", ".join(preferred_roles) if preferred_roles else "No preference"
            
            print(f"    {i}. {streaming_indicator} {username} ({account_name})")
            print(f"       Roles: {roles_str}")
            if note:
                print(f"       Note: {note}")
            print()
        
        # Test accepting a player
        test_player = queue_entries[0]  # PlayerOne
        print(f"  🎯 Testing acceptance of {test_player['username']}...")
        
        # Get player's accounts
        player_accounts = await test_db.fetch(
            """SELECT * FROM user_accounts 
               WHERE discord_id = ? 
               ORDER BY is_primary DESC, account_name ASC""",
            test_player['user_id']
        )
        
        print(f"    📋 {test_player['username']} has {len(player_accounts)} accounts:")
        for account in player_accounts:
            account_name = account['account_name']
            is_primary = account['is_primary']
            primary_str = " (Primary)" if is_primary else ""
            
            print(f"      • {account_name}{primary_str}")
            
            # Show ranks
            for role in ['tank', 'dps', 'support']:
                rank = account[f'{role}_rank']
                division = account[f'{role}_division']
                if rank and division:
                    emoji = models.ROLE_EMOJIS.get(role, "")
                    rank_display = models.get_rank_display(rank)
                    print(f"        {emoji} {role.title()}: {rank_display} {division}")
        
        # Accept the player (using their primary account as DPS)
        selected_account = player_accounts[0]  # Primary account
        selected_role = "dps"
        
        await test_db.execute(
            """INSERT INTO session_participants 
               (session_id, user_id, account_id, role, is_streaming, selected_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            session_id, test_player['user_id'], selected_account['id'],
            selected_role, test_player['is_streaming'], 123456789
        )
        
        # Remove from queue
        await test_db.execute(
            "DELETE FROM session_queue WHERE session_id = ? AND user_id = ?",
            session_id, test_player['user_id']
        )
        
        print(f"    ✅ Accepted {test_player['username']} ({selected_account['account_name']}) as {selected_role}")
        
        # Show updated session state
        participants = await test_db.fetch(
            """SELECT sp.*, u.username, ua.account_name 
               FROM session_participants sp
               JOIN users u ON sp.user_id = u.discord_id
               JOIN user_accounts ua ON sp.account_id = ua.id
               WHERE sp.session_id = ?
               ORDER BY sp.selected_at ASC""",
            session_id
        )
        
        remaining_queue = await test_db.fetch(
            """SELECT sq.*, u.username, ua.account_name 
               FROM session_queue sq
               JOIN users u ON sq.user_id = u.discord_id
               LEFT JOIN user_accounts ua ON u.discord_id = ua.discord_id AND ua.is_primary = 1
               WHERE sq.session_id = ?
               ORDER BY sq.joined_at ASC""",
            session_id
        )
        
        print(f"\n  ✅ Final Session State:")
        print(f"    Accepted Players: {len(participants)}")
        for participant in participants:
            username = participant['username']
            account_name = participant['account_name']
            role = participant['role']
            is_streaming = participant['is_streaming']
            
            streaming_indicator = "📺" if is_streaming else "  "
            role_emoji = models.ROLE_EMOJIS.get(role, "")
            
            print(f"      {streaming_indicator} {role_emoji} {username} ({account_name})")
        
        print(f"    Remaining in Queue: {len(remaining_queue)}")
        for entry in remaining_queue:
            username = entry['username']
            print(f"      ⏳ {username}")
        
        # Test game mode requirements fulfillment
        game_mode = "5v5"
        requirements = models.GAME_MODE_REQUIREMENTS[game_mode]
        role_counts = {"tank": 0, "dps": 0, "support": 0}
        
        for participant in participants:
            role = participant['role']
            role_counts[role] += 1
        
        print(f"\n  🎯 {game_mode} Requirements Check:")
        for role, needed in requirements.items():
            if needed > 0:
                accepted = role_counts.get(role, 0)
                emoji = models.ROLE_EMOJIS.get(role, "")
                status_emoji = "✅" if accepted >= needed else "❌"
                print(f"    {status_emoji} {emoji} {role.title()}: {accepted}/{needed}")
        
        print("\n  ✓ Queue management functionality test completed!")
        
    finally:
        await test_db.close()
        # Clean up test database
        for file in ["test_queue.db", "test_queue.db-wal", "test_queue.db-shm"]:
            if os.path.exists(file):
                os.remove(file)

async def main():
    """Run the queue management test."""
    print("🚀 Starting Queue Management Test\n")
    
    try:
        await test_queue_management()
        print("\n🎉 All queue management tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)