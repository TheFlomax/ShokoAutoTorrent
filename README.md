# Shoko Auto Torrent (Tsundere-Raws)

Automates searching and downloading missing episodes from Shoko to qBittorrent, prioritizing Tsundere-Raws releases from Nyaa.si.

[Version Française ici !](README.fr.md)

## Ultra-fast start (Docker Compose)
1) Copy env example
```bash
cp .env.example .env
```
2) Edit `.env` (if a password contains $, use $$)
3) Start in background
```bash
docker compose up -d
```
4) Tail logs (optional)
```bash
docker compose logs -f shoko-auto-torrent
```
5) One-off run (dry-run by default)
```bash
docker compose run --rm shoko-auto-torrent --limit 5 --dry-run --lang en
```

Minimal compose
```yaml
services:
  shoko-auto-torrent:
    image: ghcr.io/theflomax/shokoautotorrent:latest
    restart: unless-stopped
    env_file: .env
    volumes:
      - config:/app/config
    # To edit a local file instead of the named volume:
    #  - ./config.yaml:/app/config/config.yaml:ro

volumes:
  config:
```

## Configuration
- Variables in `.env` (SHOKO_URL, SHOKO_API_KEY, QBIT_URL, QBIT_USERNAME, QBIT_PASSWORD, SAVE_ROOT, DRY_RUN, SCHEDULE_INTERVAL_HOURS)
- If your qBittorrent uses an invalid HTTPS cert, set `qbittorrent.verify_cert: false` and/or `qbittorrent.prefer_http: true` in config.yaml.
- A default config is bundled in the image and reads environment variables.
- Named volume `config` (mounted at `/app/config`) persists your configuration.
- Seed the volume once with the default config:
```bash
docker compose run --rm --user root shoko-auto-torrent \
  sh -c 'install -d -o 1000 -g 1000 /app/config && [ -f /app/config/config.yaml ] || install -o 1000 -g 1000 -m 644 /app/config.yaml /app/config/config.yaml'
```
- Or mount a local file: `- ./config.yaml:/app/config/config.yaml:ro`

## Usage (key options)
- `--dry-run` forces simulation (overrides config/env)
- `--limit` caps the number of processed episodes
- `--lang` sets output language (`fr` or `en`)

## Notes
- Main source: https://nyaa.si/user/Tsundere-Raws (RSS)
- Title parsing pattern: `[Title] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- SQLite cache avoids repeated searches
- Title parsing based on pattern: `[Title] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- SQLite cache to avoid repeated searches
