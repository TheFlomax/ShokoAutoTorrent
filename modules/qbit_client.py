import logging
from typing import Optional

import qbittorrentapi


class QbitClient:
    def __init__(self, url: str, username: str, password: str, dry_run: bool = False):
        self.url = url
        self.username = username
        self.password = password
        self.dry_run = dry_run
        self.client = qbittorrentapi.Client(host=self.url, username=self.username, password=self.password)
        self.logger = logging.getLogger(__name__)

    def ensure_connected(self):
        try:
            self.client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            raise RuntimeError(f"qBittorrent login failed: {e}")

    def add_magnet(self, magnet_or_url: str, save_path: Optional[str] = None, category: Optional[str] = None, tags: Optional[str] = None):
        if self.dry_run:
            self.logger.info("[DRY-RUN] Ajouter: %s", (magnet_or_url or '')[:60] + '...')
            return
        kwargs = {}
        if save_path:
            kwargs['savepath'] = save_path
        if category:
            kwargs['category'] = category
        if tags:
            kwargs['tags'] = tags
        self.client.torrents_add(urls=magnet_or_url, **kwargs)
