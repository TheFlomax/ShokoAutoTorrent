import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional


class Cache:
    def __init__(self, db_path: Path, ttl_hours: int = 24):
        self.db_path = Path(db_path)
        self.ttl_seconds = ttl_hours * 3600
        self._init_db()
        self.logger = logging.getLogger(__name__)

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  ts INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                  episode_id INTEGER PRIMARY KEY,
                  series_id INTEGER,
                  magnet TEXT,
                  title TEXT,
                  ts INTEGER NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def get_search_cache(self, key: str) -> Optional[str]:
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT value, ts FROM search_cache WHERE key=?", (key,))
            row = cur.fetchone()
            if not row:
                return None
            value, ts = row
            if now - ts > self.ttl_seconds:
                return None
            return value
        finally:
            conn.close()

    def set_search_cache(self, key: str, value: str):
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "REPLACE INTO search_cache(key, value, ts) VALUES(?,?,?)",
                (key, value, now),
            )
            conn.commit()
        finally:
            conn.close()

    def is_episode_downloaded(self, episode_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM downloads WHERE episode_id=?", (episode_id,))
            return cur.fetchone() is not None
        finally:
            conn.close()

    def mark_episode_downloaded(self, episode_id: int, series_id: int, magnet: str, title: str):
        now = int(time.time())
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "REPLACE INTO downloads(episode_id, series_id, magnet, title, ts) VALUES(?,?,?,?,?)",
                (episode_id, series_id, magnet, title, now),
            )
            conn.commit()
        finally:
            conn.close()
