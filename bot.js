const { Client, GatewayIntentBits, SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder, InteractionResponseFlags } = require('discord.js');
const sqlite3 = require('sqlite3').verbose();

class OverwatchScheduleBot {
    constructor(token) {
        this.client = new Client({
            intents: [
                GatewayIntentBits.Guilds,
                GatewayIntentBits.GuildMessages,
                GatewayIntentBits.MessageContent
            ]
        });
        
        this.token = token;
        this.db = new sqlite3.Database('overwatch_schedule.db');
        this.initDatabase();
        this.setupCommands();
        this.setupEventHandlers();
        
        // Updated Overwatch ranks with divisions
        this.ranks = {
            'Bronze': { divisions: [5, 4, 3, 2, 1], color: '#CD7F32', wideGroupThreshold: 5 },
            'Silver': { divisions: [5, 4, 3, 2, 1], color: '#C0C0C0', wideGroupThreshold: 5 },
            'Gold': { divisions: [5, 4, 3, 2, 1], color: '#FFD700', wideGroupThreshold: 5 },
            'Platinum': { divisions: [5, 4, 3, 2, 1], color: '#00CED1', wideGroupThreshold: 5 },
            'Diamond': { divisions: [5, 4, 3, 2, 1], color: '#B57EDC', wideGroupThreshold: 5 },
            'Master': { divisions: [5, 4, 3, 2, 1], color: '#FF6B35', wideGroupThreshold: 3 },
            'Grandmaster': { divisions: [5, 4, 3, 2, 1], color: '#FF1744', wideGroupThreshold: 0 },
            'Champion': { divisions: [1], color: '#FFD700', wideGroupThreshold: 0 }
        };
        
        // Game modes and their role requirements
        this.gameModes = {
            '5v5': {
                roles: { 'Tank': 1, 'DPS': 2, 'Support': 2 },
                totalPlayers: 5
            },
            '6v6': {
                roles: { 'Any': 6 },
                totalPlayers: 6
            },
            'Stadium': {
                roles: { 'Any': 6 },
                totalPlayers: 6
            }
        };
        
        // Time slots for dropdown
        this.timeSlots = [
            '12:00 AM', '12:30 AM', '1:00 AM', '1:30 AM', '2:00 AM', '2:30 AM',
            '3:00 AM', '3:30 AM', '4:00 AM', '4:30 AM', '5:00 AM', '5:30 AM',
            '6:00 AM', '6:30 AM', '7:00 AM', '7:30 AM', '8:00 AM', '8:30 AM',
            '9:00 AM', '9:30 AM', '10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM',
            '12:00 PM', '12:30 PM', '1:00 PM', '1:30 PM', '2:00 PM', '2:30 PM',
            '3:00 PM', '3:30 PM', '4:00 PM', '4:30 PM', '5:00 PM', '5:30 PM',
            '6:00 PM', '6:30 PM', '7:00 PM', '7:30 PM', '8:00 PM', '8:30 PM',
            '9:00 PM', '9:30 PM', '10:00 PM', '10:30 PM', '11:00 PM', '11:30 PM'
        ];
        
        // Days of week
        this.daysOfWeek = [
            'Today', 'Tomorrow', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
        ];
    }
    
    initDatabase() {
        this.db.serialize(() => {
            // Users table - main Discord user
            this.db.run(`CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                preferred_roles TEXT DEFAULT '[]',
                timezone TEXT DEFAULT 'America/New_York',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`);
            
            // User accounts table - for multiple OW accounts per Discord user
            this.db.run(`CREATE TABLE IF NOT EXISTS user_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                account_name TEXT NOT NULL,
                tank_rank TEXT DEFAULT '',
                tank_division INTEGER DEFAULT 0,
                dps_rank TEXT DEFAULT '',
                dps_division INTEGER DEFAULT 0,
                support_rank TEXT DEFAULT '',
                support_division INTEGER DEFAULT 0,
                is_primary BOOLEAN DEFAULT FALSE,
                FOREIGN KEY(discord_id) REFERENCES users(discord_id)
            )`);
            
            // Sessions table - updated with timezone and message tracking
            this.db.run(`CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                game_mode TEXT NOT NULL,
                scheduled_time DATETIME NOT NULL,
                timezone TEXT NOT NULL,
                description TEXT,
                max_rank_diff INTEGER DEFAULT 5,
                status TEXT DEFAULT 'open',
                message_id TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`);
            
            // Session queue table - replaces participants (now it's a queue system)
            this.db.run(`CREATE TABLE IF NOT EXISTS session_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                account_id INTEGER,
                preferred_roles TEXT DEFAULT '[]',
                is_streaming BOOLEAN DEFAULT FALSE,
                queue_position INTEGER DEFAULT 0,
                status TEXT DEFAULT 'queued',
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id),
                FOREIGN KEY(account_id) REFERENCES user_accounts(id)
            )`);
            
            // Session participants table - actual selected team
            this.db.run(`CREATE TABLE IF NOT EXISTS session_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                account_id INTEGER,
                role TEXT NOT NULL,
                is_streaming BOOLEAN DEFAULT FALSE,
                selected_by TEXT NOT NULL,
                selected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(session_id) REFERENCES sessions(id),
                FOREIGN KEY(account_id) REFERENCES user_accounts(id),
                UNIQUE(session_id, user_id, role)
            )`);
            
            // User availability table
            this.db.run(`CREATE TABLE IF NOT EXISTS user_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                timezone TEXT NOT NULL,
                status TEXT DEFAULT 'playing',
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(discord_id) REFERENCES users(discord_id)
            )`);
            
            // Migration for existing databases
            this.db.run(`ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'America/New_York'`, () => {});
            this.db.run(`ALTER TABLE sessions ADD COLUMN timezone TEXT DEFAULT 'America/New_York'`, () => {});
            this.db.run(`ALTER TABLE sessions ADD COLUMN message_id TEXT DEFAULT ''`, () => {});
            this.db.run(`ALTER TABLE session_queue ADD COLUMN is_streaming BOOLEAN DEFAULT FALSE`, () => {});
            this.db.run(`ALTER TABLE session_participants ADD COLUMN is_streaming BOOLEAN DEFAULT FALSE`, () => {});
            this.db.run(`ALTER TABLE session_participants ADD COLUMN selected_by TEXT DEFAULT ''`, () => {});
            this.db.run(`ALTER TABLE session_participants ADD COLUMN selected_at DATETIME DEFAULT CURRENT_TIMESTAMP`, () => {});
        });
    }
    
