const { Client, GatewayIntentBits, SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, SelectMenuBuilder, StringSelectMenuBuilder } = require('discord.js');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

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

        // Timezone list
        this.timezones = [
            'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
            'America/Toronto', 'America/Vancouver', 'Europe/London', 'Europe/Paris',
            'Europe/Berlin', 'Asia/Tokyo', 'Asia/Seoul', 'Australia/Sydney'
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

            // User accounts table - updated for rank/division system
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

            // Sessions table - updated with timezone
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`);

            // Session queue table - replaces participants (now it's a queue system)
            this.db.run(`CREATE TABLE IF NOT EXISTS session_queue (
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
            )`);

            // Session participants table - actual selected team
            this.db.run(`CREATE TABLE IF NOT EXISTS session_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                account_id INTEGER,
                role TEXT NOT NULL,
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
                    option.setName('time')
                        .setDescription('Session time (e.g., "7:00 PM", "19:00", "in 2 hours")')
                        .setRequired(true))
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
                .setName('set-playing')
                .setDescription('Set when you\'re playing to show others')
                .addStringOption(option =>
                    option.setName('start-time')
                        .setDescription('When you start playing (e.g., "now", "7:00 PM", "in 30 minutes")')
                        .setRequired(true))
                .addStringOption(option =>
                    option.setName('duration')
                        .setDescription('How long you\'ll play (e.g., "2 hours", "until 11 PM")')
                        .setRequired(true))
                .addStringOption(option =>
                    option.setName('description')
                        .setDescription('What you\'re playing (e.g., "Comp grind", "Quick Play", "Custom games")')
                        .setRequired(false)),

            new SlashCommandBuilder()
                .setName('whos-playing')
                .setDescription('See who\'s currently playing or will be playing soon'),

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
                .setName('stop-playing')
                .setDescription('Stop showing as currently playing'),

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
                if (!interaction.replied) {
                    await interaction.reply({ content: 'An error occurred!', ephemeral: true });
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
            case 'set-playing':
                await this.handleSetPlaying(interaction);
                break;
            case 'whos-playing':
                await this.handleWhosPlaying(interaction);
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
            case 'stop-playing':
                await this.handleStopPlaying(interaction);
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
                    return interaction.reply({ content: 'Error setting up profile!', ephemeral: true });
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

        await interaction.reply({ embeds: [embed], components: [row], ephemeral: true });
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
                    return interaction.reply({ content: 'Error adding account!', ephemeral: true });
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

                await interaction.reply({ embeds: [embed], components: [row], ephemeral: true });
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
                    return interaction.reply({ content: 'Account not found!', ephemeral: true });
                }

                const embed = new EmbedBuilder()
                    .setTitle(`Edit Account: ${accountName}`)
                    .setDescription(`Current ranks:\n🛡️ Tank: ${this.formatRank(account.tank_rank, account.tank_division)}\n⚔️ DPS: ${this.formatRank(account.dps_rank, account.dps_division)}\n💚 Support: ${this.formatRank(account.support_rank, account.support_division)}\n\nClick buttons to update ranks:`)
                    .setColor('#FF6B35');

                const row = new ActionRowBuilder()
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

                await interaction.reply({ embeds: [embed], components: [row], ephemeral: true });
            }
        );
    }

    async handleCreateSession(interaction) {
        await interaction.deferReply();

        const gameMode = interaction.options.getString('game-mode');
        const timeString = interaction.options.getString('time');
        const description = interaction.options.getString('description') || '';
        const maxRankDiff = interaction.options.getInteger('max-rank-diff') || 5;

        // Get user timezone
        this.db.get(
            'SELECT timezone FROM users WHERE discord_id = ?',
            [interaction.user.id],
            async (err, user) => {
                const userTimezone = user?.timezone || 'America/New_York';

                // Parse time
                const scheduledTime = this.parseTime(timeString, userTimezone);
                if (!scheduledTime) {
                    return interaction.editReply({ content: 'Invalid time format! Try "7:00 PM", "19:00", or "in 2 hours"' });
                }

                const stmt = this.db.prepare(`
                    INSERT INTO sessions (creator_id, guild_id, channel_id, game_mode, scheduled_time, timezone, description, max_rank_diff)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                `);

                stmt.run([
                    interaction.user.id,
                    interaction.guild.id,
                    interaction.channel.id,
                    gameMode,
                    scheduledTime.toISOString(),
                    userTimezone,
                    description,
                    maxRankDiff
                ], async function(err) {
                    if (err) {
                        console.error(err);
                        return interaction.editReply({ content: 'Error creating session!' });
                    }

                    const sessionId = this.lastID;
                    const sessionEmbed = await interaction.client.bot.createSessionEmbed(sessionId);

                    const joinButton = new ButtonBuilder()
                        .setCustomId(`join-queue-${sessionId}`)
                        .setLabel('Join Queue')
                        .setStyle(ButtonStyle.Primary)
                        .setEmoji('🎯');

                    const manageButton = new ButtonBuilder()
                        .setCustomId(`manage-session-${sessionId}`)
                        .setLabel('Manage Session')
                        .setStyle(ButtonStyle.Secondary)
                        .setEmoji('⚙️');

                    const row = new ActionRowBuilder().addComponents(joinButton, manageButton);

                    await interaction.editReply({
                        embeds: [sessionEmbed],
                        components: [row]
                    });
                });

                stmt.finalize();
            }
        );
    }

    async handleJoinQueue(interaction) {
        const sessionId = interaction.options.getInteger('session-id');
        await this.joinQueue(interaction, sessionId);
    }

    async joinQueue(interaction, sessionId) {
        await interaction.deferReply({ ephemeral: true });

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
                ephemeral: true
            });
        }
    }

    async handleManageSession(interaction) {
        const sessionId = interaction.options.getInteger('session-id');
        await this.manageSession(interaction, sessionId);
    }

    async manageSession(interaction, sessionId) {
        await interaction.deferReply({ ephemeral: true });

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
                // For 'Any' role, show highest rank
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
                teamText += `✅ ${player.username} (${player.account_name || 'No Account'})\n`;
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
                return `• ${q.username} (${q.account_name || 'No Account'}) - ${roles.join(', ')}`;
            }).join('\n');

            embed.addFields([{ name: `Queue (${queue.length})`, value: queueText, inline: false }]);
        } else {
            embed.addFields([{ name: 'Queue', value: 'No players in queue', inline: false }]);
        }

        // Wide group warning
        if (team.length >= 2) {
            const wideGroupWarning = this.checkWideGroup(team);
            if (wideGroupWarning) {
                embed.addFields([{ name: '⚠️ Wide Group Warning', value: wideGroupWarning, inline: false }]);
            }
        }

        return embed;
    }

    checkWideGroup(team) {
        if (team.length < 2) return null;

        // Get all ranks in the team
        const ranks = [];
        for (const player of team) {
            let rank, division;
            switch (player.role) {
                case 'Tank':
                    rank = player.tank_rank;
                    division = player.tank_division;
                    break;
                case 'DPS':
                    rank = player.dps_rank;
                    division = player.dps_division;
                    break;
                case 'Support':
                    rank = player.support_rank;
                    division = player.support_division;
                    break;
            }

            if (rank && division) {
                ranks.push({ rank, division, value: this.getRankValue(rank, division) });
            }
        }

        if (ranks.length < 2) return null;

        const sortedRanks = ranks.sort((a, b) => a.value - b.value);
        const lowest = sortedRanks[0];
        const highest = sortedRanks[sortedRanks.length - 1];

        const divisionDiff = Math.abs(highest.value - lowest.value);

        // Check wide group thresholds
        const lowestRankData = this.ranks[lowest.rank];
        const threshold = lowestRankData?.wideGroupThreshold || 5;

        if (divisionDiff > threshold) {
            return `Large rank difference detected (${divisionDiff} divisions). This may result in poor queue times and unbalanced matches.`;
        }

        return null;
    }

    getRankValue(rank, division) {
        if (!rank || !division) return 0;

        const rankOrder = ['Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Master', 'Grandmaster', 'Champion'];
        const rankIndex = rankOrder.indexOf(rank);
        if (rankIndex === -1) return 0;

        // Convert to a single number (higher = better)
        return (rankIndex * 10) + (6 - division); // Division 1 is highest
    }

    formatRank(rank, division) {
        if (!rank || !division) return 'Unranked';
        return `${rank} ${division}`;
    }

    formatTimeForTimezone(date, fromTz, toTz) {
        // Simple timezone conversion - in a real app you'd use a library like moment-timezone
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

    // ... (continuing with the rest of the methods in the next part due to length)

    async handleButton(interaction) {
        const customId = interaction.customId;

        if (customId.startsWith('join-queue-')) {
            const sessionId = parseInt(customId.split('-')[2]);
            await this.joinQueue(interaction, sessionId);
        } else if (customId.startsWith('manage-session-')) {
            const sessionId = parseInt(customId.split('-')[2]);
            await this.manageSession(interaction, sessionId);
        } else if (customId.startsWith('set-rank-')) {
            const parts = customId.split('-');
            const accountId = parseInt(parts[2]);
            const role = parts[3];
            await this.showRankSelection(interaction, accountId, role);
        }
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
            ephemeral: true
        });
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
                        return interaction.reply({ content: 'Error updating preferred roles!', ephemeral: true });
                    }

                    interaction.reply({
                        content: `Preferred roles updated: ${selectedRoles.join(', ')}`,
                        ephemeral: true
                    });
                }
            );
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
                ephemeral: true
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
                        return interaction.reply({ content: 'Error updating rank!', ephemeral: true });
                    }

                    interaction.reply({
                        content: `✅ ${role} rank set to **${rank} ${division}**!`,
                        ephemeral: true
                    });
                }
            );
        } else if (customId.startsWith('select-queue-account-')) {
            const sessionId = parseInt(customId.split('-')[3]);
            const accountId = parseInt(interaction.values[0]);
            await this.showRolePreferences(interaction, sessionId, accountId);
        } else if (customId.startsWith('select-queue-roles-')) {
            const parts = customId.split('-');
            const sessionId = parseInt(parts[3]);
            const accountId = parseInt(parts[4]);
            const selectedRoles = interaction.values;

            // Add to queue
            this.db.run(
                'INSERT INTO session_queue (session_id, user_id, account_id, preferred_roles) VALUES (?, ?, ?, ?)',
                [sessionId, interaction.user.id, accountId, JSON.stringify(selectedRoles)],
                async (err) => {
                    if (err) {
                        return interaction.reply({ content: 'Error joining queue!', ephemeral: true });
                    }

                    await interaction.reply({
                        content: `✅ Successfully joined the queue for session #${sessionId}!\n**Preferred roles:** ${selectedRoles.join(', ')}`,
                        ephemeral: true
                    });
                }
            );
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
                        return interaction.reply({ content: 'Error selecting player!', ephemeral: true });
                    }

                    // Remove from queue
                    this.db.run(
                        'DELETE FROM session_queue WHERE session_id = ? AND user_id = ?',
                        [sessionId, userId]
                    );

                    await interaction.reply({
                        content: `✅ Player selected for ${role} role!`,
                        ephemeral: true
                    });

                    // Check if session is full
                    await this.checkSessionFull(sessionId);
                }
            );
        }
    }

    // Add the remaining methods...
    async createSessionEmbed(sessionId) {
        return new Promise((resolve, reject) => {
            this.db.get(
                'SELECT * FROM sessions WHERE id = ?',
                [sessionId],
                async (err, session) => {
                    if (err || !session) {
                        return reject(new Error('Session not found'));
                    }

                    // Get queue count
                    this.db.get(
                        'SELECT COUNT(*) as count FROM session_queue WHERE session_id = ?',
                        [sessionId],
                        async (err, queueResult) => {
                            const queueCount = queueResult?.count || 0;

                            // Get team
                            this.db.all(
                                `SELECT sp.*, u.username, ua.account_name FROM session_participants sp 
                                 JOIN users u ON sp.user_id = u.discord_id 
                                 LEFT JOIN user_accounts ua ON sp.account_id = ua.id
                                 WHERE sp.session_id = ?`,
                                [sessionId],
                                async (err, team) => {
                                    if (err) team = [];

                                    const mode = this.gameModes[session.game_mode];

                                    const embed = new EmbedBuilder()
                                        .setTitle(`🎮 ${session.game_mode} Session #${session.id}`)
                                        .setDescription(`**Time:** ${this.formatTimeForTimezone(new Date(session.scheduled_time), session.timezone, 'America/New_York')}\n**Description:** ${session.description || 'None'}\n**Max Rank Difference:** ${session.max_rank_diff} divisions`)
                                        .setColor('#0099FF');

                                    // Build role fields
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
                                            fieldValue += `✅ ${displayName}\n`;
                                        }

                                        // Show empty slots
                                        for (let i = filledSlots; i < count; i++) {
                                            fieldValue += `⭕ Empty Slot\n`;
                                        }

                                        embed.addFields([{
                                            name: `${this.getRoleEmoji(role)} ${role} (${filledSlots}/${count})`,
                                            value: fieldValue || 'No slots available',
                                            inline: true
                                        }]);
                                    }

                                    // Add queue info
                                    const totalFilled = team.length;
                                    const totalSlots = mode.totalPlayers;
                                    const statusColor = totalFilled === totalSlots ? '🟢' : '🟡';

                                    embed.addFields([{
                                        name: 'Status',
                                        value: `${statusColor} ${totalFilled}/${totalSlots} selected\n🎯 ${queueCount} in queue`,
                                        inline: false
                                    }]);

                                    resolve(embed);
                                }
                            );
                        }
                    );
                }
            );
        });
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

    parseTime(timeString, timezone = 'America/New_York') {
        const now = new Date();

        // Handle "in X hours/minutes"
        const inMatch = timeString.match(/in (\d+) (hour|minute)s?/i);
        if (inMatch) {
            const amount = parseInt(inMatch[1]);
            const unit = inMatch[2].toLowerCase();
            const newTime = new Date(now);
            if (unit === 'hour') {
                newTime.setHours(newTime.getHours() + amount);
            } else {
                newTime.setMinutes(newTime.getMinutes() + amount);
            }
            return newTime;
        }

        // Handle "now"
        if (timeString.toLowerCase() === 'now') {
            return now;
        }

        // Handle time formats like "7:00 PM" or "19:00"
        const timeMatch = timeString.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
        if (timeMatch) {
            let hours = parseInt(timeMatch[1]);
            const minutes = parseInt(timeMatch[2]);
            const ampm = timeMatch[3]?.toLowerCase();

            if (ampm === 'pm' && hours !== 12) hours += 12;
            if (ampm === 'am' && hours === 12) hours = 0;

            const newTime = new Date(now);
            newTime.setHours(hours, minutes, 0, 0);

            // If the time is in the past, assume it's for tomorrow
            if (newTime < now) {
                newTime.setDate(newTime.getDate() + 1);
            }

            return newTime;
        }

        return null;
    }

    async checkSessionFull(sessionId) {
        this.db.get(
            'SELECT game_mode FROM sessions WHERE id = ?',
            [sessionId],
            (err, session) => {
                if (err || !session) return;

                this.db.get(
                    'SELECT COUNT(*) as count FROM session_participants WHERE session_id = ?',
                    [sessionId],
                    (err, result) => {
                        if (err) return;

                        const mode = this.gameModes[session.game_mode];
                        if (result.count >= mode.totalPlayers) {
                            this.db.run(
                                'UPDATE sessions SET status = "full" WHERE id = ?',
                                [sessionId]
                            );
                        }
                    }
                );
            }
        );
    }

    // Stub implementations for remaining handlers
    async handleSetPlaying(interaction) {
        await interaction.reply({ content: 'Set playing feature coming soon!', ephemeral: true });
    }

    async handleWhosPlaying(interaction) {
        await interaction.reply({ content: 'Whos playing feature coming soon!', ephemeral: true });
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
                    return interaction.reply({ content: 'Profile not found! Use `/setup-profile` to create one.', ephemeral: true });
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

                        interaction.reply({ embeds: [embed], components: [row], ephemeral: true });
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
                    return interaction.reply({ content: 'Error cancelling session!', ephemeral: true });
                }

                if (this.changes === 0) {
                    return interaction.reply({ content: 'Session not found or you are not the creator!', ephemeral: true });
                }

                interaction.reply({ content: `Session #${sessionId} has been cancelled.`, ephemeral: true });
            }
        );
    }

    async handleStopPlaying(interaction) {
        await interaction.reply({ content: 'Stop playing feature coming soon!', ephemeral: true });
    }

    async handleLeaveQueue(interaction) {
        const sessionId = interaction.options.getInteger('session-id');

        this.db.run(
            'DELETE FROM session_queue WHERE session_id = ? AND user_id = ?',
            [sessionId, interaction.user.id],
            function(err) {
                if (err) {
                    return interaction.reply({ content: 'Error leaving queue!', ephemeral: true });
                }

                if (this.changes === 0) {
                    return interaction.reply({ content: 'You were not in the queue for this session!', ephemeral: true });
                }

                interaction.reply({ content: `Left the queue for session #${sessionId}.`, ephemeral: true });
            }
        );
    }

    start() {
        this.client.bot = this;
        this.client.login(this.token);
    }
}

// Usage
const token = process.env.BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE';
const bot = new OverwatchScheduleBot(token);
bot.start();

module.exports = OverwatchScheduleBot;
