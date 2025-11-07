// /status command - display current application status
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const axios = require('axios');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('status')
        .setDescription('Display current ShokoAutoTorrent status'),
    
    async execute(interaction, config, i18n) {
        await interaction.deferReply();
        
        try {
            const response = await axios.get(`${config.apiUrl}/status`, { timeout: 5000 });
            const status = response.data;
            
            const embed = new EmbedBuilder()
                .setColor(0x2ecc71)
                .setTitle(i18n.t('discord.cmd.status.title'))
                .setTimestamp();
            
            // Application status
            const appStatus = status.running 
                ? i18n.t('discord.cmd.status.running')
                : i18n.t('discord.cmd.status.stopped');
            
            embed.addFields(
                { 
                    name: i18n.t('discord.cmd.status.application'), 
                    value: appStatus, 
                    inline: true 
                },
                { 
                    name: i18n.t('discord.cmd.status.last_cycle'), 
                    value: status.last_cycle || i18n.t('discord.cmd.status.none'), 
                    inline: true 
                },
                { 
                    name: i18n.t('discord.cmd.status.torrents_added'), 
                    value: `${status.total_added || 0}`, 
                    inline: true 
                },
                { 
                    name: i18n.t('discord.cmd.status.not_found'), 
                    value: `${status.total_not_found || 0}`, 
                    inline: true 
                },
                { 
                    name: i18n.t('discord.cmd.status.next_cycle'), 
                    value: status.next_run || i18n.t('discord.cmd.status.none'), 
                    inline: true 
                }
            );
            
            // Current episode if available
            if (status.current_episode) {
                embed.addFields({ 
                    name: i18n.t('discord.cmd.status.current_episode'), 
                    value: `${status.current_episode.series} - E${status.current_episode.episode}` 
                });
            }
            
            await interaction.editReply({ embeds: [embed] });
        } catch (error) {
            console.error('Error fetching status:', error);
            
            const errorEmbed = new EmbedBuilder()
                .setColor(0xe74c3c)
                .setTitle(i18n.t('discord.cmd.status.error_title'))
                .setDescription(i18n.t('discord.cmd.status.error_desc'))
                .setTimestamp();
            
            await interaction.editReply({ embeds: [errorEmbed] });
        }
    },
};
