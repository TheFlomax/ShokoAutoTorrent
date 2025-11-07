// Main Discord bot entry point
const { Client, GatewayIntentBits, Collection, Events, REST, Routes } = require('discord.js');
const fs = require('fs');
const path = require('path');
const I18n = require('./i18n');
const NotificationListener = require('./listener');

// Configuration from environment variables
const config = {
    token: process.env.DISCORD_BOT_TOKEN,
    allowedUsers: process.env.DISCORD_ALLOWED_USER_IDS?.split(',').map(id => id.trim()).filter(id => id) || [],
    channelId: process.env.DISCORD_CHANNEL_ID || null,
    apiUrl: process.env.INTERNAL_API_URL || 'http://localhost:8765',
    language: process.env.DISCORD_LANGUAGE || process.env.LANGUAGE || 'en',
};

// Validate configuration
if (!config.token) {
    console.error('ERROR: DISCORD_BOT_TOKEN is required!');
    process.exit(1);
}

// Initialize i18n
const i18n = new I18n(config.language);

// Initialize Discord client
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.DirectMessages,
    ]
});

// Commands collection
client.commands = new Collection();

// Load commands
const commandsPath = path.join(__dirname, 'commands');
if (fs.existsSync(commandsPath)) {
    const commandFiles = fs.readdirSync(commandsPath).filter(file => file.endsWith('.js'));
    
    for (const file of commandFiles) {
        const filePath = path.join(commandsPath, file);
        const command = require(filePath);
        
        if ('data' in command && 'execute' in command) {
            client.commands.set(command.data.name, command);
            console.log(`✅ Loaded command: ${command.data.name}`);
        } else {
            console.warn(`⚠️  Command at ${filePath} is missing "data" or "execute" property`);
        }
    }
}

// Notification listener
const notificationListener = new NotificationListener(client, config, i18n);

// Event: Bot ready
client.once(Events.ClientReady, async (c) => {
    console.log(`✅ Discord bot logged in as ${c.user.tag}`);
    
    // Register slash commands
    const commands = Array.from(client.commands.values()).map(cmd => cmd.data.toJSON());
    
    try {
        const rest = new REST({ version: '10' }).setToken(config.token);
        console.log(`🔄 Registering ${commands.length} slash commands...`);
        
        await rest.put(
            Routes.applicationCommands(c.user.id),
            { body: commands }
        );
        
        console.log('✅ Slash commands registered successfully!');
    } catch (error) {
        console.error('❌ Error registering slash commands:', error);
    }
    
    // Start notification listener
    notificationListener.start();
    
    // Send startup notification
    await sendNotification(
        i18n.t('discord.bot.startup_title'),
        i18n.t('discord.bot.startup_desc')
    );
});

// Event: Interaction (slash commands)
client.on(Events.InteractionCreate, async (interaction) => {
    if (!interaction.isChatInputCommand()) return;
    
    // Check user permissions
    if (config.allowedUsers.length > 0 && !config.allowedUsers.includes(interaction.user.id)) {
        await interaction.reply({
            content: i18n.t('discord.cmd.error.unauthorized'),
            ephemeral: true
        });
        return;
    }
    
    const command = client.commands.get(interaction.commandName);
    
    if (!command) {
        console.error(`❌ Command not found: ${interaction.commandName}`);
        return;
    }
    
    try {
        await command.execute(interaction, config, i18n);
    } catch (error) {
        console.error(`❌ Error executing command ${interaction.commandName}:`, error);
        
        const errorMessage = {
            content: i18n.t('discord.cmd.error.command_error'),
            ephemeral: true
        };
        
        if (interaction.replied || interaction.deferred) {
            await interaction.followUp(errorMessage);
        } else {
            await interaction.reply(errorMessage);
        }
    }
});

// Helper function to send notifications
async function sendNotification(title, description, fields = [], color = 0x3498db) {
    const embed = {
        title: title,
        description: description,
        color: color,
        timestamp: new Date().toISOString(),
        fields: fields
    };
    
    // Send to configured channel
    if (config.channelId) {
        try {
            const channel = await client.channels.fetch(config.channelId);
            if (channel) {
                await channel.send({ embeds: [embed] });
            }
        } catch (error) {
            console.error('❌ Error sending notification to channel:', error);
        }
    }
    
    // Send as DM to allowed users
    if (config.allowedUsers.length > 0) {
        for (const userId of config.allowedUsers) {
            try {
                const user = await client.users.fetch(userId);
                if (user) {
                    await user.send({ embeds: [embed] });
                }
            } catch (error) {
                console.error(`❌ Error sending DM to user ${userId}:`, error);
            }
        }
    }
}

// Expose sendNotification for external use
client.sendNotification = sendNotification;

// Error handling
client.on('error', error => {
    console.error('❌ Discord client error:', error);
});

process.on('unhandledRejection', error => {
    console.error('❌ Unhandled promise rejection:', error);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🔄 Shutting down Discord bot...');
    notificationListener.stop();
    await sendNotification(
        i18n.t('discord.bot.shutdown_title'),
        i18n.t('discord.bot.shutdown_desc'),
        [],
        0xe74c3c
    );
    await client.destroy();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n🔄 Shutting down Discord bot...');
    notificationListener.stop();
    await sendNotification(
        i18n.t('discord.bot.shutdown_title'),
        i18n.t('discord.bot.shutdown_desc'),
        [],
        0xe74c3c
    );
    await client.destroy();
    process.exit(0);
});

// Login
client.login(config.token).catch(error => {
    console.error('❌ Failed to login to Discord:', error);
    process.exit(1);
});

module.exports = { client, sendNotification, i18n };
