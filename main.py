#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path

import yaml

from modules.shoko_client import ShokoClient
from modules.nyaa_search import NyaaSearcher
from modules.qbit_client import QbitClient
from modules.parser import build_queries_for_episode, infer_season_from_title
from modules.cache import Cache
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


def run_cycle(cfg: dict, logger: logging.Logger, qbit: QbitClient, shoko: ShokoClient, nyaa: NyaaSearcher, cache: Cache, notifier: Notifier, max_items: int):
    try:
        qbit.ensure_connected()
    except Exception as e:
        if not qbit.dry_run:
            logger.error(t("log.qbit_connect_fail"), e)
            return
        else:
            logger.warning(t("log.qbit_not_connected_dryrun"), e)

    logger.info(t("log.fetching_missing"))
    episodes = shoko.get_missing_episodes(
        page_size=int(cfg["shoko"].get("page_size", 100)),
        include_data_from=cfg["shoko"].get("include_data_from", ["AniDB"]),
        collecting_only=bool(cfg["shoko"].get("collecting_only", False)),
        include_xrefs=True,
    )

    logger.info(t("log.missing_found_count"), len(episodes))

    processed = 0
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

        results = nyaa.search_tsundere(queries)
        if not results:
            logger.info(t("log.no_results"), queries[0])
            processed += 1
            continue

        # Prendre le meilleur résultat selon préférences
        best = results[0]
        magnet = best.get("magnet") or best.get("link")
        title = best.get("title")
        parsed = best.get("parsed") or {}

        if not magnet:
            logger.debug(t("log.no_link_for_title"), title)
            processed += 1
            continue

        category = f"{cfg['qbittorrent'].get('category_prefix','anime')}/{safe_name(series_title)}"
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
        tags = ",".join(cfg["qbittorrent"].get("tags", []))

        if cache.is_episode_downloaded(shoko_ep_id):
            logger.info(t("log.already_downloaded_cache"), title)
            processed += 1
            continue

        logger.info(t("log.adding_qbit"), title)
        try:
            qbit.add_magnet(magnet, save_path=save_path, category=category, tags=tags)
            cache.mark_episode_downloaded(shoko_ep_id, shoko_series_id, magnet, title)
        except Exception as e:
            logger.error(t("log.qbit_add_fail"), e)
            notifier.notify_error(t("notify.qbit_add_fail_title", title=title), str(e))

        processed += 1
        time.sleep(nyaa.rate_limit_seconds)

    logger.info(t("log.processing_done_count"), processed)


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
    )

    logger.info(t("log.scheduler_enabled"), schedule_hours)
    try:
        while True:
            start_ts = int(time.time())
            try:
                run_cycle(cfg, logger, qbit, shoko, nyaa, cache, notifier, max_items=max_items)
            except Exception as e:
                logger.exception(t("log.cycle_error"), e)
                notifier.notify_error(t("notify.cycle_error_title"), str(e))
            if schedule_hours <= 0:
                break
            elapsed = int(time.time()) - start_ts
            sleep_s = max(0, schedule_hours * 3600 - elapsed)
            logger.info(t("log.next_run_in"), sleep_s, sleep_s / 3600)
            time.sleep(sleep_s)
    except KeyboardInterrupt:
        logger.info(t("log.shutdown_requested"))


if __name__ == "__main__":
    main()
