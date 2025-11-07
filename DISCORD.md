# Discord Bot Integration

[🇫🇷 Version Française](DISCORD.fr.md)

ShokoAutoTorrent includes an optional Discord bot for monitoring and remote control.

## Features

- **Automatic Notifications**: Cycle reports, startup/shutdown, errors, found episodes
- **Slash Commands**:
  - `/status` - Display application status
  - `/missing [limit]` - List missing anime
  - `/search [limit]` - Manually trigger search
- **Multi-language**: Uses the same locales (FR/EN) as the main application
- **Optional**: Runs only if `DISCORD_BOT_TOKEN` is provided

## Quick Setup

### 1. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create New Application
3. Go to "Bot" tab → Add Bot → Copy token
4. In "OAuth2" → "URL Generator":
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: Send Messages, Embed Links, Use Slash Commands
5. Use generated URL to invite bot to your server

### 2. Get Discord IDs

Enable Developer Mode: Settings > Advanced > Developer Mode

- **Channel ID**: Right-click channel → Copy ID
- **User ID**: Right-click your username → Copy ID

### 3. Configure Environment

Edit `.env`:

```env
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_CHANNEL_ID=1234567890123456789
DISCORD_ALLOWED_USER_IDS=123456789012345678,987654321098765432
DISCORD_LANGUAGE=en
```

### 4. Start

```bash
docker-compose up -d
```

The bot will:
- Start automatically if `DISCORD_BOT_TOKEN` is set
- Send notifications to the configured channel and/or DMs
- Register slash commands (available within 1 hour)

## Configuration Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Yes* | Discord bot token | - |
| `DISCORD_CHANNEL_ID` | No | Channel for notifications | - |
| `DISCORD_ALLOWED_USER_IDS` | No | Comma-separated user IDs for commands/DMs | - |
| `DISCORD_LANGUAGE` | No | Bot language (`en` or `fr`) | `en` |
| `INTERNAL_API_URL` | No | Internal API URL | `http://localhost:8765` |

*Required only if you want to use the Discord bot

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  Python App         │  HTTP   │  Discord Bot (Node)  │
│  modules/discord_bot│◄────────┤  discord_bot/        │
│  - InternalAPIServer│         │  - Slash Commands    │
│  - DiscordNotifier  ├────────►│  - Notifications     │
│                     │ Socket  │                      │
└─────────────────────┘         └──────────┬───────────┘
                                           │
                                           ▼
                                    Discord API
```

**Communication**:
- Python → Discord: TCP socket (port 8766) for real-time notifications
- Discord → Python: HTTP API (port 8765) for slash commands

## Usage Examples

### In Python Code

```python
from modules.discord_bot import InternalAPIServer, DiscordNotifier

# Initialize
api_server = InternalAPIServer(host="0.0.0.0", port=8765)
api_server.start()

discord = DiscordNotifier(host="localhost", port=8766)

# Send notifications
discord.notify_startup({"Dry Run": "false", "Max Items": "10"})
discord.notify_cycle_report(
    duration=45.2,
    total_episodes=20,
    processed=10,
    added=7,
    not_found=3,
    details=[
        {"series": "One Piece", "episode": 1045, "status": "✅ Added"},
        # ...
    ]
)

# Update state for /status command
api_server.update_state(
    running=True,
    total_added=150,
    missing_episodes=[
        {"series": "One Piece", "episode": 1046},
        # ...
    ]
)

# Set callback for /search command
def manual_search(limit: int) -> dict:
    # Your search logic
    return {"processed": 10, "added": 7, "not_found": 3}

api_server.set_search_callback(manual_search)
```

## Troubleshooting

### Bot doesn't appear online
- Check `DISCORD_BOT_TOKEN` is correct
- Verify bot hasn't been removed from server
- Check logs: `docker logs shoko-auto-torrent`

### Slash commands don't appear
- Wait up to 1 hour for Discord sync
- Restart: `docker-compose restart`
- Verify bot permissions on server

### No notifications received
- Check `DISCORD_CHANNEL_ID` is correct
- Verify bot has "Send Messages" permission
- Check DMs are enabled if using DMs
- Verify user IDs in `DISCORD_ALLOWED_USER_IDS`

### "Unauthorized" error
- Add your User ID to `DISCORD_ALLOWED_USER_IDS`

## Security

- **Never share your bot token**
- **Don't commit `.env` file**
- Limit access with `DISCORD_ALLOWED_USER_IDS`
- Ports 8765 and 8766 are internal only (not exposed)

## Disabling Discord Bot

Leave `DISCORD_BOT_TOKEN` empty or comment it out:

```env
# DISCORD_BOT_TOKEN=
```

The application will work normally without Discord integration.
