# Discord Notifications Feature

## Overview

ShokoAutoTorrent now supports Discord webhook notifications with rich embeds containing episode metadata whenever an anime episode is successfully added to qBittorrent.

## Features

- **Rich Embeds**: Beautiful Discord embeds with episode information
- **Episode Metadata**: Automatically fetched from Shoko Server API
  - Episode title (English or romanized)
  - Episode synopsis/description
  - Episode poster/thumbnail image
  - Series title, season, and episode number
  - Full release title
- **Dry-Run Support**: Respects dry-run mode (no notifications sent in dry-run)
- **Retry Logic**: Automatic retry with exponential backoff for failed webhook requests
- **Optional**: Notifications are completely optional - leave webhook URL empty to disable

## Setup

### 1. Create a Discord Webhook

1. Open Discord and go to your server
2. Right-click on the channel where you want notifications
3. Select **Edit Channel** → **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Copy the webhook URL

### 2. Configure the Webhook URL

Add the webhook URL to your `.env` file:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

Or in `config.yaml`:

```yaml
notify:
  discord_webhook_url: https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### 3. Run the Application

The application will automatically send Discord notifications after each successful download.

## Notification Contents

Each notification embed includes:

- **Title**: 📥 Series Name
- **Description**: Season X • Episode Y
- **Fields**:
  - Episode Title (if available from AniDB/TmDB)
  - Synopsis (if available, truncated to 300 chars)
  - Release (full torrent release name)
- **Thumbnail**: Episode poster image (from TmDB or AniDB)
- **Footer**: "ShokoAutoTorrent"
- **Color**: Blue (#3447003)

## Example Notification

```
📥 My Hero Academia
Season 7 • Episode 1

Episode Title
The Return of the Hero

Synopsis
After a long hiatus, the heroes return to face new challenges...

Release
[Tsundere-Raws] Boku no Hero Academia S07E01 VOSTFR 1080p WEB -Tsundere-Raws (CR)

[Thumbnail: Episode poster image]

ShokoAutoTorrent
```

## Technical Details

### Implementation

- **Module**: `modules/discord_notifier.py`
- **Shoko API**: Uses `/api/v3/Episode/{episodeID}` endpoint with `includeDataFrom=[AniDB, TmDB]`
- **Retry**: 3 attempts with exponential backoff (1-8 seconds)
- **Timeout**: 10 seconds per request

### Data Sources

The notification attempts to fetch metadata in this priority order:

1. **Episode Title**: AniDB (English/Romaji) → TmDB
2. **Synopsis**: AniDB Description → TmDB Overview
3. **Poster**: TmDB Thumbnail → AniDB Thumbnail

### Error Handling

- If episode metadata fetch fails, a notification is still sent with basic info (no poster/synopsis)
- If Discord webhook fails after retries, an error is logged but the download proceeds
- Dry-run mode logs intended notifications without sending them

## Disabling Notifications

To disable Discord notifications:

- Leave `DISCORD_WEBHOOK_URL` empty or unset in `.env`
- Or set `discord_webhook_url: null` in `config.yaml`

## Troubleshooting

### No notifications received

1. Check that `DISCORD_WEBHOOK_URL` is correctly set
2. Verify the webhook URL is valid (test it with a simple curl command)
3. Check application logs for Discord-related errors
4. Make sure you're not in dry-run mode (`DRY_RUN=false`)

### Notifications missing metadata

- Verify Shoko Server has metadata for the episode
- Check that AniDB or TmDB data is linked in Shoko
- Review Shoko logs for metadata fetching issues

### Rate limiting

- Discord webhooks have rate limits (30 requests per minute per webhook)
- With default settings (rate_limit_seconds=3), you should stay well within limits
- If needed, increase the delay between episodes
