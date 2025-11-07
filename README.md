# Shoko Auto Torrent 🎐

![Mascot](https://files.catbox.moe/0ydja8.jpg)

Automates searching and downloading missing episodes from Shoko to qBittorrent, prioritizing Tsundere-Raws releases from Nyaa.si.

[Version Française ici 🇫🇷🇫🇷🇫🇷](README.fr.md)

## ✨ Key Features

- 🔍 **Smart Search**: Intelligent title sanitization and query building for accurate Nyaa.si matches
- ⚡ **Async Performance**: Parallel RSS feed fetching for blazing-fast episode discovery
- 🎯 **Early Exit**: Stop at first successful query to save time (configurable)
- 🔄 **Scheduled Runs**: Automatic periodic checks (configurable interval)
- 🎨 **Quality Preferences**: Prioritize your preferred quality, language, and sources
- 💾 **Smart Caching**: SQLite-based cache to avoid duplicate searches and downloads
- 🐳 **Docker Ready**: Easy deployment with Docker Compose
- 🌍 **Multilingual**: Support for French and English output
- 🏷️ **Organized Downloads**: Automatic categorization and tagging in qBittorrent
- 🛡️ **Dry-Run Mode**: Test your configuration safely before actual downloads
- 🤖 **Discord Bot** (optional): Monitor and control via Discord slash commands - [Setup Guide](DISCORD.md)

## Prerequisites
- Requires Shoko Server to provide the API. Not affiliated with the Shoko project.
- Website: https://shokoanime.com/ — Docs: https://docs.shokoanime.com/

## Quickstart (Docker Compose)
1) Copy env example.
```bash
cp .env.example .env
```
2) Edit `.env` (if a password contains $, use `$$`)
3) Start in background
```bash
docker compose up -d
```
4) Tail logs (optional)
```bash
docker compose logs -f shoko-auto-torrent
```

Minimal compose
```yaml
services:
  shoko-auto-torrent:
    image: ghcr.io/theflomax/shokoautotorrent:latest
    container_name: shoko-auto-torrent
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
- Variables in `.env`:
  - SHOKO_URL, SHOKO_API_KEY
  - QBIT_URL, QBIT_USERNAME, QBIT_PASSWORD
  - SAVE_ROOT, DRY_RUN, EARLY_EXIT, SCHEDULE_INTERVAL_HOURS
  - SHOKO_UPDATE_SERIES_STATS (default: true) — run Shoko /Action/UpdateSeriesStats at the start of each cycle
  - SHOKO_UPDATE_WAIT_SECONDS (default: 20) — wait time after requesting the update
- If your qBittorrent uses an invalid HTTPS cert, set `qbittorrent.verify_cert: false` and/or `qbittorrent.prefer_http: true` in config.yaml.
- A default config is bundled in the image and reads environment variables.
- Named volume `config` (mounted at `/app/config`) persists your configuration.
- Seed the volume once with the default config:
```bash
docker compose run --rm --user root shoko-auto-torrent \
  sh -c 'install -d -o 1000 -g 1000 /app/config && [ -f /app/config/config.yaml ] || install -o 1000 -g 1000 -m 644 /app/config.yaml /app/config/config.yaml'
```
- Or mount a local file: `- ./config.yaml:/app/config/config.yaml:ro`

### Shoko Series Stats Update
- When enabled, the app requests `GET /api/v3/Action/UpdateSeriesStats` before fetching missing episodes, then waits `SHOKO_UPDATE_WAIT_SECONDS` to let Shoko recalculate stats and group filters.
- This helps ensure the missing list is up-to-date.

## Usage (key options)
- `--dry-run` forces simulation (overrides config/env)
- `--limit` caps the number of processed episodes
- `--lang` sets output language (`fr` or `en`)

## Development / Local Testing
- Python
  ```bash
  python -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
  .venv/bin/pytest -q
  .venv/bin/python main.py --dry-run --limit 2 --lang en
  ```
- Docker
  ```bash
  docker build -t shokoautotorrent:dev .
  # provide a .env file with your settings (see .env.example)
  docker run --rm --env-file .env -e SCHEDULE_INTERVAL_HOURS=0 shokoautotorrent:dev --limit 2 --lang fr
  ```

## Notes
- Main source: https://nyaa.si/user/Tsundere-Raws (RSS)
- You can add the source in `config.yaml` by adding nyaa.si usernames (ex: `users: [Tsundere-Raws, Arcedo, Erai-raws]`).
- Title parsing pattern: `[Title] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- SQLite cache avoids repeated searches

---

## Disclaimer

### Intended Use

Shoko Auto Torrent automates search and queuing of torrents via RSS and qBittorrent.
It is intended for legitimate uses (e.g., automating downloads of content you are authorized to access). It must not be used to download illegal, harmful, or unauthorized content.

### Administrator Responsibility

As a self-hosted tool, operators are solely responsible for:

- Compliance with all applicable local, national, and international laws
- Proper configuration and security of their environment (Shoko, qBittorrent, network, etc.)
- Monitoring and moderating what is downloaded through their setup
- Defining and enforcing appropriate usage policies for users of their environment

### No Warranty

THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Recommended Practices

We strongly recommend that operators:

- Restrict access to the environment (Shoko/qBittorrent) with proper authentication
- Configure appropriate save paths, categories, and tags
- Set reasonable limits (rate limits, item limits) and review logs regularly
- Consider additional monitoring and backups in production

By using Shoko Auto Torrent, you acknowledge you have read and understood this disclaimer.
