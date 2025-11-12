# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

ShokoAutoTorrent is a Python automation tool that bridges Shoko Server, Nyaa.si (anime torrent indexer), and qBittorrent. It automatically searches for and downloads missing anime episodes by fetching missing episodes from Shoko, building smart search queries, searching across multiple Nyaa.si RSS feeds concurrently, scoring results based on preferences, and adding selected torrents to qBittorrent with organized categories and save paths.

**Core workflow**: Shoko API → Missing Episodes → Query Builder → Async RSS Search (Nyaa.si) → Score & Filter → qBittorrent Client → SQLite Cache

## Development Commands

### Setup
```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
.venv/bin/pytest -q

# Run specific test file
.venv/bin/pytest tests/test_parser.py -v
```

### Running Locally
```bash
# Dry-run with limit (safe testing, no actual downloads)
.venv/bin/python main.py --dry-run --limit 2 --lang en

# Configure via .env file first
cp .env.example .env
# Edit .env with your Shoko/qBittorrent credentials
# Note: if password contains $, use $$
```

### Docker Development
```bash
# Build dev image
docker build -t shokoautotorrent:dev .

# Run with dry-run mode (provide .env with settings)
docker run --rm --env-file .env -e SCHEDULE_INTERVAL_HOURS=0 shokoautotorrent:dev --limit 2 --lang fr

# Docker Compose (production-like)
docker compose up -d
docker compose logs -f shoko-auto-torrent
```

### Configuration Management
```bash
# Seed named volume with default config (run once)
docker compose run --rm --user root shoko-auto-torrent \
  sh -c 'install -d -o 1000 -g 1000 /app/config && [ -f /app/config/config.yaml ] || install -o 1000 -g 1000 -m 644 /app/config.yaml /app/config/config.yaml'
```

## Architecture

### Module Structure

**`main.py`**: Entry point and scheduler. Loads config (supports env var substitution with `${VAR}`), initializes clients, runs search/download cycles in a loop (configurable interval), and handles dry-run mode and CLI args (`--dry-run`, `--limit`, `--lang`).

**`modules/shoko_client.py`**: Shoko Server API wrapper using httpx with retry logic. Methods: `get_missing_episodes()` (paginated), `get_series_name()` (cached), `update_series_stats()` (trigger Shoko job before each cycle).

**`modules/nyaa_search.py`**: Nyaa.si RSS searcher with async parallel fetching. Builds RSS URLs from usernames (e.g., Tsundere-Raws, Arcedo). Uses `asyncio.gather()` to fetch multiple RSS feeds concurrently. Supports early_exit optimization (stops at first successful query). Extracts magnets from RSS or by scraping page HTML.

**`modules/qbit_client.py`**: qBittorrent API wrapper using `qbittorrent-api` library. Handles authentication, magnet addition with custom save paths, categories (e.g., `SERIES S01`), and tags. Supports `prefer_http` and `verify_cert` options for TLS issues.

**`modules/discord_notifier.py`**: Discord webhook notifier with rich embeds. Sends notifications after successful downloads with episode metadata (title, season, episode, poster, synopsis) fetched from Shoko API. Uses retry logic and respects dry-run mode.

