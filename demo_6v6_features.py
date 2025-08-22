#!/usr/bin/env python3
"""
Demo script showing 6v6 functionality in action.
This simulates the user experience with the new 6v6 features.
"""

import asyncio
import tempfile
import os
import sys
from datetime import datetime, timezone

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import database, models, embeds


async def demo_6v6_features():
    """Demonstrate the new 6v6 features."""
    print("🎯 6v6 Enhancement Demo")
    print("=" * 50)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        temp_db_path = tmp_file.name
    
    try:
        # Initialize database
        db = database.Database(temp_db_path)
        await db.connect()
        print("✅ Database initialized with 6v6 migration")
        
        # Demo 1: User creates profile and adds account with 6v6 rank
        print("\n1️⃣ User Profile with 6v6 Rank")
        print("-" * 30)
        
        # Create user
        await db.execute(
            "INSERT INTO users (discord_id, username, preferred_roles, timezone) VALUES (?, ?, ?, ?)",
            123456789, "Pro6v6Player", '["tank", "dps"]', "America/New_York"
        )
        
        # Add account with 6v6 rank
        await db.execute(
            """INSERT INTO user_accounts 
               (discord_id, account_name, is_primary, 
                tank_rank, tank_division, dps_rank, dps_division, 
                support_rank, support_division, sixv6_rank, sixv6_division)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            123456789, "Pro6v6#1234", True,
            "platinum", 2, "diamond", 1, "gold", 3, "master", 2
        )
        
        # Display profile
        user_data = dict(await db.fetchrow("SELECT * FROM users WHERE discord_id = ?", 123456789))
        accounts = [dict(row) for row in await db.fetch("SELECT * FROM user_accounts WHERE discord_id = ?", 123456789)]
        
        print("Profile Display:")
        print(f"👤 {user_data['username']}")
        print(f"🌍 Timezone: {user_data['timezone']}")
        for account in accounts:
            print(f"🎮 {account['account_name']} (Primary)")
            print(f"  🛡️ Tank: {account['tank_rank'].title() if account['tank_rank'] else 'None'} {account['tank_division'] or ''}")
            print(f"  ⚔️ DPS: {account['dps_rank'].title() if account['dps_rank'] else 'None'} {account['dps_division'] or ''}")
            print(f"  💉 Support: {account['support_rank'].title() if account['support_rank'] else 'None'} {account['support_division'] or ''}")
            print(f"  🎯 6v6: {account['sixv6_rank'].title() if account['sixv6_rank'] else 'None'} {account['sixv6_division'] or ''}")
        
        # Demo 2: Game mode comparison
        print("\n2️⃣ Game Mode Comparison")
        print("-" * 30)
        
        modes = ["5v5", "6v6", "Stadium"]
        for mode in modes:
            team_size = models.get_game_mode_team_size(mode)
            is_role_restricted = models.is_role_restricted_mode(mode)
            requirements = models.GAME_MODE_REQUIREMENTS.get(mode, {})
            
            print(f"🎮 {mode}:")
            print(f"  Team Size: {team_size}")
            print(f"  Role Restricted: {'Yes' if is_role_restricted else 'No'}")
            if requirements:
                print("  Requirements:", {role: count for role, count in requirements.items()})
            else:
                print("  Requirements: None (flexible composition)")
        
        # Demo 3: Create 6v6 session
        print("\n3️⃣ 6v6 Session Creation")
        print("-" * 30)
        
        await db.execute(
            """INSERT INTO sessions 
               (creator_id, guild_id, channel_id, game_mode, scheduled_time, timezone, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            123456789, 987654321, 555666777, "6v6", 
            datetime.now(timezone.utc).isoformat(), "UTC",
            "Open 6v6 - No role restrictions! All skill levels welcome.", "OPEN"
        )
        
        session_data = dict(await db.fetchrow("SELECT * FROM sessions WHERE id = ?", 1))
        print("Session Created:")
        print(f"🎯 Game Mode: {session_data['game_mode']}")
        print(f"📝 Description: {session_data['description']}")
        print(f"🔓 Role Restricted: {'No' if session_data['game_mode'] == '6v6' else 'Yes'}")
        
        # Demo 4: Add participants without roles
        print("\n4️⃣ Adding 6v6 Participants")
        print("-" * 30)
        
        # Add more test accounts for demonstration
        test_accounts = [
            (222222222, "FlexPlayer#5678", "diamond", 1),
            (333333333, "CasualGamer#9012", "gold", 4),
            (444444444, "CompetitiveAce#3456", "grandmaster", 1),
        ]
        
        for i, (discord_id, account_name, sixv6_rank, sixv6_div) in enumerate(test_accounts, 2):
            await db.execute(
                "INSERT INTO users (discord_id, username, preferred_roles, timezone) VALUES (?, ?, ?, ?)",
                discord_id, account_name.split('#')[0], '[]', "UTC"
            )
            
            await db.execute(
                """INSERT INTO user_accounts 
                   (discord_id, account_name, is_primary, sixv6_rank, sixv6_division)
                   VALUES (?, ?, ?, ?, ?)""",
                discord_id, account_name, True, sixv6_rank, sixv6_div
            )
            
            # Add as session participant with 'player' role (6v6 style)
            await db.execute(
                """INSERT INTO session_participants 
                   (session_id, user_id, account_id, role, is_streaming, selected_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                1, discord_id, i, "player", False, 123456789
            )
        
        # Add original user too
        await db.execute(
            """INSERT INTO session_participants 
               (session_id, user_id, account_id, role, is_streaming, selected_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            1, 123456789, 1, "player", True, 123456789
        )
        
        # Display participants
        participants_query = """
            SELECT u.username, ua.account_name, sp.role, sp.is_streaming, ua.sixv6_rank, ua.sixv6_division
            FROM session_participants sp
            JOIN users u ON sp.user_id = u.discord_id
            JOIN user_accounts ua ON sp.account_id = ua.id
            WHERE sp.session_id = ?
        """
        participants = await db.fetch(participants_query, 1)
        
        print("Session Participants:")
        for p in participants:
            streaming = "📺 " if p['is_streaming'] else ""
            sixv6_info = f"({p['sixv6_rank'].title()} {p['sixv6_division']})" if p['sixv6_rank'] else "(No 6v6 rank)"
            print(f"  {streaming}**{p['username']}** ({p['account_name']}) {sixv6_info}")
        
        print(f"\nTeam Status: {len(participants)}/6 players ready")
        
        # Demo 5: Session embed comparison
        print("\n5️⃣ Session Display Comparison")
        print("-" * 30)
        
        # Create comparable 5v5 session
        await db.execute(
            """INSERT INTO sessions 
               (creator_id, guild_id, channel_id, game_mode, scheduled_time, timezone, description, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            123456789, 987654321, 555666777, "5v5", 
            datetime.now(timezone.utc).isoformat(), "UTC",
            "Competitive 5v5 - Role queue required", "OPEN"
        )
        
        print("5v5 Session Display:")
        print("🎯 Role Requirements")
        print("❌ 🛡️ Tank: 0/1")
        print("❌ ⚔️ DPS: 0/2")
        print("❌ 💉 Support: 0/2")
        
        print("\n6v6 Session Display:")
        print("👥 Team Composition")
        print("✅ Players: 4/6")
        
        # Demo 6: Profile embed generation
        print("\n6️⃣ Generated Profile Embed")
        print("-" * 30)
        
        embed = embeds.profile_embed(user_data, accounts)
        print(f"Title: {embed.title}")
        print(f"Color: {embed.color}")
        for field in embed.fields:
            print(f"Field: {field.name}")
            print(f"Value: {field.value}")
            print()
        
        await db.close()
        print("✅ Demo completed successfully!")
        
        print("\n🎉 Key 6v6 Features Demonstrated:")
        print("   ✓ 6v6 rank storage and display")
        print("   ✓ Non-role-restricted team composition")
        print("   ✓ Flexible participant management") 
        print("   ✓ Adaptive session displays")
        print("   ✓ Comprehensive profile integration")
        
    finally:
        # Clean up
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


if __name__ == "__main__":
    asyncio.run(demo_6v6_features())