# Queue Management Feature - User Guide

## Overview

The new queue management system allows session creators to review and accept players into their Overwatch sessions with detailed information about each player's accounts and ranks.

## How to Use

### 1. Managing Your Session

After creating a session with `/create-session`, use `/manage-session` to open the management dashboard.

```
/manage-session session_id:<your_session_id>
```

### 2. Queue Management Interface

Click the **"Manage Queue"** button to view detailed information about players waiting to join:

- **Player Information**: Username, streaming status, preferred roles
- **Account Details**: All linked accounts with rank information for each role
- **Queue Position**: Shows join order and any notes from players

### 3. Accepting Players

1. **Select a Player**: Use the dropdown to choose a player from the queue
2. **Review Accounts**: See all their accounts with Tank/DPS/Support ranks
3. **Choose Account & Role**: Select which account and role to accept them as
4. **Accept**: Click "Accept Player" to move them to your session

### 4. Player Information Display

Each player shows:
- 📺 Streaming indicator (if they're streaming)
- 🎯 Preferred roles with emojis (🛡️ Tank, ⚔️ DPS, 💉 Support)
- 🎮 All accounts with detailed ranks:
  - Primary account indicator
  - Rank and division for each role (e.g., "Gold🟨 3")

### 5. Session Status

The management dashboard shows:
- ✅ **Accepted Players**: Who's been accepted and in what role
- ⏳ **Queue**: Who's still waiting
- 🎯 **Team Composition**: Requirements vs accepted players

## Example Workflow

1. Player joins your session queue with the "Join" button
2. You use `/manage-session` to review applicants
3. Click "Manage Queue" to see detailed player information
4. Select a player to review their accounts and ranks
5. Choose their account and role, then accept them
6. Player is moved from queue to your session team
7. Session embed updates to show team composition

## Database Changes

The system uses these database tables:
- `session_queue`: Players waiting to join (unchanged)
- `session_participants`: Accepted players (now utilized)
- `user_accounts`: Player account and rank data (unchanged)

## Benefits

- **Informed Decisions**: See exact ranks before accepting
- **Flexible Selection**: Choose specific accounts and roles for each player
- **Team Balance**: Visual indicators for role requirements
- **No Anonymous Players**: Full transparency of player capabilities
- **Multiple Accounts**: Players can show off their smurf/alt accounts

## Interface Components

### Queue Management View
- Paginated display (5 players per page)
- Player selection dropdown
- Navigation buttons (Previous/Next)
- Refresh button for real-time updates

### Player Acceptance View  
- Account selection dropdown
- Role selection (Tank/DPS/Support)
- Accept/Reject buttons
- Real-time selection preview

This system provides session creators complete control while giving players full transparency about their skills and capabilities.