    setupCommands() {
        const commands = [
            new SlashCommandBuilder()
                .setName('setup-profile')
                .setDescription('Set up your Discord profile and timezone')
                .addStringOption(option =>
                    option.setName('timezone')
                        .setDescription('Your timezone')
                        .setRequired(false)
                        .addChoices(
                            { name: 'Eastern Time (New York)', value: 'America/New_York' },
                            { name: 'Central Time (Chicago)', value: 'America/Chicago' },
                            { name: 'Mountain Time (Denver)', value: 'America/Denver' },
                            { name: 'Pacific Time (Los Angeles)', value: 'America/Los_Angeles' },
                            { name: 'Toronto', value: 'America/Toronto' },
                            { name: 'Vancouver', value: 'America/Vancouver' },
                            { name: 'London', value: 'Europe/London' },
                            { name: 'Paris', value: 'Europe/Paris' },
                            { name: 'Berlin', value: 'Europe/Berlin' },
                            { name: 'Tokyo', value: 'Asia/Tokyo' },
                            { name: 'Seoul', value: 'Asia/Seoul' },
                            { name: 'Sydney', value: 'Australia/Sydney' }
                        )),
                
            new SlashCommandBuilder()
                .setName('add-account')
                .setDescription('Add an Overwatch account with ranks')
                .addStringOption(option =>
                    option.setName('account-name')
                        .setDescription('Name for this account (e.g., "Main", "Alt", "Smurf")')
                        .setRequired(true))
                .addBooleanOption(option =>
                    option.setName('is-primary')
                        .setDescription('Is this your primary account?')
                        .setRequired(false)),
                
            new SlashCommandBuilder()
                .setName('edit-account')
                .setDescription('Edit one of your accounts')
                .addStringOption(option =>
                    option.setName('account-name')
                        .setDescription('Name of the account to edit')
                        .setRequired(true)),
                        
            new SlashCommandBuilder()
                .setName('create-session')
                .setDescription('Create a new gaming session')
                .addStringOption(option =>
                    option.setName('game-mode')
                        .setDescription('Game mode')
                        .setRequired(true)
                        .addChoices(
                            { name: '5v5 Competitive', value: '5v5' },
                            { name: '6v6 Classic', value: '6v6' },
                            { name: 'Stadium Mode', value: 'Stadium' }
                        ))
                .addStringOption(option =>
                    option.setName('description')
                        .setDescription('Optional description for the session')
                        .setRequired(false))
                .addIntegerOption(option =>
                    option.setName('max-rank-diff')
                        .setDescription('Maximum rank difference in divisions (default: 5)')
                        .setRequired(false)),
                        
            new SlashCommandBuilder()
                .setName('join-queue')
                .setDescription('Join the queue for a gaming session')
                .addIntegerOption(option =>
                    option.setName('session-id')
                        .setDescription('Session ID to join queue for')
                        .setRequired(true)),
                        
            new SlashCommandBuilder()
                .setName('manage-session')
                .setDescription('Manage your session (select players from queue)')
                .addIntegerOption(option =>
                    option.setName('session-id')
                        .setDescription('Session ID to manage')
                        .setRequired(true)),
                        
            new SlashCommandBuilder()
                .setName('view-sessions')
                .setDescription('View all active gaming sessions'),
                
            new SlashCommandBuilder()
                .setName('my-profile')
                .setDescription('View your profile and all accounts'),
                
            new SlashCommandBuilder()
                .setName('cancel-session')
                .setDescription('Cancel a session you created')
                .addIntegerOption(option =>
                    option.setName('session-id')
                        .setDescription('Session ID to cancel')
                        .setRequired(true)),
                        
            new SlashCommandBuilder()
                .setName('leave-queue')
                .setDescription('Leave the queue for a session')
                .addIntegerOption(option =>
                    option.setName('session-id')
                        .setDescription('Session ID to leave queue for')
                        .setRequired(true))
        ];
        
        this.commands = commands;
    }
    
