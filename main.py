#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from modules.shoko_client import ShokoClient
from modules.nyaa_search import NyaaSearcher
from modules.qbit_client import QbitClient
from modules.parser import build_queries_for_episode, infer_season_from_title
from modules.cache import Cache
from modules.discord_bot import InternalAPIServer, DiscordNotifier
from utils.logger import setup_logging
from utils.notifier import Notifier
from utils.pathing import render_path_template, safe_name
from utils.i18n import set_locale, t


def expand_env_vars(obj):
    if isinstance(obj, dict):
        return {k: expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env_vars(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        return os.environ.get(obj[2:-1], "")
    return obj


def to_bool(value, default=False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        s = value.strip().lower()
        if s == "":
            return default
        if s in ("1", "true", "yes", "on"):  # common truthy
            return True
        if s in ("0", "false", "no", "off"):  # common falsy
            return False
    return bool(value)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return expand_env_vars(cfg)


def ensure_cache_db(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def run_cycle(
    cfg: dict,
    logger: logging.Logger,
    qbit: QbitClient,
    shoko: ShokoClient,
    nyaa: NyaaSearcher,
    cache: Cache,
    notifier: Notifier,
    max_items: int,
    early_exit: bool = True,
    discord_notifier: DiscordNotifier = None,
    api_server: InternalAPIServer = None,
    language: str = "en",
):
    # Skip qBittorrent connection check in dry-run mode to avoid IP bans during testing
    if not qbit.dry_run:
        try:
            qbit.ensure_connected()
        except Exception as e:
            logger.error(t("log.qbit_connect_fail"), e)
            return
    else:
        logger.info("Dry-run mode: skipping qBittorrent connection check")

    # Request Shoko to update series stats and wait a bit to ensure fresh data (configurable)
    update_enabled = to_bool(cfg.get("general", {}).get("shoko_update_series_stats", None), default=True)
    wait_raw = cfg.get("general", {}).get("shoko_update_wait_seconds", None)
    try:
        wait_seconds = int(str(wait_raw).strip()) if str(wait_raw).strip() != "" else 20
    except Exception:
        wait_seconds = 20
    if update_enabled:
        # Notify Discord about Shoko update
        if discord_notifier:
            progress_msg = t("log.shoko_update_series_stats") if language == "en" else "Mise à jour des statistiques des séries Shoko..."
            discord_notifier.notify_progress(progress_msg, countdown_seconds=wait_seconds)
        
        logger.info(t("log.shoko_update_series_stats"))
        try:
            shoko.update_series_stats()
        except Exception as e:
            logger.warning(t("log.shoko_update_series_stats_failed"), e)
        if wait_seconds > 0:
            logger.info(t("log.waiting_after_shoko_update"), wait_seconds)
            time.sleep(wait_seconds)

    logger.info(t("log.fetching_missing"))
    episodes = shoko.get_missing_episodes(
        page_size=int(cfg["shoko"].get("page_size", 100)),
        include_data_from=cfg["shoko"].get("include_data_from", ["AniDB"]),
        collecting_only=bool(cfg["shoko"].get("collecting_only", False)),
        include_xrefs=True,
    )

    logger.info(t("log.missing_found_count"), len(episodes))

    # Update missing episodes for Discord /missing command
    if api_server:
        missing_list = []
        for ep in episodes:
            shoko_series_id = (ep.get("IDs") or {}).get("ParentSeries")
            ep_num = (ep.get("AniDB") or {}).get("EpisodeNumber")
            series_title = shoko.get_series_name(shoko_series_id)
            if series_title and ep_num:
                missing_list.append({
                    "series": series_title,
                    "episode": int(ep_num),
                    "shoko_id": (ep.get("IDs") or {}).get("ID") or ep.get("ID")
                })
        api_server.update_state(missing_episodes=missing_list)

    processed = 0
    added_count = 0
    not_found_count = 0
    cycle_details = []
    for ep in episodes:
        if processed >= max_items:
            break

        shoko_ep_id = (ep.get("IDs") or {}).get("ID") or ep.get("ID")
        shoko_series_id = (ep.get("IDs") or {}).get("ParentSeries")
        ep_num = (ep.get("AniDB") or {}).get("EpisodeNumber")
        series_title = shoko.get_series_name(shoko_series_id)
        season = None  # Non fourni directement; on s'appuie sur requêtes E## + VOSTFR

        if not series_title or not ep_num:
            logger.debug(t("log.insufficient_info"), series_title, ep_num, shoko_ep_id)
            continue

        queries = build_queries_for_episode(series_title, season, ep_num)

        disp_season = int(season) if season else infer_season_from_title(series_title, default=1)
        logger.info(t("log.searching_for"), series_title, f"{int(disp_season):02d}", int(ep_num), shoko_ep_id)

        # Update current episode for Discord /status command
        if api_server:
            api_server.update_state(
                current_episode={"series": series_title, "episode": int(ep_num)}
            )

        results = nyaa.search_tsundere(queries, early_exit=early_exit)
        if not results:
            logger.info(t("log.no_results"), queries[0])
            not_found_count += 1
            cycle_details.append({
                "series": series_title,
                "episode": int(ep_num),
                "status": "❌ Non trouvé" if language == "fr" else "❌ Not found"
            })
            processed += 1
            continue

        # Prendre le meilleur résultat selon préférences
        best = results[0]
        magnet = best.get("magnet") or best.get("link")
        title = best.get("title")
        parsed = best.get("parsed") or {}

        if not magnet:
            logger.debug(t("log.no_link_for_title"), title)
            not_found_count += 1
            cycle_details.append({
                "series": series_title,
                "episode": int(ep_num),
                "status": "❌ Pas de lien" if language == "fr" else "❌ No link"
            })
            processed += 1
            continue

        # Category: SERIES Sxx in uppercase (optional)
        s_for_cat = int(season) if season else infer_season_from_title(series_title, default=1)
        category_enabled = True if cfg["qbittorrent"].get("category_enabled", None) is None else to_bool(cfg["qbittorrent"].get("category_enabled"), True)
        category = f"{safe_name(series_title).upper()} S{s_for_cat:02d}" if category_enabled else None
        # Build customizable save path from template
        tmpl = cfg["qbittorrent"].get("path_template") or "{save_root}/{series}"
        save_root = cfg["qbittorrent"].get("save_root", "/data/anime")
        mapping = {
            'save_root': save_root,
            'series': safe_name(series_title),
            'season': str(season or ""),
            'season2': f"{int(season):02d}" if season else "",
            'episode': str(ep_num or ""),
            'episode2': f"{int(ep_num):02d}" if ep_num else "",
            'quality': parsed.get('quality') or "",
            'group': parsed.get('group') or "",
            'source': parsed.get('source') or "",
        }
        save_path = render_path_template(tmpl, mapping)
        # Tag: single tag (optional, customizable)
        tag_enabled = True if cfg["qbittorrent"].get("tag_enabled", None) is None else to_bool(cfg["qbittorrent"].get("tag_enabled"), True)
        tag_value = str(cfg["qbittorrent"].get("tag_value", "ShokoAT")) if tag_enabled else ""
        tags = tag_value if tag_enabled and tag_value else ""

        if cache.is_episode_downloaded(shoko_ep_id):
            logger.info(t("log.already_downloaded_cache"), title)
            cycle_details.append({
                "series": series_title,
                "episode": int(ep_num),
                "status": "✅ Déjà ajouté" if language == "fr" else "✅ Already added"
            })
            processed += 1
            continue

        logger.info(t("log.adding_qbit"), title)
        try:
            qbit.add_magnet(magnet, save_path=save_path, category=category, tags=tags)
            cache.mark_episode_downloaded(shoko_ep_id, shoko_series_id, magnet, title)
            added_count += 1
            cycle_details.append({
                "series": series_title,
                "episode": int(ep_num),
                "status": "✅ Ajouté" if language == "fr" else "✅ Added"
            })
            # Notify Discord of found episode
            if discord_notifier:
                discord_notifier.notify_episode_found(series_title, int(ep_num), title)
        except Exception as e:
            logger.error(t("log.qbit_add_fail"), e)
            notifier.notify_error(t("notify.qbit_add_fail_title", title=title), str(e))
            cycle_details.append({
                "series": series_title,
                "episode": int(ep_num),
                "status": "❌ Erreur" if language == "fr" else "❌ Error"
            })

        processed += 1
        time.sleep(nyaa.rate_limit_seconds)

    logger.info(t("log.processing_done_count"), processed)
    logger.info(t("log.cycle_summary"), len(episodes), added_count, not_found_count)

    # Clear current episode after cycle
    if api_server:
        api_server.update_state(current_episode=None)

    return {
        "processed": processed,
        "added": added_count,
        "not_found": not_found_count,
        "details": cycle_details
    }


def main():
    # First pass parser to get --config and --lang early
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", default="config.yaml")
    pre.add_argument("--lang", default=None)
    pre_args, _ = pre.parse_known_args()

    # Resolve config path, supporting named volume at /app/config/config.yaml
    CONFIG_DIR = Path("/app/config")
    CFG_IN_VOLUME = CONFIG_DIR / "config.yaml"
    DEFAULT_CFG_IN_IMAGE = Path("/app/config.yaml")

    def resolve_config_path(requested: str) -> Path:
        req = Path(requested)
        if str(req) == "config.yaml":
            if CFG_IN_VOLUME.exists():
                return CFG_IN_VOLUME
            # Try to seed from default if possible
            try:
                if CONFIG_DIR.exists() and DEFAULT_CFG_IN_IMAGE.exists() and os.access(CONFIG_DIR, os.W_OK):
                    import shutil
                    shutil.copy2(DEFAULT_CFG_IN_IMAGE, CFG_IN_VOLUME)
                    return CFG_IN_VOLUME
            except Exception:
                pass
            return DEFAULT_CFG_IN_IMAGE if DEFAULT_CFG_IN_IMAGE.exists() else req
        return req

    pre_cfg_path = resolve_config_path(pre_args.config)
    cfg = load_config(pre_cfg_path)
    language = pre_args.lang or str(cfg.get("general", {}).get("language", "fr"))
    set_locale(language)

    parser = argparse.ArgumentParser(description=t("cli.description"))
    parser.add_argument("--config", default="config.yaml", help=t("cli.config_help"))
    parser.add_argument("--limit", type=int, default=None, help=t("cli.limit_help"))
    parser.add_argument("--dry-run", action="store_true", help=t("cli.dry_run_help"))
    parser.add_argument("--lang", default=None, help=t("cli.lang_help"))
    args = parser.parse_args()

    # Re-load config with final resolution
    cfg_path = resolve_config_path(args.config)
    cfg = load_config(cfg_path)

    log_level = getattr(logging, str(cfg.get("general", {}).get("log_level", "INFO")).upper(), logging.INFO)
    setup_logging(level=log_level)
    logger = logging.getLogger("main")

    # DRY-RUN: CLI flag overrides config/env; default True if unset
    dry_run_cfg = cfg.get("general", {}).get("dry_run", None)
    dry_run = args.dry_run or to_bool(dry_run_cfg, default=True)
    max_items = args.limit or int(cfg.get("general", {}).get("max_items", 10))
    
    # EARLY_EXIT: default True if unset
    early_exit_cfg = cfg.get("general", {}).get("early_exit", None)
    early_exit = to_bool(early_exit_cfg, default=True)

    # Scheduler interval in hours (default 24h if unset/empty)
    sched_hours_raw = cfg.get("general", {}).get("schedule_hours", None)
    try:
        schedule_hours = int(str(sched_hours_raw).strip()) if str(sched_hours_raw).strip() != "" else 24
    except Exception:
        schedule_hours = 24

    cache_path = Path(cfg.get("cache", {}).get("path", ".cache/shoko_auto_torrent.db"))
    ensure_cache_db(cache_path)
    cache = Cache(cache_path, ttl_hours=int(cfg.get("cache", {}).get("ttl_hours", 24)))

    notifier = Notifier(cfg.get("notify", {}))

    shoko = ShokoClient(
        base_url=cfg["shoko"]["base_url"],
        api_key=cfg["shoko"]["api_key"],
    )

    nyaa = NyaaSearcher(
        users=cfg["search"]["nyaa"].get("users", ["Tsundere-Raws"]),
        rss_urls=cfg["search"]["nyaa"].get("rss_urls", []),
        preferred=cfg["search"]["nyaa"].get("preferred", {}),
        rate_limit_seconds=int(cfg["search"]["nyaa"].get("rate_limit_seconds", 3)),
        cache=cache,
    )

    qbit = QbitClient(
        url=cfg["qbittorrent"]["url"],
        username=cfg["qbittorrent"].get("username", ""),
        password=cfg["qbittorrent"].get("password", ""),
        dry_run=dry_run,
        verify_cert=bool(cfg["qbittorrent"].get("verify_cert", True)),
        prefer_http=bool(cfg["qbittorrent"].get("prefer_http", False)),
    )

    # Initialize Discord integration if enabled
    discord_enabled = bool(os.environ.get("DISCORD_BOT_TOKEN"))
    api_server = None
    discord_notifier = None

    if discord_enabled:
        logger.info("Discord bot enabled, starting internal API server")
        api_server = InternalAPIServer(host="0.0.0.0", port=8765)
        api_server.start()

        discord_notifier = DiscordNotifier(host="localhost", port=8766)

        # Set manual search callback for Discord /search command
        def manual_search_callback(limit: int) -> dict:
            # limit=0 means search all episodes
            search_limit = 999999 if limit == 0 else limit
            logger.info(f"Manual search triggered from Discord: limit={limit} (actual={search_limit})")
            
            start_time = time.time()
            result = run_cycle(
                cfg, logger, qbit, shoko, nyaa, cache, notifier,
                max_items=search_limit, early_exit=early_exit,
                discord_notifier=discord_notifier, api_server=api_server,
                language=language
            )
            duration = time.time() - start_time
            result["duration"] = f"{duration:.1f}s"
            return result

        api_server.set_search_callback(manual_search_callback)

        # Send startup notification
        discord_notifier.notify_startup({
            "Dry Run": str(dry_run),
            "Max Items": str(max_items),
            "Schedule Hours": str(schedule_hours),
            "Language": language
        })

        # Initialize state
        api_server.update_state(
            running=True,
            last_cycle=None,
            next_run=datetime.now() + timedelta(hours=schedule_hours) if schedule_hours > 0 else None,
            total_added=0,
            total_not_found=0
        )

    logger.info(t("log.scheduler_enabled"), schedule_hours)
    try:
        while True:
            start_ts = int(time.time())
            cycle_start = datetime.now()
            
            try:
                result = run_cycle(
                    cfg, logger, qbit, shoko, nyaa, cache, notifier,
                    max_items=max_items, early_exit=early_exit,
                    discord_notifier=discord_notifier, api_server=api_server,
                    language=language
                )
                
                # Update Discord state after cycle
                if api_server:
                    api_server.update_state(
                        last_cycle=cycle_start,
                        next_run=datetime.now() + timedelta(hours=schedule_hours) if schedule_hours > 0 else None,
                        total_added=api_server.state.total_added + result["added"],
                        total_not_found=api_server.state.total_not_found + result["not_found"]
                    )
                
                # Send cycle report to Discord
                if discord_notifier:
                    cycle_duration = time.time() - start_ts
                    discord_notifier.notify_cycle_report(
                        duration=cycle_duration,
                        total_episodes=result["processed"],
                        processed=result["processed"],
                        added=result["added"],
                        not_found=result["not_found"],
                        details=result["details"]
                    )
                    
            except Exception as e:
                logger.exception(t("log.cycle_error"), e)
                notifier.notify_error(t("notify.cycle_error_title"), str(e))
                if discord_notifier:
                    discord_notifier.notify_error(t("notify.cycle_error_title"), str(e))
                    
            if schedule_hours <= 0:
                # If Discord is enabled, keep running to serve Discord commands
                if discord_enabled:
                    logger.info("Initial cycle complete. Discord bot remains active for manual commands.")
                    # Sleep indefinitely, waking periodically to check for shutdown
                    while True:
                        time.sleep(60)  # Wake every minute to allow clean shutdown
                else:
                    break
                
            elapsed = int(time.time()) - start_ts
            sleep_s = max(0, schedule_hours * 3600 - elapsed)
            logger.info(t("log.next_run_in"), sleep_s, sleep_s / 3600)
            time.sleep(sleep_s)
            
    except KeyboardInterrupt:
        logger.info(t("log.shutdown_requested"))
    finally:
        # Cleanup Discord integration
        if discord_notifier:
            discord_notifier.notify_shutdown()
        if api_server:
            api_server.stop()


if __name__ == "__main__":
    main()
