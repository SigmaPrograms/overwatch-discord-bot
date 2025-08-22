#!/usr/bin/env python3
"""
Visual demonstration of the new queue management interface.
This script shows what the Discord embeds would look like.
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import embeds, models, timeutil

def print_embed(embed, title="EMBED"):
    """Print a Discord embed in a readable format."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")
    print(f"📋 {embed.title}")
    print(f"📝 {embed.description}")
    print()
    
    for field in embed.fields:
        print(f"🔹 {field.name}")
        print(f"   {field.value}")
        print()
    
    if embed.footer:
        print(f"💬 {embed.footer.text}")
    print(f"{'='*60}")

async def demonstrate_queue_management():
    """Show visual examples of the queue management interface."""
    
    print("🎮 OVERWATCH DISCORD BOT - QUEUE MANAGEMENT DEMO")
    print("This demonstrates what session creators will see when managing their sessions.")
    
    # Sample session data
    session_data = {
        'id': 42,
        'game_mode': '5v5', 
        'description': 'Competitive 5v5 - Diamond level players preferred',
        'status': 'OPEN',
        'scheduled_time': '2024-12-25T19:30:00+00:00',
        'timezone': 'America/New_York',
        'max_rank_diff': 5
    }
    
    # Sample accepted participants
    participants = [
        {
            'username': 'ProPlayer1',
            'account_name': 'ProPlayer#1234',
            'role': 'tank',
            'is_streaming': True
        },
        {
            'username': 'FlexSupport',
            'account_name': 'FlexGod#5678',
            'role': 'support', 
            'is_streaming': False
        }
    ]
    
    # Sample queue entries
    queue_entries = [
        {
            'username': 'DPSMain99',
            'account_name': 'DPSMain#9999',
            'is_streaming': False,
            'preferred_roles': ['dps', 'support'],
            'note': 'Looking for DPS primarily but can flex support'
        },
        {
            'username': 'StreamerTank',
            'account_name': 'StreamTank#1111', 
            'is_streaming': True,
            'preferred_roles': ['tank'],
            'note': None
        },
        {
            'username': 'FlexPlayer',
            'account_name': 'FlexKing#2222',
            'is_streaming': False,
            'preferred_roles': ['tank', 'dps', 'support'],
            'note': 'Can fill any role needed'
        }
    ]
    
    print("\n1️⃣  MAIN SESSION EMBED (What everyone sees)")
    print("   This is displayed in the channel for all users to see and interact with.")
    
    # Create main session embed
    session_embed = embeds.session_embed(session_data, len(queue_entries) + len(participants))
    print_embed(session_embed, "PUBLIC SESSION EMBED")
    
    print("\n2️⃣  MANAGEMENT DASHBOARD (Session creator only)")
    print("   This is shown when the creator uses /manage-session (ephemeral).")
    
    # Create management embed mockup
    mgmt_embed_content = f"""🛠️ Managing Session #{session_data['id']}

**Game Mode:** {session_data['game_mode']}
**Status:** {session_data['status']}
**Description:** {session_data['description']}

⏰ Scheduled Time
{timeutil.format_discord_timestamp(datetime.fromisoformat(session_data['scheduled_time']), 'F')}
({timeutil.format_discord_timestamp(datetime.fromisoformat(session_data['scheduled_time']), 'R')})

✅ Accepted Players (2)
📺 🛡️ **ProPlayer1** (ProPlayer#1234)
   💉 **FlexSupport** (FlexGod#5678)

🎯 Team Composition
✅ 🛡️ Tank: 1/1
❌ ⚔️ Dps: 0/2
✅ 💉 Support: 1/2

⏳ Queue (3 waiting)
**DPSMain99** (DPSMain#9999) - dps, support
📺 **StreamerTank** (StreamTank#1111) - tank
**FlexPlayer** (FlexKing#2222) - tank, dps, support

Use the buttons below to manage your session.

🔒 Open/Close Session  👥 Manage Queue  🗑️ Cancel Session"""
    
    print(mgmt_embed_content)
    
    print("\n3️⃣  QUEUE MANAGEMENT VIEW (Creator clicks 'Manage Queue')")
    print("   Detailed view of all players in queue with full account information.")
    
    queue_mgmt_content = f"""👥 Queue Management - Session #42

Review players in queue and accept them into the session.

1. **DPSMain99**
🎯 Roles: ⚔️ Dps, 💉 Support

🎮 **Accounts:**
• **DPSMain#9999** (Primary)
  ⚔️ Dps: Diamond💎 2
  💉 Support: Platinum🟦 1

2. **StreamerTank**
📺 Streaming
🎯 Roles: 🛡️ Tank

🎮 **Accounts:**
• **StreamTank#1111** (Primary)
  🛡️ Tank: Master🟧 3
• **TankSmurf#3333**
  🛡️ Tank: Gold🟨 1

3. **FlexPlayer**
🎯 Roles: 🛡️ Tank, ⚔️ Dps, 💉 Support

🎮 **Accounts:**
• **FlexKing#2222** (Primary)
  🛡️ Tank: Platinum🟦 4
  ⚔️ Dps: Diamond💎 1
  💉 Support: Gold🟨 3

Page 1/1 • 3 players in queue

[Select Player Dropdown] [Previous] [Next] [🔄 Refresh]"""
    
    print(queue_mgmt_content)
    
    print("\n4️⃣  PLAYER ACCEPTANCE VIEW (Creator selects a player)")
    print("   Detailed view for accepting a specific player into the session.")
    
    accept_view_content = f"""👤 Accept Player: DPSMain99

Select an account and role to accept this player.

🎯 Preferred Roles: ⚔️ Dps, 💉 Support

🎮 Available Accounts
**DPSMain#9999** (Primary)
  ⚔️ Dps: Diamond💎 2
  💉 Support: Platinum🟦 1

✅ Current Selection
Account: DPSMain#9999
Role: ⚔️ Dps

[Account Dropdown] [Role Dropdown]
✅ Accept Player  ❌ Reject Player"""
    
    print(accept_view_content)
    
    print("\n5️⃣  SUCCESS CONFIRMATION")
    print("   What the creator sees after accepting a player.")
    
    print("✅ Accepted **DPSMain99** (DPSMain#9999) as ⚔️ Dps!")
    
    print("\n6️⃣  UPDATED MANAGEMENT DASHBOARD")
    print("   The dashboard updates to show the new team composition.")
    
    updated_mgmt_content = f"""✅ Accepted Players (3)
📺 🛡️ **ProPlayer1** (ProPlayer#1234)
   💉 **FlexSupport** (FlexGod#5678)
   ⚔️ **DPSMain99** (DPSMain#9999)

🎯 Team Composition
✅ 🛡️ Tank: 1/1
✅ ⚔️ Dps: 1/2
✅ 💉 Support: 1/2

⏳ Queue (2 waiting)
📺 **StreamerTank** (StreamTank#1111) - tank
**FlexPlayer** (FlexKing#2222) - tank, dps, support"""
    
    print(updated_mgmt_content)
    
    print(f"\n{'='*60}")
    print("🎉 QUEUE MANAGEMENT DEMO COMPLETE")
    print("The session creator now has full control over team building!")
    print("Players can see their ranks and accounts are being considered.")
    print("No more anonymous queue - complete transparency and control.")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(demonstrate_queue_management())