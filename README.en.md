# Shoko Auto Torrent (Tsundere-Raws)

Automates searching and downloading missing episodes from Shoko to qBittorrent, prioritizing Tsundere-Raws releases from Nyaa.si.

📖 This README is the source of truth. 🐳 Advanced Docker details: see [DOCKER.md](DOCKER.md)

## Requirements
- Python 3.10+
- qBittorrent with WebUI enabled
- Access to Shoko v3 API (API key)

## Installation

### Option 1: Local install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Option 2: Docker (recommended)
```bash
# 1. Copy env example
cp .env.example .env

# 2. Edit .env with your credentials
vim .env  # or nano, code, etc.
# IMPORTANT: If your password contains $, escape it as $$ (ex: pass$$word)

# 3. Build the Docker image
make build
# Or manually: docker build -t shoko-auto-torrent:latest .

# 4. Start the container
make run
# Or manually: docker compose up -d

# 5. View logs
make logs
# Or manually: docker compose logs -f shoko-auto-torrent
```

**Notes:**
- If you need `sudo` for Docker, uncomment `DOCKER` and `DOCKER_COMPOSE` lines in the Makefile
- In dry-run mode (default), nothing will be added to qBittorrent. To disable dry-run, set `DRY_RUN=false` in your environment (e.g., `.env` for Docker, or `export DRY_RUN=false` before `python main.py`).

## Configuration
Copy `config.yaml` and set environment variables for secrets:
- SHOKO_API_KEY
- QBIT_USERNAME
- QBIT_PASSWORD
- DRY_RUN (optional, default: `true`) — set to `false` to actually add items

Adjust `qbittorrent.url`, `save_root`, search preferences (language, quality, sources), etc.

## Usage

### With local Python
```bash
python main.py --config config.yaml --limit 10 --dry-run
```

### With Docker
```bash
# One-off execution
docker-compose run --rm shoko-auto-torrent --limit 10 --dry-run

# Daemon mode (auto start)
docker-compose up -d

# Stop service
docker-compose down
```

### Options
- `--dry-run` forces simulation mode (takes priority over config/env)
- `DRY_RUN` (environment variable, read via `config.yaml`) controls default behavior (without CLI flag). Default: `true`.
- `--limit` caps number of episodes processed
- `--config` specifies configuration file (use outside Docker)
- `--lang` overrides output language (fr or en)

## Structure
See modules under `modules/` and utilities under `utils/`.

## Tests
```
pytest -q
```

## Notes
- Main source: https://nyaa.si/user/Tsundere-Raws (RSS feed used)
- Title parsing based on pattern: `[Title] S##E## VOSTFR 1080p WEB … -Tsundere-Raws (CR)`
- SQLite cache to avoid repeated searches
