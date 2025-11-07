// /missing command - list missing anime episodes
const { SlashCommandBuilder, EmbedBuilder } = require('discord.js');
const axios = require('axios');

module.exports = {
    data: new SlashCommandBuilder()
        .setName('missing')
        .setDescription('List missing anime in media library')
        .addIntegerOption(option =>
            option.setName('limit')
                .setDescription('Maximum number of anime to display')
                .setMinValue(1)
                .setMaxValue(25)
                .setRequired(false)),
    
    async execute(interaction, config, i18n) {
        await interaction.deferReply();
        
        const limit = interaction.options.getInteger('limit') || 10;
        
        try {
            const response = await axios.get(`${config.apiUrl}/missing`, {
                params: { limit },
                timeout: 10000
            });
            
            const missing = response.data.episodes || [];
            
            // No missing episodes
            if (missing.length === 0) {
                const embed = new EmbedBuilder()
                    .setColor(0x2ecc71)
                    .setTitle(i18n.t('discord.cmd.missing.title_none'))
                    .setDescription(i18n.t('discord.cmd.missing.desc_none'))
                    .setTimestamp();
                
                await interaction.editReply({ embeds: [embed] });
                return;
            }
            
            // Build embed with missing episodes
            const embed = new EmbedBuilder()
                .setColor(0xe67e22)
                .setTitle(i18n.t('discord.cmd.missing.title', { count: missing.length }))
                .setTimestamp()
                .setFooter({ text: i18n.t('discord.cmd.missing.footer', { limit }) });
            
            // Group episodes by series
            const grouped = {};
            for (const ep of missing.slice(0, limit)) {
                const series = ep.series || 'Unknown';
                if (!grouped[series]) {
                    grouped[series] = [];
                }
                grouped[series].push(ep.episode);
            }
            
            // Add fields (max 25 fields per embed)
            let count = 0;
            for (const [series, episodes] of Object.entries(grouped)) {
                if (count >= 25) break;
                
                const epList = episodes
                    .sort((a, b) => a - b)
                    .map(e => `E${String(e).padStart(2, '0')}`)
                    .join(', ');
                
                embed.addFields({
                    name: `${i18n.t('discord.cmd.missing.series_prefix')} ${series}`,
                    value: epList,
                    inline: false
                });
                
                count++;
            }
            
            await interaction.editReply({ embeds: [embed] });
        } catch (error) {
            console.error('Error fetching missing episodes:', error);
            
            const errorEmbed = new EmbedBuilder()
                .setColor(0xe74c3c)
                .setTitle(i18n.t('discord.cmd.missing.error_title'))
                .setDescription(i18n.t('discord.cmd.missing.error_desc'))
                .setTimestamp();
            
            await interaction.editReply({ embeds: [errorEmbed] });
        }
    },
};
