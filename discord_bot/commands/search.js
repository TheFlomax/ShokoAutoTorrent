// /search command - manually trigger anime search
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const axios = require('axios');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('search')
        .setDescription('Manually trigger a search for missing anime')
        .addIntegerOption(option =>
            option.setName('limit')
                .setDescription('Maximum number of anime to search for')
                .setMinValue(1)
                .setMaxValue(50)
                .setRequired(false)),
    
    async execute(interaction, config, i18n) {
        await interaction.deferReply();
        
        const limit = interaction.options.getInteger('limit') || 0; // 0 = all episodes
        
        // Send initial response
        const limitText = limit === 0 ? i18n.t('discord.cmd.search.all_episodes') : limit.toString();
        const embed = new EmbedBuilder()
            .setColor(0x3498db)
            .setTitle(i18n.t('discord.cmd.search.title_started'))
            .setDescription(i18n.t('discord.cmd.search.desc_started', { limit: limitText }))
            .setTimestamp();
        
        await interaction.editReply({ embeds: [embed] });
        
        try {
            const response = await axios.post(`${config.apiUrl}/search`, {
                limit: limit
            }, {
                timeout: 300000 // 5 minutes timeout
            });
            
            const result = response.data;
            
            // Build result embed
            const resultEmbed = new EmbedBuilder()
                .setColor(0x2ecc71)
                .setTitle(i18n.t('discord.cmd.search.title_completed'))
                .setTimestamp()
                .addFields(
                    { 
                        name: i18n.t('discord.cmd.search.episodes_processed'), 
                        value: `${result.processed || 0}`, 
                        inline: true 
                    },
                    { 
                        name: i18n.t('discord.cmd.search.torrents_added'), 
                        value: `${result.added || 0}`, 
                        inline: true 
                    },
                    { 
                        name: i18n.t('discord.cmd.search.not_found'), 
                        value: `${result.not_found || 0}`, 
                        inline: true 
                    },
                    { 
                        name: i18n.t('discord.cmd.search.duration'), 
                        value: `${result.duration || 'N/A'}`, 
                        inline: true 
                    }
                );
            
            // Add details if available
            if (result.details && result.details.length > 0) {
                const detailText = result.details
                    .slice(0, 5)
                    .map(d => `• ${d.series} - E${String(d.episode).padStart(2, '0')}: ${d.status}`)
                    .join('\n');
                
                resultEmbed.addFields({
                    name: i18n.t('discord.cmd.search.details_title'),
                    value: detailText || i18n.t('discord.cmd.search.details_none')
                });
            }
            
            await interaction.followUp({ embeds: [resultEmbed] });
        } catch (error) {
            console.error('Error triggering search:', error);
            
            const errorEmbed = new EmbedBuilder()
                .setColor(0xe74c3c)
                .setTitle(i18n.t('discord.cmd.search.error_title'))
                .setDescription(i18n.t('discord.cmd.search.error_desc', { error: error.message }))
                .setTimestamp();
            
            await interaction.followUp({ embeds: [errorEmbed] });
        }
    },
};
