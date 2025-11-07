// Notification listener - receives messages from Python app via TCP socket
const net = require('net');
const { EmbedBuilder } = require('discord.js');

class NotificationListener {
    constructor(client, config, i18n, port = 8766) {
        this.client = client;
        this.config = config;
        this.i18n = i18n;
        this.port = port;
        this.server = null;
    }

    start() {
        this.server = net.createServer((socket) => {
            console.log('📡 New connection from Python app');

            let buffer = '';

            socket.on('data', (data) => {
                buffer += data.toString();

                // Process complete messages (newline-delimited JSON)
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete message in buffer

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const notification = JSON.parse(line);
                            this.handleNotification(notification);
                        } catch (error) {
                            console.error('❌ Failed to parse notification:', error);
                        }
                    }
                }
            });

            socket.on('end', () => {
                console.log('📡 Connection closed');
            });

            socket.on('error', (error) => {
                console.error('❌ Socket error:', error);
            });
        });

        this.server.listen(this.port, '127.0.0.1', () => {
            console.log(`✅ Notification listener started on port ${this.port}`);
        });

        this.server.on('error', (error) => {
            console.error('❌ Server error:', error);
        });
    }

    stop() {
        if (this.server) {
            this.server.close();
            console.log('Notification listener stopped');
        }
    }

    async handleNotification(notification) {
        try {
            const embed = new EmbedBuilder()
                .setTitle(notification.title || 'Notification')
                .setColor(notification.color || 0x3498db)
                .setTimestamp(new Date(notification.timestamp));

            if (notification.description) {
                embed.setDescription(notification.description);
            }

            if (notification.fields && Array.isArray(notification.fields)) {
                for (const field of notification.fields) {
                    embed.addFields({
                        name: field.name,
                        value: field.value,
                        inline: field.inline !== false
                    });
                }
            }

            await this.sendEmbed(embed);
        } catch (error) {
            console.error('❌ Error handling notification:', error);
        }
    }

    async sendEmbed(embed) {
        // Send to configured channel
        if (this.config.channelId) {
            try {
                const channel = await this.client.channels.fetch(this.config.channelId);
                if (channel) {
                    await channel.send({ embeds: [embed] });
                }
            } catch (error) {
                console.error('❌ Error sending to channel:', error);
            }
        }

        // Send to allowed users as DM
        if (this.config.allowedUsers && this.config.allowedUsers.length > 0) {
            for (const userId of this.config.allowedUsers) {
                try {
                    const user = await this.client.users.fetch(userId);
                    if (user) {
                        await user.send({ embeds: [embed] });
                    }
                } catch (error) {
                    console.error(`❌ Error sending DM to user ${userId}:`, error);
                }
            }
        }
    }
}

module.exports = NotificationListener;
