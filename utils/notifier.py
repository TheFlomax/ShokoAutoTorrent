import json
import logging
from typing import Optional

import httpx


class Notifier:
    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self.logger = logging.getLogger(__name__)

    def notify_error(self, title: str, details: str):
        url = self.cfg.get('discord_webhook_url')
        if not url:
            return
        try:
            httpx.post(url, json={
                'content': f"❗ {title}\n```\n{details}\n```"
            }, timeout=15)
        except Exception as e:
            from utils.i18n import t
            self.logger.debug(t("log.discord_notify_failed"), e)
