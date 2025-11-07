// i18n module - reads locale files from parent project
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

class I18n {
    constructor(language = 'en') {
        this.language = language;
        this.localesDir = path.join(__dirname, '..', 'locales');
        this.messages = this.loadLocale(this.language);
    }

    loadLocale(lang) {
        const filePath = path.join(this.localesDir, `${lang}.yaml`);
        
        try {
            if (!fs.existsSync(filePath)) {
                // Fallback to English
                const fallbackPath = path.join(this.localesDir, 'en.yaml');
                if (fs.existsSync(fallbackPath)) {
                    return yaml.load(fs.readFileSync(fallbackPath, 'utf8')) || {};
                }
                return {};
            }
            
            return yaml.load(fs.readFileSync(filePath, 'utf8')) || {};
        } catch (error) {
            console.error(`Failed to load locale ${lang}:`, error);
            return {};
        }
    }

    t(key, params = {}) {
        const keys = key.split('.');
        let text = this.messages;
        
        for (const k of keys) {
            if (text && typeof text === 'object' && k in text) {
                text = text[k];
            } else {
                text = null;
                break;
            }
        }
        
        if (typeof text !== 'string') {
            return key; // Return key itself if not found
        }
        
        // Replace {param} placeholders
        return text.replace(/\{(\w+)\}/g, (match, paramName) => {
            return params[paramName] !== undefined ? params[paramName] : match;
        });
    }

    setLanguage(lang) {
        this.language = lang;
        this.messages = this.loadLocale(lang);
    }
}

module.exports = I18n;