**`modules/parser.py`**: Title parsing and query building logic.
- `parse_release_title()`: Regex-based parser for formats like `[Group] Title S##E## VOSTFR 1080p WEB -Tsundere-Raws (CR)`
- `build_queries_for_episode()`: Generates multiple query variants (sanitized, shortened, E## fallback)
- `score_release()`: Ranks results by language, quality, version, and source preferences
- `sanitize_title_for_nyaa()`: Removes punctuation that uploaders strip

**`modules/cache.py`**: SQLite cache with two tables: `search_cache` (RSS responses with TTL) and `downloads` (episode_id → avoid re-downloading). Prevents duplicate searches and tracks downloaded episodes.

**`utils/`**: Helper modules for logging (`logger.py`), i18n (`i18n.py` - loads `locales/en.yaml` or `locales/fr.yaml`), notifications (`notifier.py`), and path templating (`pathing.py` - renders `{save_root}/{series}/Season {season2}`).

### Key Design Patterns

**Environment Variable Substitution**: `config.yaml` uses `${SHOKO_URL}` syntax expanded by `expand_env_vars()` recursively at load time.

**Retry Logic**: Shoko and Nyaa HTTP calls use `tenacity` decorator with exponential backoff (3 attempts).

**Async RSS Fetching**: `_search_query_async()` fetches all configured RSS feeds in parallel for a single query using `asyncio.gather()`, significantly reducing search time.

**Early Exit Optimization**: Stops query iteration at first successful match (configurable via `EARLY_EXIT` env var, default true).

**Two-Pass Config Loading**: CLI parser runs twice - first to get `--config` and `--lang`, then full parse after loading config and setting locale.

**Config Path Resolution**: Supports Docker named volume at `/app/config/config.yaml` with auto-seeding from bundled default at `/app/config.yaml`.

### Important Behaviors

- **Dry-run mode**: Default is `true` unless explicitly disabled. CLI `--dry-run` flag always overrides config.
- **Season Inference**: If season not provided by Shoko, infers from series title patterns (e.g., "Season 2", "S02", "2nd Season") or defaults to 1.
- **Query Strategy**: Tries sanitized title + SxxEyy format first, then with VOSTFR, then shortened title, then E## fallback, then original title variations.
- **Shoko Stats Update**: Optionally requests `/Action/UpdateSeriesStats` before fetching missing episodes (configurable via `SHOKO_UPDATE_SERIES_STATS`, default true). Waits configurable seconds (default 20) for Shoko to recalculate.
- **qBittorrent Categories**: Auto-generated as `SERIES_TITLE S##` in uppercase (e.g., `MY HERO ACADEMIA S07`), configurable via `QBIT_CATEGORY_ENABLED`.
- **Save Path Template**: Customizable via `path_template` in config.yaml. Variables: `{save_root}`, `{series}`, `{season}`, `{season2}`, `{episode}`, `{episode2}`, `{quality}`, `{group}`, `{source}`.

## Configuration

Configuration combines `config.yaml` and `.env` (environment variables have priority via `${VAR}` substitution).

**Critical env vars**: `SHOKO_URL`, `SHOKO_API_KEY`, `QBIT_URL`, `QBIT_USERNAME`, `QBIT_PASSWORD`, `SAVE_ROOT`, `DRY_RUN`, `SCHEDULE_INTERVAL_HOURS`.

**qBittorrent HTTPS issues**: If using self-signed cert, set `qbittorrent.verify_cert: false` and/or `qbittorrent.prefer_http: true` in config.yaml.

**Customizing sources**: Edit `config.yaml` → `search.nyaa.users` to add/remove Nyaa.si uploaders (e.g., `[Tsundere-Raws, Arcedo, Erai-raws]`).

**Password escaping**: In `.env`, if password contains `$`, escape as `$$` (e.g., `pass$$word`).

## Testing

Tests use pytest with fixtures defined in `tests/conftest.py`. Main test file is `tests/test_parser.py` covering title parsing, query building, and scoring logic. Tests verify handling of different release formats (Tsundere-Raws, Team Arcedo) and version numbers.

## Docker Notes

- Multi-stage build: builder stage installs deps, runtime stage copies Python packages and app code
- Runs as non-root user `appuser` (UID 1000)
- Default entrypoint: `python main.py --config config.yaml`
- Published to `ghcr.io/theflomax/shokoautotorrent:latest` via GitHub Actions
- Supports multi-arch: linux/amd64, linux/arm64

## Locale/i18n

Supports French (`fr`) and English (`en`) via YAML files in `locales/`. Language selected via `--lang` CLI arg or `general.language` in config. All user-facing messages use `t()` function from `utils.i18n`.
