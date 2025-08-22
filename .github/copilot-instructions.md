# Overwatch Discord Bot - GitHub Copilot Instructions

**ALWAYS FOLLOW THESE INSTRUCTIONS FIRST** and only fallback to additional search and context gathering if the information provided here is incomplete or found to be in error.

## Repository Overview

Overwatch Discord Bot is a comprehensive Python Discord bot for scheduling and managing Overwatch 2 game sessions. Features include user profiles with multiple Battle.net accounts, rank tracking, real-time session management via interactive Discord buttons, SQLite database persistence, and Docker/Railway deployment support.

- **Language**: Python 3.12
- **Framework**: discord.py 2.4.0  
- **Database**: SQLite with aiosqlite
- **Deployment**: Docker + Railway platform
- **Architecture**: Cog-based command system with persistent UI components

## Working Effectively

### Initial Setup and Dependencies

1. **Environment Setup**:
   ```bash
   python3 --version  # Ensure Python 3.12+ is available
   pip install -r requirements.txt  # Takes ~7 seconds
   ```

2. **Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env file and set BOT_TOKEN=your-discord-bot-token
   # DB_PATH defaults to data/overwatch.db if not specified
   ```

3. **Create Data Directory**:
   ```bash
   mkdir -p data
   # Database will be automatically created on first run
   ```

### Testing and Validation

**CRITICAL TIMING INFORMATION**:
- All tests complete in under 1 second each - NEVER CANCEL
- No long-running builds or processes in this repository
- Use timeout values of 30+ seconds for safety margin

4. **Run Core Functionality Tests**:
   ```bash
   python3 test_functionality.py  # Takes ~0.3 seconds - NEVER CANCEL
   ```
   Validates: Database operations, models, time utilities, embed generation

5. **Run UI and Display Tests**:
   ```bash
   python3 test_accepted_players_display.py  # Takes ~0.3 seconds - NEVER CANCEL
   python3 test_queue_management.py  # Takes ~0.1 seconds - NEVER CANCEL  
   ```
   Validates: Session display, queue management, player acceptance flows

6. **Syntax Validation**:
   ```bash
   python3 -m py_compile bot.py
   python3 -m py_compile cogs/*.py core/*.py
   ```

### Running the Bot

7. **Test Bot Startup** (without Discord connection):
   ```bash
   # This will fail with connection error due to invalid/missing token - this is expected
   timeout 10 python3 bot.py  # Should show startup logs then fail with DNS/connection error
   ```

8. **Normal Bot Operation** (with valid Discord token):
   ```bash
   python3 bot.py  # Runs indefinitely until Ctrl+C
   ```

### Docker Deployment

9. **Docker Build** (NOTE: May fail in restricted network environments):
   ```bash
   docker build -t overwatch-bot .  # May fail due to SSL certificate issues in sandboxed environments
   ```

10. **Docker Run with Persistence**:
    ```bash
    docker run -d --name overwatch-bot \
      -e BOT_TOKEN=your_token_here \
      -e DB_PATH=/app/data/overwatch.db \
      -v bot-data:/app/data \
      overwatch-bot
    ```

## Validation Scenarios

**MANUAL VALIDATION REQUIREMENT**: After making changes, ALWAYS run these validation scenarios:

### Core Database and Models Testing
```bash
python3 test_functionality.py
```
- Verify all database operations work correctly
- Confirm rank validation and display formatting
- Test timezone and datetime utilities
- Validate embed generation for sessions and profiles

### UI and Session Management Testing  
```bash
python3 test_accepted_players_display.py
python3 test_queue_management.py
```
- Test session creation and player queue management
- Verify embed updates when players are accepted
- Confirm role assignment and team composition logic
- Validate streaming status display and role emoji formatting

### Demo and Interface Testing
```bash
python3 demo_accepted_players.py    # Demonstrates session display before/after accepting players
python3 demo_queue_interface.py     # Shows complete queue management workflow
```
- Review visual output to ensure UI components render correctly
- Verify player acceptance flow works end-to-end
- Confirm role requirements and team composition logic

### Module Import Testing
```bash
python3 -c "import sys; sys.path.insert(0, '.'); from core import database, models, timeutil, embeds; print('✓ All core modules import successfully')"
```

## File Structure and Navigation

### Core Components
- **`bot.py`** - Main entry point, Discord bot initialization and event handling
- **`cogs/`** - Discord command modules:
  - `profile_cog.py` - User profile and account management commands  
  - `session_cog.py` - Session creation and management commands
  - `manage_cog.py` - Session creator management interface
- **`core/`** - Core functionality modules:
  - `database.py` - SQLite database operations and schema management
  - `models.py` - Data models, game modes, rank validation  
  - `ui.py` - Discord UI components (buttons, modals, persistent views)
  - `embeds.py` - Discord embed generation for sessions and profiles
  - `timeutil.py` - Timezone and datetime parsing utilities
  - `errors.py` - Custom exception definitions

### Configuration and Deployment
- **`.env.example`** - Environment variable template (copy to `.env`)
- **`requirements.txt`** - Python dependencies (discord.py, aiosqlite, python-dotenv)
- **`Dockerfile`** - Container build configuration
- **`railway.json`** - Railway platform deployment configuration

### Documentation Files
- **`readme.md`** - Main project documentation with setup instructions
- **`DATABASE_PERSISTENCE_GUIDE.md`** - Database deployment and backup strategies
- **`IMPLEMENTATION_SUMMARY.md`** - Technical implementation details
- **`QUEUE_MANAGEMENT.md`** - Queue system usage and workflows
- **`VISUAL_MODIFICATION_GUIDE.md`** - UI customization instructions

### Test and Demo Files
- **`test_functionality.py`** - Core functionality validation
- **`test_accepted_players_display.py`** - Session display testing  
- **`test_queue_management.py`** - Queue workflow testing
- **`demo_accepted_players.py`** - Visual demonstration of session states
- **`demo_queue_interface.py`** - Complete queue management demo

## Common Development Tasks

### Adding New Commands
1. Create command in appropriate cog file (`cogs/profile_cog.py`, `cogs/session_cog.py`, etc.)
2. Update `bot.py` if new cog is added to `initial_extensions` list
3. Test with `python3 test_functionality.py`
4. Test Discord integration manually

### Modifying Database Schema  
1. Update schema in `core/database.py`
2. Add migration logic to handle existing databases
3. Update models in `core/models.py` if needed
4. Test with `python3 test_functionality.py`
5. Verify data persistence with existing test database

### UI Component Changes
1. Modify UI classes in `core/ui.py`  
2. Update embed generation in `core/embeds.py` if needed
3. Test display with `python3 test_accepted_players_display.py`
4. Run demo scripts to verify visual changes

### Environment-Specific Issues
- **Docker build failures**: Expected in restricted network environments due to SSL certificate issues
- **Discord connection failures**: Expected without valid BOT_TOKEN - bot will show startup logs then fail with DNS/connection error
- **No linting tools configured**: Repository has no flake8, black, or pylint configuration - use manual syntax checking with `python3 -m py_compile`

## Repository Timing Reference

All operations in this repository are fast - there are NO long-running builds or processes:

- **Dependency installation**: ~7 seconds
- **Core functionality tests**: ~0.3 seconds  
- **UI/display tests**: ~0.3 seconds
- **Queue management tests**: ~0.1 seconds
- **Demo script execution**: ~0.3 seconds
- **Module import validation**: ~0.1 seconds
- **Python syntax compilation**: ~0.1 seconds

**NEVER CANCEL any command** - all operations complete quickly. Use 30+ second timeouts for safety margin but expect everything to finish in under 1 second.