    setupEventHandlers() {
        this.client.once('ready', () => {
            console.log(`Logged in as ${this.client.user.tag}!`);
            this.registerCommands();
        });
        
        this.client.on('interactionCreate', async (interaction) => {
            try {
                if (interaction.isChatInputCommand()) {
                    await this.handleCommand(interaction);
                } else if (interaction.isButton()) {
                    await this.handleButton(interaction);
                } else if (interaction.isStringSelectMenu()) {
                    await this.handleSelectMenu(interaction);
                }
            } catch (error) {
                console.error('Error handling interaction:', error);
                if (!interaction.replied && !interaction.deferred) {
                    await interaction.reply({ 
                        content: 'An error occurred!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
            }
        });
    }
    
    async registerCommands() {
        try {
            await this.client.application.commands.set(this.commands);
            console.log('Successfully registered application commands.');
        } catch (error) {
            console.error('Error registering commands:', error);
        }
    }
    
    async handleCommand(interaction) {
        switch (interaction.commandName) {
            case 'setup-profile':
                await this.handleSetupProfile(interaction);
                break;
            case 'add-account':
                await this.handleAddAccount(interaction);
                break;
            case 'edit-account':
                await this.handleEditAccount(interaction);
                break;
            case 'create-session':
                await this.handleCreateSession(interaction);
                break;
            case 'join-queue':
                await this.handleJoinQueue(interaction);
                break;
            case 'manage-session':
                await this.handleManageSession(interaction);
                break;
            case 'view-sessions':
                await this.handleViewSessions(interaction);
                break;
            case 'my-profile':
                await this.handleMyProfile(interaction);
                break;
            case 'cancel-session':
                await this.handleCancelSession(interaction);
                break;
            case 'leave-queue':
                await this.handleLeaveQueue(interaction);
                break;
        }
    }
    
    async handleSetupProfile(interaction) {
        const timezone = interaction.options.getString('timezone') || 'America/New_York';
        
        // Create or update user profile
        this.db.run(
            `INSERT OR REPLACE INTO users (discord_id, username, timezone) VALUES (?, ?, ?)`,
            [interaction.user.id, interaction.user.username, timezone],
            function(err) {
                if (err) {
                    console.error(err);
                    return interaction.reply({ 
                        content: 'Error setting up profile!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
            }
        );
        
        // Create role selection menu
        const roleMenu = new StringSelectMenuBuilder()
            .setCustomId('select-preferred-roles')
            .setPlaceholder('Select your preferred roles')
            .setMinValues(1)
            .setMaxValues(3)
            .addOptions([
                { label: 'Tank', value: 'Tank', emoji: '🛡️' },
                { label: 'DPS', value: 'DPS', emoji: '⚔️' },
                { label: 'Support', value: 'Support', emoji: '💚' }
            ]);
        
        const row = new ActionRowBuilder().addComponents(roleMenu);
        
        const embed = new EmbedBuilder()
            .setTitle('Profile Setup')
            .setDescription(`Welcome! Profile created for ${interaction.user.username}.\n\n**Timezone:** ${timezone}\n\nNext steps:\n1. Select your preferred roles below\n2. Use \`/add-account\` to add your Overwatch accounts with ranks\n3. Start creating and joining sessions!`)
            .setColor('#FF6B35');
        
        await interaction.reply({ 
            embeds: [embed], 
            components: [row], 
            flags: InteractionResponseFlags.Ephemeral 
        });
    }
    
    async handleAddAccount(interaction) {
        const accountName = interaction.options.getString('account-name');
        const isPrimary = interaction.options.getBoolean('is-primary') || false;
        
        // If this is set as primary, unset other primary accounts
        if (isPrimary) {
            this.db.run(
                'UPDATE user_accounts SET is_primary = FALSE WHERE discord_id = ?',
                [interaction.user.id]
            );
        }
        
        // Insert the account first
        this.db.run(
            `INSERT INTO user_accounts (discord_id, account_name, is_primary) VALUES (?, ?, ?)`,
            [interaction.user.id, accountName, isPrimary],
            async function(err) {
                if (err) {
                    console.error(err);
                    return interaction.reply({ 
                        content: 'Error adding account!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                const accountId = this.lastID;
                
                // Now show rank selection interface
                const embed = new EmbedBuilder()
                    .setTitle('Account Added!')
                    .setDescription(`**${accountName}** ${isPrimary ? '(Primary)' : ''}\n\nNow let's set up your ranks for each role. Click the buttons below to set your competitive ranks.`)
                    .setColor('#00FF00');
                
                const row = new ActionRowBuilder()
                    .addComponents(
                        new ButtonBuilder()
                            .setCustomId(`set-rank-${accountId}-Tank`)
                            .setLabel('Set Tank Rank')
                            .setStyle(ButtonStyle.Secondary)
                            .setEmoji('🛡️'),
                        new ButtonBuilder()
                            .setCustomId(`set-rank-${accountId}-DPS`)
                            .setLabel('Set DPS Rank')
                            .setStyle(ButtonStyle.Secondary)
                            .setEmoji('⚔️'),
                        new ButtonBuilder()
                            .setCustomId(`set-rank-${accountId}-Support`)
                            .setLabel('Set Support Rank')
                            .setStyle(ButtonStyle.Secondary)
                            .setEmoji('💚')
                    );
                
                await interaction.reply({ 
                    embeds: [embed], 
                    components: [row], 
                    flags: InteractionResponseFlags.Ephemeral 
                });
            }
        );
    }
    
    async handleEditAccount(interaction) {
        const accountName = interaction.options.getString('account-name');
        
        // Find the account
        this.db.get(
            'SELECT * FROM user_accounts WHERE discord_id = ? AND account_name = ?',
            [interaction.user.id, accountName],
            async (err, account) => {
                if (err || !account) {
                    return interaction.reply({ 
                        content: 'Account not found!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                const embed = new EmbedBuilder()
                    .setTitle(`Edit Account: ${accountName}`)
                    .setDescription(`Current ranks:\n🛡️ Tank: ${this.formatRank(account.tank_rank, account.tank_division)}\n⚔️ DPS: ${this.formatRank(account.dps_rank, account.dps_division)}\n💚 Support: ${this.formatRank(account.support_rank, account.support_division)}\n\nClick buttons to update ranks:`)
                    .setColor('#FF6B35');
                
                const row1 = new ActionRowBuilder()
                    .addComponents(
                        new ButtonBuilder()
                            .setCustomId(`set-rank-${account.id}-Tank`)
                            .setLabel('Edit Tank')
                            .setStyle(ButtonStyle.Secondary)
                            .setEmoji('🛡️'),
                        new ButtonBuilder()
                            .setCustomId(`set-rank-${account.id}-DPS`)
                            .setLabel('Edit DPS')
                            .setStyle(ButtonStyle.Secondary)
                            .setEmoji('⚔️'),
                        new ButtonBuilder()
                            .setCustomId(`set-rank-${account.id}-Support`)
                            .setLabel('Edit Support')
                            .setStyle(ButtonStyle.Secondary)
                            .setEmoji('💚')
                    );
                
                const row2 = new ActionRowBuilder()
                    .addComponents(
                        new ButtonBuilder()
                            .setCustomId(`delete-account-${account.id}`)
                            .setLabel('Delete Account')
                            .setStyle(ButtonStyle.Danger)
                            .setEmoji('🗑️')
                    );
                
                await interaction.reply({ 
                    embeds: [embed], 
                    components: [row1, row2], 
                    flags: InteractionResponseFlags.Ephemeral 
                });
            }
        );
    }
    
    async handleCreateSession(interaction) {
        await interaction.deferReply();
        
        const gameMode = interaction.options.getString('game-mode');
        const description = interaction.options.getString('description') || '';
        const maxRankDiff = interaction.options.getInteger('max-rank-diff') || 5;
        
        // Get user timezone
        this.db.get(
            'SELECT timezone FROM users WHERE discord_id = ?',
            [interaction.user.id],
            async (err, user) => {
                const userTimezone = user?.timezone || 'America/New_York';
                
                // Show time/day selection interface
                const embed = new EmbedBuilder()
                    .setTitle(`🎮 Creating ${gameMode} Session`)
                    .setDescription(`**Description:** ${description || 'None'}\n**Max Rank Difference:** ${maxRankDiff} divisions\n**Your Timezone:** ${userTimezone}\n\nSelect when you want to play:`)
                    .setColor('#0099FF');
                
                // Day selection dropdown
                const dayMenu = new StringSelectMenuBuilder()
                    .setCustomId(`select-day-${gameMode}-${maxRankDiff}`)
                    .setPlaceholder('Select day')
                    .addOptions(this.daysOfWeek.map(day => ({
                        label: day,
                        value: day
                    })));
                
                const row = new ActionRowBuilder().addComponents(dayMenu);
                
                // Store session creation data temporarily
                this.tempSessionData = this.tempSessionData || {};
                this.tempSessionData[interaction.user.id] = {
                    gameMode,
                    description,
                    maxRankDiff,
                    userTimezone,
                    guildId: interaction.guild.id,
                    channelId: interaction.channel.id
                };
                
                await interaction.editReply({ 
                    embeds: [embed], 
                    components: [row]
                });
            }
        );
    }
    
    async handleJoinQueue(interaction) {
        const sessionId = interaction.options.getInteger('session-id');
        await this.joinQueue(interaction, sessionId);
    }
    
    async joinQueue(interaction, sessionId) {
        await interaction.deferReply({ flags: InteractionResponseFlags.Ephemeral });
        
        // Check if user already in queue
        this.db.get(
            'SELECT * FROM session_queue WHERE session_id = ? AND user_id = ?',
            [sessionId, interaction.user.id],
            async (err, existing) => {
                if (existing) {
                    return interaction.editReply({ content: 'You are already in the queue for this session!' });
                }
                
                // Get user accounts
                this.db.all(
                    'SELECT * FROM user_accounts WHERE discord_id = ?',
                    [interaction.user.id],
                    async (err, accounts) => {
                        if (err || accounts.length === 0) {
                            return interaction.editReply({ content: 'Please add at least one account first with `/add-account`!' });
                        }
                        
                        // Show account selection if multiple accounts
                        if (accounts.length > 1) {
                            const accountMenu = new StringSelectMenuBuilder()
                                .setCustomId(`select-queue-account-${sessionId}`)
                                .setPlaceholder('Select which account to use')
                                .addOptions(accounts.map(account => ({
                                    label: `${account.account_name}${account.is_primary ? ' (Primary)' : ''}`,
                                    value: account.id.toString(),
                                    description: `Tank: ${this.formatRank(account.tank_rank, account.tank_division)} | DPS: ${this.formatRank(account.dps_rank, account.dps_division)} | Support: ${this.formatRank(account.support_rank, account.support_division)}`
                                })));
                            
                            const row = new ActionRowBuilder().addComponents(accountMenu);
                            
                            await interaction.editReply({
                                content: 'Select which account to use for this session:',
                                components: [row]
                            });
                        } else {
                            // Single account, show role preferences
                            await this.showRolePreferences(interaction, sessionId, accounts[0].id);
                        }
                    }
                );
            }
        );
    }
    
    async showRolePreferences(interaction, sessionId, accountId) {
        const roleMenu = new StringSelectMenuBuilder()
            .setCustomId(`select-queue-roles-${sessionId}-${accountId}`)
            .setPlaceholder('Select roles you can play (multiple allowed)')
            .setMinValues(1)
            .setMaxValues(3)
            .addOptions([
                { label: 'Tank', value: 'Tank', emoji: '🛡️' },
                { label: 'DPS', value: 'DPS', emoji: '⚔️' },
                { label: 'Support', value: 'Support', emoji: '💚' }
            ]);
        
        const row = new ActionRowBuilder().addComponents(roleMenu);
        
        if (interaction.deferred) {
            await interaction.editReply({
                content: 'Select which roles you can play for this session:',
                components: [row]
            });
        } else {
            await interaction.reply({
                content: 'Select which roles you can play for this session:',
                components: [row],
                flags: InteractionResponseFlags.Ephemeral
            });
        }
    }
    
    async handleManageSession(interaction) {
        const sessionId = interaction.options.getInteger('session-id');
        await this.manageSession(interaction, sessionId);
    }
    
    async manageSession(interaction, sessionId) {
        await interaction.deferReply({ flags: InteractionResponseFlags.Ephemeral });
        
        // Check if user is the session creator
        this.db.get(
            'SELECT * FROM sessions WHERE id = ? AND creator_id = ?',
            [sessionId, interaction.user.id],
            async (err, session) => {
                if (err || !session) {
                    return interaction.editReply({ content: 'Session not found or you are not the creator!' });
                }
                
                // Get queue and current team
                this.db.all(
                    `SELECT sq.*, u.username, ua.account_name, ua.tank_rank, ua.tank_division, ua.dps_rank, ua.dps_division, ua.support_rank, ua.support_division 
                     FROM session_queue sq 
                     JOIN users u ON sq.user_id = u.discord_id 
                     LEFT JOIN user_accounts ua ON sq.account_id = ua.id
                     WHERE sq.session_id = ? ORDER BY sq.joined_at`,
                    [sessionId],
                    async (err, queue) => {
                        if (err) queue = [];
                        
                        this.db.all(
                            `SELECT sp.*, u.username, ua.account_name FROM session_participants sp 
                             JOIN users u ON sp.user_id = u.discord_id 
                             LEFT JOIN user_accounts ua ON sp.account_id = ua.id
                             WHERE sp.session_id = ?`,
                            [sessionId],
                            async (err, team) => {
                                if (err) team = [];
                                
                                const embed = await this.createManagementEmbed(session, queue, team);
                                
                                // Create selection dropdowns for each role
                                const mode = this.gameModes[session.game_mode];
                                const components = [];
                                
                                for (const [role, count] of Object.entries(mode.roles)) {
                                    const currentInRole = team.filter(p => p.role === role).length;
                                    
                                    if (currentInRole < count) {
                                        // Find eligible players for this role
                                        const eligible = queue.filter(q => {
                                            const roles = JSON.parse(q.preferred_roles || '[]');
                                            return roles.includes(role) || roles.includes('Any') || role === 'Any';
                                        });
                                        
                                        if (eligible.length > 0) {
                                            const selectMenu = new StringSelectMenuBuilder()
                                                .setCustomId(`select-player-${sessionId}-${role}`)
                                                .setPlaceholder(`Select ${role} player`)
                                                .addOptions(eligible.slice(0, 25).map(p => ({
                                                    label: `${p.username} (${p.account_name || 'No Account'})`,
                                                    value: `${p.user_id}-${p.account_id}`,
                                                    description: this.getPlayerRankDescription(p, role)
                                                })));
                                            
                                            components.push(new ActionRowBuilder().addComponents(selectMenu));
                                        }
                                    }
                                }
                                
                                await interaction.editReply({
                                    embeds: [embed],
                                    components: components.slice(0, 5) // Discord limit
                                });
                            }
                        );
                    }
                );
            }
        );
    }
    
    async handleViewSessions(interaction) {
        await interaction.deferReply();
        
        this.db.all(
            'SELECT * FROM sessions WHERE guild_id = ? AND status = "open" ORDER BY scheduled_time',
            [interaction.guild.id],
            async (err, sessions) => {
                if (err || sessions.length === 0) {
                    return interaction.editReply({ content: 'No active sessions found!' });
                }
                
                const embeds = [];
                
                for (const session of sessions.slice(0, 5)) {
                    const sessionEmbed = await this.createSessionEmbed(session.id);
                    embeds.push(sessionEmbed);
                }
                
                await interaction.editReply({ embeds: embeds });
            }
        );
    }
    
    async handleMyProfile(interaction) {
        this.db.get(
            'SELECT * FROM users WHERE discord_id = ?',
            [interaction.user.id],
            async (err, user) => {
                if (err || !user) {
                    return interaction.reply({ 
                        content: 'Profile not found! Use `/setup-profile` to create one.', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                // Get all accounts
                this.db.all(
                    'SELECT * FROM user_accounts WHERE discord_id = ? ORDER BY is_primary DESC, account_name',
                    [interaction.user.id],
                    (err, accounts) => {
                        if (err) accounts = [];
                        
                        const preferredRoles = JSON.parse(user.preferred_roles || '[]');
                        
                        const embed = new EmbedBuilder()
                            .setTitle(`${interaction.user.username}'s Overwatch Profile`)
                            .setColor('#FF6B35')
                            .setThumbnail(interaction.user.displayAvatarURL());
                        
                        embed.addFields([
                            { name: '🌍 Timezone', value: user.timezone, inline: true },
                            { name: '⭐ Preferred Roles', value: preferredRoles.join(', ') || 'None selected', inline: true }
                        ]);
                        
                        if (accounts.length === 0) {
                            embed.addFields([{ name: '🎮 Accounts', value: 'No accounts added yet! Use `/add-account` to add your Overwatch accounts.', inline: false }]);
                        } else {
                            accounts.forEach(account => {
                                const accountTitle = `${account.account_name}${account.is_primary ? ' (Primary)' : ''}`;
                                const accountValue = `🛡️ Tank: ${this.formatRank(account.tank_rank, account.tank_division)}\n⚔️ DPS: ${this.formatRank(account.dps_rank, account.dps_division)}\n💚 Support: ${this.formatRank(account.support_rank, account.support_division)}`;
                                embed.addFields([{ name: accountTitle, value: accountValue, inline: true }]);
                            });
                        }
                        
                        // Add edit buttons
                        const row = new ActionRowBuilder()
                            .addComponents(
                                new ButtonBuilder()
                                    .setCustomId('edit-profile')
                                    .setLabel('Edit Profile')
                                    .setStyle(ButtonStyle.Primary)
                                    .setEmoji('✏️')
                            );
                        
                        interaction.reply({ 
                            embeds: [embed], 
                            components: [row], 
                            flags: InteractionResponseFlags.Ephemeral 
                        });
                    }
                );
            }
        );
    }
    
    async handleCancelSession(interaction) {
        const sessionId = interaction.options.getInteger('session-id');
        
        this.db.run(
            'UPDATE sessions SET status = "cancelled" WHERE id = ? AND creator_id = ?',
            [sessionId, interaction.user.id],
            function(err) {
                if (err) {
                    return interaction.reply({ 
                        content: 'Error cancelling session!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                if (this.changes === 0) {
                    return interaction.reply({ 
                        content: 'Session not found or you are not the creator!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                interaction.reply({ 
                    content: `Session #${sessionId} has been cancelled.`, 
                    flags: InteractionResponseFlags.Ephemeral 
                });
            }
        );
    }
    
    async handleLeaveQueue(interaction) {
        const sessionId = interaction.options.getInteger('session-id');
        
        this.db.run(
            'DELETE FROM session_queue WHERE session_id = ? AND user_id = ?',
            [sessionId, interaction.user.id],
            async function(err) {
                if (err) {
                    return interaction.reply({ 
                        content: 'Error leaving queue!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                if (this.changes === 0) {
                    return interaction.reply({ 
                        content: 'You were not in the queue for this session!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                // Update session message
                await interaction.client.bot.updateSessionMessage(sessionId);
                
                interaction.reply({ 
                    content: `Left the queue for session #${sessionId}.`, 
                    flags: InteractionResponseFlags.Ephemeral 
                });
            }
        );
    }
    
    async handleButton(interaction) {
        const customId = interaction.customId;
        
        if (customId.startsWith('join-queue-')) {
            const sessionId = parseInt(customId.split('-')[2]);
            await this.joinQueue(interaction, sessionId);
        } else if (customId.startsWith('leave-queue-')) {
            const sessionId = parseInt(customId.split('-')[2]);
            await this.handleLeaveQueueButton(interaction, sessionId);
        } else if (customId.startsWith('quick-join-')) {
            const parts = customId.split('-');
            const sessionId = parseInt(parts[2]);
            const role = parts[3];
            await this.handleQuickJoin(interaction, sessionId, role);
        } else if (customId.startsWith('toggle-stream-')) {
            const parts = customId.split('-');
            const sessionId = parseInt(parts[2]);
            const userId = parts[3];
            await this.handleToggleStream(interaction, sessionId, userId);
        } else if (customId.startsWith('refresh-session-')) {
            const sessionId = parseInt(customId.split('-')[2]);
            await this.handleRefreshSession(interaction, sessionId);
        } else if (customId.startsWith('manage-session-')) {
            const sessionId = parseInt(customId.split('-')[2]);
            await this.manageSession(interaction, sessionId);
        } else if (customId.startsWith('set-rank-')) {
            const parts = customId.split('-');
            const accountId = parseInt(parts[2]);
            const role = parts[3];
            await this.showRankSelection(interaction, accountId, role);
        } else if (customId === 'edit-profile') {
            await this.handleEditProfile(interaction);
        } else if (customId.startsWith('delete-account-')) {
            const accountId = parseInt(customId.split('-')[2]);
            await this.handleDeleteAccount(interaction, accountId);
        }
    }
    
    async handleQuickJoin(interaction, sessionId, role) {
        await interaction.deferReply({ flags: InteractionResponseFlags.Ephemeral });
        
        // Get user accounts with ranks for this role
        this.db.all(
            'SELECT * FROM user_accounts WHERE discord_id = ?',
            [interaction.user.id],
            async (err, accounts) => {
                if (err || accounts.length === 0) {
                    return interaction.editReply({ 
                        content: 'Please add an account first with `/add-account`!' 
                    });
                }
                
                // Filter accounts that have ranks for this role (or show all for Any)
                let eligibleAccounts = accounts;
                if (role !== 'Any') {
                    eligibleAccounts = accounts.filter(account => {
                        const rankField = `${role.toLowerCase()}_rank`;
                        return account[rankField] && account[rankField] !== '';
                    });
                }
                
                if (eligibleAccounts.length === 0) {
                    return interaction.editReply({ 
                        content: `No accounts found with ${role} ranks! Please set your ${role} rank first.` 
                    });
                }
                
                if (eligibleAccounts.length === 1) {
                    // Auto-join with single account
                    await this.joinWithAccount(interaction, sessionId, eligibleAccounts[0].id, [role]);
                } else {
                    // Show account selection with ranks
                    const embed = new EmbedBuilder()
                        .setTitle(`🎯 Quick Join as ${role}`)
                        .setDescription('Select which account to use:')
                        .setColor('#00FF00');
                    
                    let accountText = '';
                    eligibleAccounts.forEach((account, index) => {
                        const rankValue = role !== 'Any' ? 
                            this.formatRank(account[`${role.toLowerCase()}_rank`], account[`${role.toLowerCase()}_division`]) :
                            `Tank: ${this.formatRank(account.tank_rank, account.tank_division)} | DPS: ${this.formatRank(account.dps_rank, account.dps_division)} | Support: ${this.formatRank(account.support_rank, account.support_division)}`;
                        
                        accountText += `**${index + 1}. ${account.account_name}** ${account.is_primary ? '(Primary)' : ''}\n${rankValue}\n\n`;
                    });
                    
                    embed.setDescription(accountText);
                    
                    const accountMenu = new StringSelectMenuBuilder()
                        .setCustomId(`quick-join-account-${sessionId}-${role}`)
                        .setPlaceholder('Select account')
                        .addOptions(eligibleAccounts.map(account => ({
                            label: `${account.account_name}${account.is_primary ? ' (Primary)' : ''}`,
                            value: account.id.toString(),
                            description: role !== 'Any' ? 
                                this.formatRank(account[`${role.toLowerCase()}_rank`], account[`${role.toLowerCase()}_division`]) :
                                'Multi-role account'
                        })));
                    
                    const row = new ActionRowBuilder().addComponents(accountMenu);
                    
                    await interaction.editReply({
                        embeds: [embed],
                        components: [row]
                    });
                }
            }
        );
    }
    
    async joinWithAccount(interaction, sessionId, accountId, roles) {
        // Check if already in queue
        this.db.get(
            'SELECT * FROM session_queue WHERE session_id = ? AND user_id = ?',
            [sessionId, interaction.user.id],
            async (err, existing) => {
                if (existing) {
                    // Update existing queue entry with new roles
                    const existingRoles = JSON.parse(existing.preferred_roles || '[]');
                    const newRoles = [...new Set([...existingRoles, ...roles])]; // Merge and remove duplicates
                    
                    this.db.run(
                        'UPDATE session_queue SET preferred_roles = ?, account_id = ? WHERE session_id = ? AND user_id = ?',
                        [JSON.stringify(newRoles), accountId, sessionId, interaction.user.id],
                        async (err) => {
                            if (err) {
                                if (interaction.deferred) {
                                    return interaction.editReply({ content: 'Error updating queue entry!' });
                                } else {
                                    return interaction.reply({ 
                                        content: 'Error updating queue entry!', 
                                        flags: InteractionResponseFlags.Ephemeral 
                                    });
                                }
                            }
                            
                            await this.updateSessionMessage(sessionId);
                            
                            const message = `✅ Updated queue entry! Now queued for: **${newRoles.join(', ')}**`;
                            if (interaction.deferred) {
                                await interaction.editReply({ content: message });
                            } else {
                                await interaction.reply({ 
                                    content: message, 
                                    flags: InteractionResponseFlags.Ephemeral 
                                });
                            }
                        }
                    );
                } else {
                    // Add to queue
                    this.db.run(
                        'INSERT INTO session_queue (session_id, user_id, account_id, preferred_roles) VALUES (?, ?, ?, ?)',
                        [sessionId, interaction.user.id, accountId, JSON.stringify(roles)],
                        async (err) => {
                            if (err) {
                                if (interaction.deferred) {
                                    return interaction.editReply({ content: 'Error joining queue!' });
                                } else {
                                    return interaction.reply({ 
                                        content: 'Error joining queue!', 
                                        flags: InteractionResponseFlags.Ephemeral 
                                    });
                                }
                            }
                            
                            await this.updateSessionMessage(sessionId);
                            
                            const message = `✅ Successfully joined queue for: **${roles.join(', ')}**`;
                            if (interaction.deferred) {
                                await interaction.editReply({ content: message });
                            } else {
                                await interaction.reply({ 
                                    content: message, 
                                    flags: InteractionResponseFlags.Ephemeral 
                                });
                            }
                        }
                    );
                }
            }
        );
    }
    
    async handleToggleStream(interaction, sessionId, userId) {
        // Check if user is toggling their own stream or if they're in the session
        const isOwnToggle = userId === interaction.user.id;
        
        if (!isOwnToggle) {
            return interaction.reply({ 
                content: 'You can only toggle your own streaming status!', 
                flags: InteractionResponseFlags.Ephemeral 
            });
        }
        
        // Toggle in queue first
        this.db.get(
            'SELECT * FROM session_queue WHERE session_id = ? AND user_id = ?',
            [sessionId, userId],
            (err, queueEntry) => {
                if (queueEntry) {
                    const newStreamStatus = !queueEntry.is_streaming;
                    this.db.run(
                        'UPDATE session_queue SET is_streaming = ? WHERE session_id = ? AND user_id = ?',
                        [newStreamStatus, sessionId, userId],
                        async (err) => {
                            if (!err) {
                                await this.updateSessionMessage(sessionId);
                                await interaction.reply({ 
                                    content: `${newStreamStatus ? '📺 Now streaming!' : '📺 Stopped streaming'}`, 
                                    flags: InteractionResponseFlags.Ephemeral 
                                });
                            }
                        }
                    );
                } else {
                    // Check if they're in the selected team
                    this.db.get(
                        'SELECT * FROM session_participants WHERE session_id = ? AND user_id = ?',
                        [sessionId, userId],
                        (err, participant) => {
                            if (participant) {
                                const newStreamStatus = !participant.is_streaming;
                                this.db.run(
                                    'UPDATE session_participants SET is_streaming = ? WHERE session_id = ? AND user_id = ?',
                                    [newStreamStatus, sessionId, userId],
                                    async (err) => {
                                        if (!err) {
                                            await this.updateSessionMessage(sessionId);
                                            await interaction.reply({ 
                                                content: `${newStreamStatus ? '📺 Now streaming!' : '📺 Stopped streaming'}`, 
                                                flags: InteractionResponseFlags.Ephemeral 
                                            });
                                        }
                                    }
                                );
                            } else {
                                await interaction.reply({ 
                                    content: 'You are not part of this session!', 
                                    flags: InteractionResponseFlags.Ephemeral 
                                });
                            }
                        }
                    );
                }
            }
        );
    }
    
    async handleSelectMenu(interaction) {
        const customId = interaction.customId;
        
        if (customId === 'select-preferred-roles') {
            const selectedRoles = interaction.values;
            
            this.db.run(
                'UPDATE users SET preferred_roles = ? WHERE discord_id = ?',
                [JSON.stringify(selectedRoles), interaction.user.id],
                (err) => {
                    if (err) {
                        return interaction.reply({ 
                            content: 'Error updating preferred roles!', 
                            flags: InteractionResponseFlags.Ephemeral 
                        });
                    }
                    
                    interaction.reply({ 
                        content: `Preferred roles updated: ${selectedRoles.join(', ')}`, 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
            );
        } else if (customId.startsWith('select-day-')) {
            const parts = customId.split('-');
            const gameMode = parts[2];
            const maxRankDiff = parseInt(parts[3]);
            const selectedDay = interaction.values[0];
            
            // Show time selection
            const timeOptions = this.timeSlots.map(time => ({
                label: time,
                value: time
            }));
            
            // Split into multiple menus due to Discord's 25 option limit
            const morningTimes = timeOptions.slice(0, 12); // 12:00 AM - 11:30 AM
            const afternoonTimes = timeOptions.slice(12, 24); // 12:00 PM - 11:30 PM
            const eveningTimes = timeOptions.slice(24); // 12:00 PM - 11:30 PM (second half)
            
            const embed = new EmbedBuilder()
                .setTitle(`🕐 Select Time for ${selectedDay}`)
                .setDescription(`Game Mode: **${gameMode}**\nDay: **${selectedDay}**\n\nChoose your preferred time:`)
                .setColor('#0099FF');
            
            const morningMenu = new StringSelectMenuBuilder()
                .setCustomId(`select-time-${gameMode}-${maxRankDiff}-${selectedDay}-morning`)
                .setPlaceholder('Morning (12:00 AM - 11:30 AM)')
                .addOptions(morningTimes);
            
            const afternoonMenu = new StringSelectMenuBuilder()
                .setCustomId(`select-time-${gameMode}-${maxRankDiff}-${selectedDay}-afternoon`)
                .setPlaceholder('Afternoon (12:00 PM - 11:30 PM)')
                .addOptions(afternoonTimes);
            
            const row1 = new ActionRowBuilder().addComponents(morningMenu);
            const row2 = new ActionRowBuilder().addComponents(afternoonMenu);
            
            await interaction.reply({
                embeds: [embed],
                components: [row1, row2],
                flags: InteractionResponseFlags.Ephemeral
            });
        } else if (customId.startsWith('select-time-')) {
            const parts = customId.split('-');
            const gameMode = parts[2];
            const maxRankDiff = parseInt(parts[3]);
            const selectedDay = parts[4];
            const timeOfDay = parts[5];
            const selectedTime = interaction.values[0];
            
            // Create the session
            const sessionData = this.tempSessionData[interaction.user.id];
            if (!sessionData) {
                return interaction.reply({ 
                    content: 'Session creation expired. Please try again!', 
                    flags: InteractionResponseFlags.Ephemeral 
                });
            }
            
            // Parse the selected day and time
            const scheduledTime = this.parseScheduledTime(selectedDay, selectedTime, sessionData.userTimezone);
            
            const stmt = this.db.prepare(`
                INSERT INTO sessions (creator_id, guild_id, channel_id, game_mode, scheduled_time, timezone, description, max_rank_diff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            `);
            
            stmt.run([
                interaction.user.id,
                sessionData.guildId,
                sessionData.channelId,
                gameMode,
                scheduledTime.toISOString(),
                sessionData.userTimezone,
                sessionData.description,
                maxRankDiff
            ], async function(err) {
                if (err) {
                    console.error(err);
                    return interaction.reply({ 
                        content: 'Error creating session!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                const sessionId = this.lastID;
                
                // Clean up temp data
                delete interaction.client.bot.tempSessionData[interaction.user.id];
                
                // Get the original channel and send the session
                const channel = await interaction.client.channels.fetch(sessionData.channelId);
                const sessionEmbed = await interaction.client.bot.createSessionEmbed(sessionId);
                const components = await interaction.client.bot.createSessionButtons(sessionId);
                
                const message = await channel.send({ 
                    embeds: [sessionEmbed], 
                    components: components
                });
                
                // Store message ID for updates
                interaction.client.bot.db.run(
                    'UPDATE sessions SET message_id = ? WHERE id = ?',
                    [message.id, sessionId]
                );
                
                await interaction.reply({ 
                    content: `✅ Session #${sessionId} created for **${selectedDay}** at **${selectedTime}**!`, 
                    flags: InteractionResponseFlags.Ephemeral 
                });
            });
            
            stmt.finalize();
        } else if (customId.startsWith('select-rank-')) {
            const parts = customId.split('-');
            const accountId = parseInt(parts[2]);
            const role = parts[3];
            const selectedRank = interaction.values[0];
            
            // Now show division selection
            const divisions = this.ranks[selectedRank].divisions;
            const divisionMenu = new StringSelectMenuBuilder()
                .setCustomId(`select-division-${accountId}-${role}-${selectedRank}`)
                .setPlaceholder(`Select your ${selectedRank} division`)
                .addOptions(divisions.map(div => ({
                    label: `${selectedRank} ${div}`,
                    value: div.toString()
                })));
            
            const row = new ActionRowBuilder().addComponents(divisionMenu);
            
            await interaction.reply({
                content: `Now select your **${selectedRank}** division:`,
                components: [row],
                flags: InteractionResponseFlags.Ephemeral
            });
        } else if (customId.startsWith('select-division-')) {
            const parts = customId.split('-');
            const accountId = parseInt(parts[2]);
            const role = parts[3];
            const rank = parts[4];
            const division = parseInt(interaction.values[0]);
            
            // Update database
            const column = `${role.toLowerCase()}_rank`;
            const divisionColumn = `${role.toLowerCase()}_division`;
            
            this.db.run(
                `UPDATE user_accounts SET ${column} = ?, ${divisionColumn} = ? WHERE id = ?`,
                [rank, division, accountId],
                (err) => {
                    if (err) {
                        return interaction.reply({ 
                            content: 'Error updating rank!', 
                            flags: InteractionResponseFlags.Ephemeral 
                        });
                    }
                    
                    interaction.reply({
                        content: `✅ ${role} rank set to **${rank} ${division}**!`,
                        flags: InteractionResponseFlags.Ephemeral
                    });
                }
            );
        } else if (customId.startsWith('quick-join-account-')) {
            const parts = customId.split('-');
            const sessionId = parseInt(parts[3]);
            const role = parts[4];
            const accountId = parseInt(interaction.values[0]);
            
            await this.joinWithAccount(interaction, sessionId, accountId, [role]);
        } else if (customId.startsWith('select-queue-account-')) {
            const sessionId = parseInt(customId.split('-')[3]);
            const accountId = parseInt(interaction.values[0]);
            await this.showRolePreferences(interaction, sessionId, accountId);
        } else if (customId.startsWith('select-queue-roles-')) {
            const parts = customId.split('-');
            const sessionId = parseInt(parts[3]);
            const accountId = parseInt(parts[4]);
            const selectedRoles = interaction.values;
            
            await this.joinWithAccount(interaction, sessionId, accountId, selectedRoles);
        } else if (customId.startsWith('select-player-')) {
            const parts = customId.split('-');
            const sessionId = parseInt(parts[2]);
            const role = parts[3];
            const [userId, accountId] = interaction.values[0].split('-');
            
            // Add player to team
            this.db.run(
                'INSERT INTO session_participants (session_id, user_id, account_id, role, selected_by) VALUES (?, ?, ?, ?, ?)',
                [sessionId, userId, parseInt(accountId), role, interaction.user.id],
                async (err) => {
                    if (err) {
                        return interaction.reply({ 
                            content: 'Error selecting player!', 
                            flags: InteractionResponseFlags.Ephemeral 
                        });
                    }
                    
                    // Remove from queue
                    this.db.run(
                        'DELETE FROM session_queue WHERE session_id = ? AND user_id = ?',
                        [sessionId, userId]
                    );
                    
                    // Update session message
                    await this.updateSessionMessage(sessionId);
                    
                    await interaction.reply({
                        content: `✅ Player selected for ${role} role!`,
                        flags: InteractionResponseFlags.Ephemeral
                    });
                }
            );
        }
    }
    
    // Enhanced session embed with streaming indicators and quick join buttons
    async createSessionEmbed(sessionId) {
        return new Promise((resolve, reject) => {
            this.db.get(
                'SELECT * FROM sessions WHERE id = ?',
                [sessionId],
                async (err, session) => {
                    if (err || !session) {
                        return reject(new Error('Session not found'));
                    }
                    
                    // Get queue count and team
                    this.db.get(
                        'SELECT COUNT(*) as count FROM session_queue WHERE session_id = ?',
                        [sessionId],
                        async (err, queueResult) => {
                            const queueCount = queueResult?.count || 0;
                            
                            this.db.all(
                                `SELECT sp.*, u.username, ua.account_name FROM session_participants sp 
                                 JOIN users u ON sp.user_id = u.discord_id 
                                 LEFT JOIN user_accounts ua ON sp.account_id = ua.id
                                 WHERE sp.session_id = ?`,
                                [sessionId],
                                async (err, team) => {
                                    if (err) team = [];
                                    
                                    // Get queue members with streaming status
                                    this.db.all(
                                        `SELECT sq.*, u.username, ua.account_name FROM session_queue sq 
                                         JOIN users u ON sq.user_id = u.discord_id 
                                         LEFT JOIN user_accounts ua ON sq.account_id = ua.id
                                         WHERE sq.session_id = ?`,
                                        [sessionId],
                                        async (err, queue) => {
                                            if (err) queue = [];
                                            
                                            const mode = this.gameModes[session.game_mode];
                                            
                                            const embed = new EmbedBuilder()
                                                .setTitle(`🎮 ${session.game_mode} Session #${session.id}`)
                                                .setDescription(`**⏰ Time:** ${this.formatTimeForTimezone(new Date(session.scheduled_time), session.timezone, 'America/New_York')}\n**📝 Description:** ${session.description || 'None'}\n**📊 Max Rank Difference:** ${session.max_rank_diff} divisions`)
                                                .setColor(queueCount > 0 ? '#00FF00' : '#0099FF');
                                            
                                            // Build role fields with streaming indicators
                                            for (const [role, count] of Object.entries(mode.roles)) {
                                                const roleTeam = team.filter(p => p.role === role);
                                                const filledSlots = roleTeam.length;
                                                
                                                let fieldValue = '';
                                                
                                                // Show filled slots
                                                for (let i = 0; i < filledSlots; i++) {
                                                    const player = roleTeam[i];
                                                    const displayName = player.account_name 
                                                        ? `${player.username} (${player.account_name})`
                                                        : player.username;
                                                    const streamIndicator = player.is_streaming ? ' 📺' : '';
                                                    fieldValue += `✅ ${displayName}${streamIndicator}\n`;
                                                }
                                                
                                                // Show empty slots
                                                for (let i = filledSlots; i < count; i++) {
                                                    fieldValue += `⭕ *Open Slot*\n`;
                                                }
                                                
                                                embed.addFields([{
                                                    name: `${this.getRoleEmoji(role)} ${role} (${filledSlots}/${count})`,
                                                    value: fieldValue || 'No slots available',
                                                    inline: true
                                                }]);
                                            }
                                            
                                            // Enhanced status with queue info and streaming count
                                            const totalFilled = team.length;
                                            const totalSlots = mode.totalPlayers;
                                            const streamingCount = team.filter(p => p.is_streaming).length + queue.filter(q => q.is_streaming).length;
                                            
                                            let statusValue = '';
                                            if (totalFilled === totalSlots) {
                                                statusValue = '🟢 **FULL TEAM SELECTED**';
                                            } else {
                                                statusValue = `🟡 **${totalFilled}/${totalSlots}** selected from team`;
                                            }
                                            
                                            if (queueCount > 0) {
                                                statusValue += `\n🎯 **${queueCount}** player${queueCount !== 1 ? 's' : ''} in queue`;
                                            } else {
                                                statusValue += '\n📭 No one in queue yet';
                                            }
                                            
                                            if (streamingCount > 0) {
                                                statusValue += `\n📺 **${streamingCount}** streaming`;
                                            }
                                            
                                            embed.addFields([{
                                                name: '📊 Status',
                                                value: statusValue,
                                                inline: false
                                            }]);
                                            
                                            // Add footer with helpful tips
                                            embed.setFooter({ 
                                                text: 'Use buttons below to join, manage, or toggle streaming!'
                                            });
                                            
                                            resolve(embed);
                                        }
                                    );
                                }
                            );
                        }
                    );
                }
            );
        });
    }
    
    // Create comprehensive button system for sessions
    async createSessionButtons(sessionId) {
        // Get session info to determine which buttons to show
        return new Promise((resolve) => {
            this.db.get(
                'SELECT * FROM sessions WHERE id = ?',
                [sessionId],
                (err, session) => {
                    if (err || !session) {
                        return resolve([]);
                    }
                    
                    const mode = this.gameModes[session.game_mode];
                    
                    // Row 1: Quick join buttons for each role
                    const quickJoinButtons = [];
                    for (const role of Object.keys(mode.roles)) {
                        quickJoinButtons.push(
                            new ButtonBuilder()
                                .setCustomId(`quick-join-${sessionId}-${role}`)
                                .setLabel(`Join as ${role}`)
                                .setStyle(ButtonStyle.Primary)
                                .setEmoji(this.getRoleEmoji(role))
                        );
                    }
                    
                    const row1 = new ActionRowBuilder().addComponents(quickJoinButtons.slice(0, 5));
                    
                    // Row 2: General actions
                    const row2 = new ActionRowBuilder()
                        .addComponents(
                            new ButtonBuilder()
                                .setCustomId(`join-queue-${sessionId}`)
                                .setLabel('Join Queue')
                                .setStyle(ButtonStyle.Secondary)
                                .setEmoji('🎯'),
                            new ButtonBuilder()
                                .setCustomId(`leave-queue-${sessionId}`)
                                .setLabel('Leave Queue')
                                .setStyle(ButtonStyle.Secondary)
                                .setEmoji('❌'),
                            new ButtonBuilder()
                                .setCustomId(`refresh-session-${sessionId}`)
                                .setLabel('Refresh')
                                .setStyle(ButtonStyle.Secondary)
                                .setEmoji('🔄'),
                            new ButtonBuilder()
                                .setCustomId(`manage-session-${sessionId}`)
                                .setLabel('Manage Team')
                                .setStyle(ButtonStyle.Success)
                                .setEmoji('⚙️')
                        );
                    
                    // Row 3: Streaming toggle (users will see their own)
                    const row3 = new ActionRowBuilder()
                        .addComponents(
                            new ButtonBuilder()
                                .setCustomId(`toggle-stream-${sessionId}-{USER_ID}`)
                                .setLabel('Toggle Streaming')
                                .setStyle(ButtonStyle.Secondary)
                                .setEmoji('📺')
                        );
                    
                    resolve([row1, row2, row3]);
                }
            );
        });
    }
    
    // Update session message in real-time
    async updateSessionMessage(sessionId) {
        this.db.get(
            'SELECT * FROM sessions WHERE id = ?',
            [sessionId],
            async (err, session) => {
                if (err || !session || !session.message_id) return;
                
                try {
                    const channel = await this.client.channels.fetch(session.channel_id);
                    const message = await channel.messages.fetch(session.message_id);
                    
                    const updatedEmbed = await this.createSessionEmbed(sessionId);
                    const updatedButtons = await this.createSessionButtons(sessionId);
                    
                    await message.edit({
                        embeds: [updatedEmbed],
                        components: updatedButtons
                    });
                } catch (error) {
                    console.error('Failed to update session message:', error);
                }
            }
        );
    }
    
    // Helper methods
    async handleLeaveQueueButton(interaction, sessionId) {
        this.db.run(
            'DELETE FROM session_queue WHERE session_id = ? AND user_id = ?',
            [sessionId, interaction.user.id],
            async (err) => {
                if (err) {
                    return interaction.reply({ 
                        content: 'Error leaving queue!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                await this.updateSessionMessage(sessionId);
                
                await interaction.reply({ 
                    content: `✅ Left the queue for session #${sessionId}!`, 
                    flags: InteractionResponseFlags.Ephemeral 
                });
            }
        );
    }
    
    async handleRefreshSession(interaction, sessionId) {
        const embed = await this.createSessionEmbed(sessionId);
        const buttons = await this.createSessionButtons(sessionId);
        
        await interaction.reply({
            content: '🔄 **Refreshed Session Status:**',
            embeds: [embed],
            components: buttons,
            flags: InteractionResponseFlags.Ephemeral
        });
    }
    
    async handleEditProfile(interaction) {
        this.db.all(
            'SELECT * FROM user_accounts WHERE discord_id = ? ORDER BY account_name',
            [interaction.user.id],
            async (err, accounts) => {
                if (err) accounts = [];
                
                let message = '**Your Accounts:**\n';
                accounts.forEach((account, i) => {
                    message += `${i+1}. ${account.account_name} ${account.is_primary ? '(Primary)' : ''}\n`;
                });
                
                message += '\nUse `/edit-account account-name:YourAccountName` to edit ranks!';
                
                // Add delete buttons for duplicate accounts
                const components = [];
                if (accounts.length > 1) {
                    const deleteButtons = accounts.slice(0, 5).map(account => 
                        new ButtonBuilder()
                            .setCustomId(`delete-account-${account.id}`)
                            .setLabel(`Delete ${account.account_name}`)
                            .setStyle(ButtonStyle.Danger)
                            .setEmoji('🗑️')
                    );
                    
                    for (let i = 0; i < deleteButtons.length; i += 5) {
                        const row = new ActionRowBuilder()
                            .addComponents(deleteButtons.slice(i, i + 5));
                        components.push(row);
                    }
                }
                
                await interaction.reply({ 
                    content: message,
                    components: components.slice(0, 5),
                    flags: InteractionResponseFlags.Ephemeral 
                });
            }
        );
    }
    
    async handleDeleteAccount(interaction, accountId) {
        this.db.get(
            'SELECT * FROM user_accounts WHERE id = ? AND discord_id = ?',
            [accountId, interaction.user.id],
            (err, account) => {
                if (err || !account) {
                    return interaction.reply({ 
                        content: 'Account not found or not yours!', 
                        flags: InteractionResponseFlags.Ephemeral 
                    });
                }
                
                this.db.run(
                    'DELETE FROM user_accounts WHERE id = ?',
                    [accountId],
                    function(err) {
                        if (err) {
                            return interaction.reply({ 
                                content: 'Error deleting account!', 
                                flags: InteractionResponseFlags.Ephemeral 
                            });
                        }
                        
                        interaction.reply({ 
                            content: `✅ Deleted account "${account.account_name}"!`, 
                            flags: InteractionResponseFlags.Ephemeral 
                        });
                    }
                );
            }
        );
    }
    
    async showRankSelection(interaction, accountId, role) {
        const rankMenu = new StringSelectMenuBuilder()
            .setCustomId(`select-rank-${accountId}-${role}`)
            .setPlaceholder(`Select your ${role} rank`)
            .addOptions(Object.keys(this.ranks).map(rank => ({
                label: rank,
                value: rank
            })));
        
        const row = new ActionRowBuilder().addComponents(rankMenu);
        
        await interaction.reply({
            content: `Select your **${role}** rank:`,
            components: [row],
            flags: InteractionResponseFlags.Ephemeral
        });
    }
    
    parseScheduledTime(day, time, timezone) {
        const now = new Date();
        let targetDate = new Date(now);
        
        // Handle day selection
        switch (day) {
            case 'Today':
                // Keep current date
                break;
            case 'Tomorrow':
                targetDate.setDate(targetDate.getDate() + 1);
                break;
            default:
                // Handle specific day names
                const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                const targetDayIndex = dayNames.indexOf(day);
                const currentDayIndex = targetDate.getDay();
                
                let daysToAdd = targetDayIndex - currentDayIndex;
                if (daysToAdd <= 0) {
                    daysToAdd += 7; // Next week
                }
                
                targetDate.setDate(targetDate.getDate() + daysToAdd);
                break;
        }
        
        // Parse time
        const [timeStr, period] = time.split(' ');
        const [hoursStr, minutesStr] = timeStr.split(':');
        let hours = parseInt(hoursStr);
        const minutes = parseInt(minutesStr);
        
        if (period === 'PM' && hours !== 12) {
            hours += 12;
        } else if (period === 'AM' && hours === 12) {
            hours = 0;
        }
        
        targetDate.setHours(hours, minutes, 0, 0);
        
        return targetDate;
    }
    
    formatTimeForTimezone(date, fromTz, toTz) {
        const options = {
            timeZone: toTz || 'America/New_York',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            timeZoneName: 'short'
        };
        return date.toLocaleString('en-US', options);
    }
    
    formatRank(rank, division) {
        if (!rank || !division) return 'Unranked';
        return `${rank} ${division}`;
    }
    
    getRoleEmoji(role) {
        const emojis = {
            'Tank': '🛡️',
            'DPS': '⚔️',
            'Support': '💚',
            'Any': '🎮'
        };
        return emojis[role] || '❓';
    }
    
    getRankValue(rank, division) {
        if (!rank || !division) return 0;
        
        const rankOrder = ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Master', 'Grandmaster', 'Champion'];
        const rankIndex = rankOrder.indexOf(rank);
        if (rankIndex === -1) return 0;
        
        return (rankIndex * 10) + (6 - division);
    }
    
    getPlayerRankDescription(player, role) {
        let rank = '';
        switch (role) {
            case 'Tank':
                rank = this.formatRank(player.tank_rank, player.tank_division);
                break;
            case 'DPS':
                rank = this.formatRank(player.dps_rank, player.dps_division);
                break;
            case 'Support':
                rank = this.formatRank(player.support_rank, player.support_division);
                break;
            default:
                const tankRank = this.getRankValue(player.tank_rank, player.tank_division);
                const dpsRank = this.getRankValue(player.dps_rank, player.dps_division);
                const supportRank = this.getRankValue(player.support_rank, player.support_division);
                const highest = Math.max(tankRank, dpsRank, supportRank);
                
                if (highest === tankRank) rank = this.formatRank(player.tank_rank, player.tank_division);
                else if (highest === dpsRank) rank = this.formatRank(player.dps_rank, player.dps_division);
                else rank = this.formatRank(player.support_rank, player.support_division);
        }
        return rank || 'Unranked';
    }
    
    async createManagementEmbed(session, queue, team) {
        const mode = this.gameModes[session.game_mode];
        
        const embed = new EmbedBuilder()
            .setTitle(`⚙️ Manage Session #${session.id}`)
            .setDescription(`**Mode:** ${session.game_mode}\n**Time:** ${this.formatTimeForTimezone(new Date(session.scheduled_time), session.timezone, 'America/New_York')}\n**Description:** ${session.description || 'None'}`)
            .setColor('#FF6B35');
        
        // Current team
        let teamText = '';
        for (const [role, count] of Object.entries(mode.roles)) {
            const roleTeam = team.filter(p => p.role === role);
            teamText += `**${this.getRoleEmoji(role)} ${role} (${roleTeam.length}/${count})**\n`;
            
            for (const player of roleTeam) {
                const streamIndicator = player.is_streaming ? ' 📺' : '';
                teamText += `✅ ${player.username} (${player.account_name || 'No Account'})${streamIndicator}\n`;
            }
            
            for (let i = roleTeam.length; i < count; i++) {
                teamText += `⭕ Empty Slot\n`;
            }
            teamText += '\n';
        }
        
        embed.addFields([{ name: 'Current Team', value: teamText || 'No players selected', inline: false }]);
        
        // Queue
        if (queue.length > 0) {
            const queueText = queue.slice(0, 10).map(q => {
                const roles = JSON.parse(q.preferred_roles || '[]');
                const streamIndicator = q.is_streaming ? ' 📺' : '';
                return `• ${q.username} (${q.account_name || 'No Account'}) - ${roles.join(', ')}${streamIndicator}`;
            }).join('\n');
            
            embed.addFields([{ name: `Queue (${queue.length})`, value: queueText, inline: false }]);
        } else {
            embed.addFields([{ name: 'Queue', value: 'No players in queue', inline: false }]);
        }
        
        return embed;
    }
    
    start() {
        this.client.bot = this;
        this.client.login(this.token);
    }
}

// Usage - gets token from environment variable or fallback
const token = process.env.BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE';
const bot = new OverwatchScheduleBot(token);
bot.start();

module.exports = OverwatchScheduleBot;
