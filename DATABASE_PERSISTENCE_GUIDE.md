# Database Persistence Guide for Overwatch Discord Bot

This guide explains how to make the bot's database persistent between updates and deployments, ensuring that user data, sessions, and configurations are preserved.

## Table of Contents
1. [Understanding Database Storage](#understanding-database-storage)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Backup and Recovery](#backup-and-recovery)
5. [Database Migration](#database-migration)
6. [Docker Deployment](#docker-deployment)
7. [Cloud Storage Options](#cloud-storage-options)

## Understanding Database Storage

The bot uses SQLite as its database, stored in a single file. The database location is configured via:

```python
# In core/database.py
DB_FILE = os.getenv("DB_PATH", "data/overwatch.db")
```

### Current Database Schema

The database contains these main tables:
- **`users`** - Discord user profiles with timezones and preferences
- **`user_accounts`** - Battle.net accounts with ranks (including new 6v6 ranks)
- **`sessions`** - Game sessions with scheduling and settings
- **`session_queue`** - Players waiting to join sessions
- **`session_participants`** - Accepted players in sessions

## Local Development Setup

### Method 1: Environment Variable

Create a `.env` file in your project root:

```bash
# .env file
DB_PATH=/path/to/persistent/overwatch.db
BOT_TOKEN=your_bot_token_here
```

### Method 2: Data Directory

Create a persistent data directory:

```bash
# Create data directory
mkdir -p data
chmod 755 data

# Database will be created at data/overwatch.db (default)
```

### Method 3: Custom Path

Set an absolute path for maximum control:

```bash
# Linux/Mac
export DB_PATH="/home/username/bot-data/overwatch.db"

# Windows
set DB_PATH="C:\bot-data\overwatch.db"
```

## Production Deployment

### Railway (Current Platform)

Based on your `railway.json`, you're using Railway. Here's how to ensure persistence:

#### Option 1: Railway Volumes (Recommended)

```json
{
  "build": {
    "builder": "DOCKER"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  },
  "volumes": [
    {
      "name": "bot-data",
      "mountPath": "/app/data"
    }
  ]
}
```

Set environment variable in Railway dashboard:
```
DB_PATH=/app/data/overwatch.db
```

#### Option 2: Railway PostgreSQL (Enterprise)

For high-traffic bots, consider PostgreSQL:

1. Add PostgreSQL service in Railway
2. Install psycopg2: `pip install psycopg2-binary`
3. Update database connection code

### Heroku Deployment

```bash
# Set environment variable
heroku config:set DB_PATH=/app/data/overwatch.db

# Add buildpack for SQLite
heroku buildpacks:add --index 1 https://github.com/charlesroper/heroku-buildpack-sqlite3.git
```

Note: Heroku's filesystem is ephemeral. Use PostgreSQL addon:

```bash
heroku addons:create heroku-postgresql:hobby-dev
```

### VPS/Server Deployment

#### Create persistent directory:

```bash
# Create bot user and directory
sudo useradd -r -s /bin/false overwatch-bot
sudo mkdir -p /var/lib/overwatch-bot
sudo chown overwatch-bot:overwatch-bot /var/lib/overwatch-bot
sudo chmod 750 /var/lib/overwatch-bot
```

#### Systemd service file:

```ini
# /etc/systemd/system/overwatch-bot.service
[Unit]
Description=Overwatch Discord Bot
After=network.target

[Service]
Type=simple
User=overwatch-bot
WorkingDirectory=/opt/overwatch-bot
Environment=DB_PATH=/var/lib/overwatch-bot/overwatch.db
ExecStart=/opt/overwatch-bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Enable and start:

```bash
sudo systemctl enable overwatch-bot
sudo systemctl start overwatch-bot
```

## Backup and Recovery

### Automated Backup Script

Create `backup_db.py`:

```python
#!/usr/bin/env python3
import shutil
import os
from datetime import datetime
import sys

DB_PATH = os.getenv("DB_PATH", "data/overwatch.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")

def backup_database():
    """Create a timestamped backup of the database."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return False
    
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/overwatch_backup_{timestamp}.db"
    
    try:
        shutil.copy2(DB_PATH, backup_file)
        print(f"Backup created: {backup_file}")
        
        # Keep only last 10 backups
        cleanup_old_backups()
        return True
        
    except Exception as e:
        print(f"Backup failed: {e}")
        return False

def cleanup_old_backups():
    """Keep only the 10 most recent backups."""
    if not os.path.exists(BACKUP_DIR):
        return
    
    backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith("overwatch_backup_")]
    backup_files.sort(reverse=True)
    
    for old_backup in backup_files[10:]:  # Keep 10, remove rest
        os.remove(os.path.join(BACKUP_DIR, old_backup))
        print(f"Removed old backup: {old_backup}")

if __name__ == "__main__":
    backup_database()
```

### Automated Backup with Cron

```bash
# Run backup every 6 hours
0 */6 * * * /path/to/overwatch-bot/backup_db.py

# Or daily at 2 AM
0 2 * * * /path/to/overwatch-bot/backup_db.py
```

### Cloud Backup Script

Upload backups to cloud storage:

```python
# backup_to_cloud.py
import boto3  # for AWS S3
import os
from datetime import datetime

def backup_to_s3():
    """Upload database backup to AWS S3."""
    s3 = boto3.client('s3')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_key = f"overwatch-bot/backup_{timestamp}.db"
    
    try:
        s3.upload_file(
            os.getenv("DB_PATH", "data/overwatch.db"),
            "your-backup-bucket",
            backup_key
        )
        print(f"Uploaded to S3: {backup_key}")
    except Exception as e:
        print(f"S3 upload failed: {e}")
```

## Database Migration

The bot includes automatic migration support. Here's how to add new migrations:

### Adding New Migrations

In `core/database.py`, update the `_run_migrations()` method:

```python
async def _run_migrations(self):
    """Run database migrations for schema updates."""
    
    # Migration 1: Add 6v6 rank columns (already implemented)
    cursor = await self.conn.execute("PRAGMA table_info(user_accounts)")
    columns = await cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    if 'sixv6_rank' not in column_names:
        await self.conn.execute("ALTER TABLE user_accounts ADD COLUMN sixv6_rank TEXT")
        print("✓ Added sixv6_rank column")
        
    if 'sixv6_division' not in column_names:
        await self.conn.execute("ALTER TABLE user_accounts ADD COLUMN sixv6_division INTEGER")
        print("✓ Added sixv6_division column")
    
    # Migration 2: Add new table (example)
    try:
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS user_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER NOT NULL,
                games_played INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (discord_id) REFERENCES users(discord_id)
            )
        """)
        print("✓ Created user_statistics table")
    except Exception as e:
        print(f"Migration warning: {e}")
    
    # Migration 3: Add indexes for performance
    try:
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_game_mode ON sessions(game_mode)")
        await self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
        print("✓ Added performance indexes")
    except Exception as e:
        print(f"Index creation warning: {e}")
```

### Version Tracking

For complex migrations, add a version table:

```python
# Add to CREATE_STATEMENTS
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```python
async def get_schema_version(self):
    """Get current schema version."""
    try:
        result = await self.fetchrow("SELECT MAX(version) as version FROM schema_version")
        return result['version'] if result and result['version'] else 0
    except:
        return 0

async def set_schema_version(self, version):
    """Set schema version."""
    await self.execute("INSERT INTO schema_version (version) VALUES (?)", version)
```

## Docker Deployment

### Dockerfile with Persistent Storage

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV DB_PATH=/app/data/overwatch.db

# Run bot
CMD ["python", "bot.py"]
```

### Docker Compose with Volume

```yaml
version: '3.8'

services:
  overwatch-bot:
    build: .
    environment:
      - DB_PATH=/app/data/overwatch.db
      - BOT_TOKEN=${BOT_TOKEN}
    volumes:
      - bot-data:/app/data
    restart: unless-stopped

volumes:
  bot-data:
    driver: local
```

### Run with Docker

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f overwatch-bot

# Backup volume
docker run --rm -v bot-data:/data -v $(pwd):/backup alpine tar czf /backup/bot-data-backup.tar.gz -C /data .

# Restore volume
docker run --rm -v bot-data:/data -v $(pwd):/backup alpine tar xzf /backup/bot-data-backup.tar.gz -C /data
```

## Cloud Storage Options

### AWS RDS (PostgreSQL)

1. Create RDS instance
2. Install `asyncpg`: `pip install asyncpg`
3. Update database code:

```python
# For PostgreSQL support
import asyncpg

class PostgreSQLDatabase:
    async def connect(self):
        self.conn = await asyncpg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", 5432),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
```

### Google Cloud SQL

Similar setup with Cloud SQL proxy:

```bash
# Download Cloud SQL proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O cloud_sql_proxy
chmod +x cloud_sql_proxy

# Connect to instance
./cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432
```

### Railway Database Plugin

For Railway, use their PostgreSQL plugin:

1. Add PostgreSQL plugin in Railway dashboard
2. Copy connection variables
3. Update your bot configuration

## Best Practices

### 1. Regular Backups

```bash
# Daily backup cron job
0 2 * * * /opt/overwatch-bot/backup_db.py && /opt/overwatch-bot/backup_to_cloud.py
```

### 2. Monitoring Database Size

```python
def check_db_size():
    """Monitor database size."""
    db_path = os.getenv("DB_PATH", "data/overwatch.db")
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"Database size: {size_mb:.2f} MB")
        
        if size_mb > 100:  # Alert if over 100MB
            print("⚠️ Database size is large, consider cleanup")
```

### 3. Database Optimization

```python
async def optimize_database(self):
    """Optimize database performance."""
    # Cleanup old sessions
    await self.execute("""
        DELETE FROM sessions 
        WHERE status = 'COMPLETED' 
        AND created_at < datetime('now', '-30 days')
    """)
    
    # Vacuum database
    await self.execute("VACUUM")
    
    # Update statistics
    await self.execute("ANALYZE")
```

### 4. Health Checks

```python
async def health_check(self):
    """Check database health."""
    try:
        # Test connection
        await self.fetchrow("SELECT 1")
        
        # Check table integrity
        result = await self.fetchrow("PRAGMA integrity_check")
        if result[0] != "ok":
            print("⚠️ Database integrity issues detected")
            
        return True
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False
```

This guide ensures your bot's data persists through updates and deployments while providing robust backup and recovery options!