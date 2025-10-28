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
from modules.parser import build_queries_for_episode
from modules.cache import Cache
from utils.logger import setup_logging
from utils.notifier import Notifier
from utils.pathing import render_path_template, safe_name


def expand_env_vars(obj):
    if isinstance(obj, dict):
        return {k: expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env_vars(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        return os.environ.get(obj[2:-1], "")
    return obj


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return expand_env_vars(cfg)


def ensure_cache_db(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Shoko Auto Torrent - Tsundere-Raws")
    parser.add_argument("--config", default="config.yaml", help="Chemin du fichier de configuration")
    parser.add_argument("--limit", type=int, default=None, help="Nombre maximum d'épisodes à traiter")
    parser.add_argument("--dry-run", action="store_true", help="Ne pas envoyer à qBittorrent")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    log_level = getattr(logging, str(cfg.get("general", {}).get("log_level", "INFO")).upper(), logging.INFO)
    setup_logging(level=log_level)
    logger = logging.getLogger("main")

    dry_run = args.dry_run or bool(cfg.get("general", {}).get("dry_run", False))
    max_items = args.limit or int(cfg.get("general", {}).get("max_items", 10))

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

    try:
        qbit.ensure_connected()
    except Exception as e:
        if not dry_run:
            logger.error("Connexion qBittorrent échouée: %s", e)
            sys.exit(1)
        else:
            logger.warning("qBittorrent non connecté (dry-run): %s", e)

    logger.info("Récupération des épisodes manquants depuis Shoko…")
    episodes = shoko.get_missing_episodes(
        page_size=int(cfg["shoko"].get("page_size", 100)),
        include_data_from=cfg["shoko"].get("include_data_from", ["AniDB"]),
        collecting_only=bool(cfg["shoko"].get("collecting_only", False)),
        include_xrefs=True,
    )

    logger.info("%d épisodes manquants trouvés", len(episodes))

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
            logger.debug("Infos insuffisantes (title:%s, ep:%s) pour l'entrée: %s", series_title, ep_num, shoko_ep_id)
            continue

        queries = build_queries_for_episode(series_title, season, ep_num)

        logger.info("Recherche: %s S%sE%02d (id:%s)", series_title, f"{int(season):02d}" if season else "??", int(ep_num), shoko_ep_id)

        results = nyaa.search_tsundere(queries)
        if not results:
            logger.info("Aucun résultat pertinent trouvé pour %s", queries[0])
            processed += 1
            continue

        # Prendre le meilleur résultat selon préférences
        best = results[0]
        magnet = best.get("magnet") or best.get("link")
        title = best.get("title")
        parsed = best.get("parsed") or {}

        if not magnet:
            logger.debug("Pas de lien pour %s", title)
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
            logger.info("Déjà téléchargé (cache): %s", title)
            processed += 1
            continue

        logger.info("Ajout qBittorrent: %s", title)
        try:
            qbit.add_magnet(magnet, save_path=save_path, category=category, tags=tags)
            cache.mark_episode_downloaded(shoko_ep_id, shoko_series_id, magnet, title)
        except Exception as e:
            logger.error("Échec d'ajout dans qBittorrent: %s", e)
            notifier.notify_error(f"Échec ajout qBittorrent: {title}", str(e))

        processed += 1
        time.sleep(nyaa.rate_limit_seconds)

    logger.info("Traitement terminé. %d épisodes traités.", processed)


if __name__ == "__main__":
    main()
