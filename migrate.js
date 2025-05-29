// Run this ONCE to migrate your existing database
// Save as migrate.js and run with: node migrate.js

const sqlite3 = require('sqlite3').verbose();
const db = new sqlite3.Database('overwatch_schedule.db');

console.log('Starting database migration...');

db.serialize(() => {
    // Add missing columns to users table
    db.run(`ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'America/New_York'`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding timezone column:', err);
        } else {
            console.log('✅ Added timezone column to users table');
        }
    });

    // Update user_accounts table structure
    db.run(`ALTER TABLE user_accounts ADD COLUMN tank_rank TEXT DEFAULT ''`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding tank_rank column:', err);
        } else {
            console.log('✅ Updated tank_rank column');
        }
    });

    db.run(`ALTER TABLE user_accounts ADD COLUMN tank_division INTEGER DEFAULT 0`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding tank_division column:', err);
        } else {
            console.log('✅ Added tank_division column');
        }
    });

    db.run(`ALTER TABLE user_accounts ADD COLUMN dps_rank TEXT DEFAULT ''`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding dps_rank column:', err);
        } else {
            console.log('✅ Updated dps_rank column');
        }
    });

    db.run(`ALTER TABLE user_accounts ADD COLUMN dps_division INTEGER DEFAULT 0`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding dps_division column:', err);
        } else {
            console.log('✅ Added dps_division column');
        }
    });

    db.run(`ALTER TABLE user_accounts ADD COLUMN support_rank TEXT DEFAULT ''`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding support_rank column:', err);
        } else {
            console.log('✅ Updated support_rank column');
        }
    });

    db.run(`ALTER TABLE user_accounts ADD COLUMN support_division INTEGER DEFAULT 0`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding support_division column:', err);
        } else {
            console.log('✅ Added support_division column');
        }
    });

    // Add timezone to sessions table
    db.run(`ALTER TABLE sessions ADD COLUMN timezone TEXT DEFAULT 'America/New_York'`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding timezone to sessions:', err);
        } else {
            console.log('✅ Added timezone to sessions table');
        }
    });

    // Create new tables
    db.run(`CREATE TABLE IF NOT EXISTS session_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        account_id INTEGER,
        preferred_roles TEXT DEFAULT '[]',
        queue_position INTEGER DEFAULT 0,
        status TEXT DEFAULT 'queued',
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(session_id) REFERENCES sessions(id),
        FOREIGN KEY(account_id) REFERENCES user_accounts(id)
    )`, (err) => {
        if (err) {
            console.error('Error creating session_queue table:', err);
        } else {
            console.log('✅ Created session_queue table');
        }
    });

    // Update session_participants table
    db.run(`ALTER TABLE session_participants ADD COLUMN selected_by TEXT DEFAULT ''`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding selected_by column:', err);
        } else {
            console.log('✅ Added selected_by column to session_participants');
        }
    });

    db.run(`ALTER TABLE session_participants ADD COLUMN selected_at DATETIME DEFAULT CURRENT_TIMESTAMP`, (err) => {
        if (err && !err.message.includes('duplicate column name')) {
            console.error('Error adding selected_at column:', err);
        } else {
            console.log('✅ Added selected_at column to session_participants');
        }
    });

    // Create user_availability table
    db.run(`CREATE TABLE IF NOT EXISTS user_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        timezone TEXT NOT NULL,
        status TEXT DEFAULT 'playing',
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(discord_id) REFERENCES users(discord_id)
    )`, (err) => {
        if (err) {
            console.error('Error creating user_availability table:', err);
        } else {
            console.log('✅ Created user_availability table');
        }
    });

    console.log('\n🎉 Database migration complete! You can now restart your bot.');
    console.log('Run: npm start');

    db.close();
});