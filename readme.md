# Overwatch Discord Bot

A comprehensive Discord bot for scheduling and managing Overwatch 2 game sessions. It features user profiles with multiple accounts, rank tracking, real-time session management via interactive buttons, SQLite persistence, and is designed for Docker/Railway deployment.

## ✨ Features

### 🎮 Game Session Management
- **Create Sessions**: Schedule Overwatch sessions with specific game modes (5v5, 6v6, Stadium)
- **Real-time Queue**: Interactive buttons for joining/leaving sessions
- **Rank Gating**: Optional rank restrictions to ensure balanced matches
- **Timezone Support**: Schedule in your local timezone, displayed for everyone
- **Auto-completion**: Sessions automatically close when start time arrives

### 👤 User Profiles
- **Multi-account Support**: Add multiple Battle.net accounts
- **Rank Tracking**: Track Tank, DPS, and Support ranks for each account
- **Preferred Roles**: Set your preferred roles for easy matchmaking
- **Timezone Configuration**: Set your timezone for accurate scheduling

### 🛠️ Session Management
- **Creator Controls**: Manage your sessions with dedicated dashboard
- **Queue Monitoring**: See who's in queue with their preferred roles
- **Session Status**: Open/close sessions or cancel them entirely
- **Streaming Support**: Toggle streaming status in queue

### 🔧 Technical Features
- **Slash Commands Only**: Modern Discord interface, no message content needed
- **Persistent UI**: Buttons work even after bot restarts
- **Async Architecture**: Handles multiple users efficiently
- **SQLite Database**: Reliable data persistence with WAL mode
- **Docker Ready**: Easy deployment to any platform

## 🚀 Quick Start

### Local Development

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd overwatch-discord-bot
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your Discord bot token
   ```

3. **Run the Bot**
   ```bash
   python bot.py
   ```

4. **Invite to Discord**
   - Create a Discord application at https://discord.com/developers/applications
   - Add bot permissions: `Send Messages`, `Embed Links`, `Use Slash Commands`
   - Generate invite link and add to your server

### Railway Deployment

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Deploy on Railway**
   - Go to [Railway](https://railway.app)
   - Create new project from GitHub repo
   - Add environment variable: `BOT_TOKEN=your-discord-bot-token`
   - Add volume mount: `/app/data` for database persistence
   - Deploy automatically uses the included `Dockerfile`

## 📋 Commands

### Profile Management
- `/setup-profile` - Create your profile with timezone and preferred roles
- `/add-account` - Add a Battle.net account with ranks
- `/edit-account` - Modify existing account details
- `/my-profile` - View your complete profile

### Session Management
- `/create-session` - Create a new game session
- `/view-sessions` - List all active sessions in the server
- `/cancel-session` - Cancel one of your sessions
- `/manage-session` - Open management dashboard for your session

## 🎯 Usage Examples

### Creating Your First Session

1. **Set up your profile**:
   ```
   /setup-profile timezone:America/New_York
   # Select your preferred roles using the dropdown
   ```

2. **Add your account**:
   ```
   /add-account account_name:YourBattleTag#1234 is_primary:True 
                tank_rank:gold tank_div:3 dps_rank:platinum dps_div:1
   ```

3. **Create a session**:
   ```
   /create-session game_mode:5v5 time:2024-12-25T19:30 
                   timezone:America/New_York description:"Competitive push to Masters!"
   ```

### Managing Sessions

- **Join a session**: Click the "Join" button on any session
- **Leave a session**: Click the "Leave" button
- **Toggle streaming**: Click "Toggle Streaming" to show you're streaming
- **Manage your session**: Use `/manage-session` for creator controls

## 🗄️ Database Schema

The bot uses SQLite with the following tables:

- **users**: Discord profiles with timezones and preferences
- **user_accounts**: Multiple Battle.net accounts per user with ranks
- **sessions**: Game session details and settings
- **session_queue**: Users waiting to join sessions
- **session_participants**: Final team selections (future feature)

## 🔧 Configuration

### Environment Variables
- `BOT_TOKEN`: Your Discord bot token (required)
- `DB_PATH`: Database file path (optional, defaults to `data/overwatch.db`)

### Game Modes
- **5v5**: 1 Tank, 2 DPS, 2 Support (standard competitive)
- **6v6**: 2 Tank, 2 DPS, 2 Support (classic format)
- **Stadium**: 6 DPS (experimental game mode)

### Rank System
Supported ranks: Bronze, Silver, Gold, Platinum, Diamond, Master, Grandmaster, Champion
Each rank has divisions 1-5 (1 being highest within the rank)

## 🛡️ Security

- **Environment Variables**: Sensitive data stored securely
- **Parameterized Queries**: SQL injection protection
- **Input Validation**: All user inputs validated
- **Permission Checks**: Users can only manage their own sessions

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding to commands**
   - Ensure bot has proper permissions in Discord
   - Check that slash commands are synced (`/` should show commands)

2. **Database errors**
   - Ensure `data/` directory exists and is writable
   - Check database file permissions

3. **Timezone issues**
   - Use IANA timezone names (e.g., `America/New_York`)
   - Check timezone autocomplete for valid options

### Support

For issues and feature requests, please create an issue in the repository.

## 🎯 Future Enhancements

- **Team Selection**: Let creators pick final teams from queue
- **Queue Limits**: Set maximum queue sizes per role
- **Session Editing**: Modify existing session details
- **Data Export**: Export session history to CSV
- **Advanced Matchmaking**: Automatic team balancing by rank

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Ready to level up your Overwatch group coordination? Deploy this bot today!** 🚀