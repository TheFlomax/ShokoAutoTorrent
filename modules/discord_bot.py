#!/usr/bin/env python3
"""
Discord bot integration module.
Provides internal API server and notification system for Discord bot communication.
"""

import json
import logging
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from utils.i18n import t

logger = logging.getLogger("discord_bot")


class AppState:
    """Thread-safe shared state between main application and Discord bot."""

    def __init__(self):
        self.running = False
        self.last_cycle: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.total_added = 0
        self.total_not_found = 0
        self.current_episode: Optional[Dict[str, Any]] = None
        self.missing_episodes: List[Dict[str, Any]] = []
        self.search_callback: Optional[Callable[[int], Dict[str, Any]]] = None
        self._lock = threading.Lock()

    def update(self, **kwargs):
        """Thread-safe state update."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)

    def get_status(self) -> Dict[str, Any]:
        """Get current status as dict."""
        with self._lock:
            return {
                "running": self.running,
                "last_cycle": self.last_cycle.isoformat() if self.last_cycle else None,
                "next_run": self.next_run.isoformat() if self.next_run else None,
                "total_added": self.total_added,
                "total_not_found": self.total_not_found,
                "current_episode": self.current_episode,
            }

    def get_missing(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of missing episodes."""
        with self._lock:
            return self.missing_episodes[:limit]


class APIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for internal API."""

    state: AppState = None  # Will be set by server

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/status":
            self._handle_status()
        elif path == "/missing":
            self._handle_missing(parsed.query)
        elif path == "/health":
            self._send_json({"status": "ok"}, 200)
        else:
            self._send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/search":
            self._handle_search()
        else:
            self._send_error(404, "Not Found")

    def _handle_status(self):
        """Return current application status."""
        status = self.state.get_status()
        self._send_json(status, 200)

    def _handle_missing(self, query_string: str):
        """Return list of missing episodes."""
        params = parse_qs(query_string)
        limit = int(params.get("limit", [100])[0])

        episodes = self.state.get_missing(limit)
        self._send_json({"episodes": episodes}, 200)

    def _handle_search(self):
        """Trigger manual search."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body) if body else {}

            limit = data.get("limit", 10)

            if not self.state.search_callback:
                self._send_error(503, "Search functionality not available")
                return

            # Execute search in background thread
            def run_search():
                try:
                    result = self.state.search_callback(limit)
                    logger.info("Manual search completed: %s", result)
                except Exception as e:
                    logger.error("Manual search failed: %s", e, exc_info=True)

            search_thread = threading.Thread(target=run_search, daemon=True)
            search_thread.start()

            self._send_json(
                {"status": "started", "message": f"Search started for {limit} episodes"},
                202,
            )

        except Exception as e:
            logger.error("Error handling search request: %s", e)
            self._send_error(500, str(e))

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_error(self, status_code: int, message: str):
        """Send error response."""
        self._send_json({"error": message}, status_code)

    def log_message(self, format, *args):
        """Override to use custom logger."""
        logger.debug(
            "%s - - [%s] %s",
            self.address_string(),
            self.log_date_time_string(),
            format % args,
        )


class InternalAPIServer:
    """Internal API server for Discord bot communication."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.state = AppState()
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start the API server in a background thread."""
        if self.thread and self.thread.is_alive():
            logger.warning("API server already running")
            return

        # Set shared state on handler class
        APIHandler.state = self.state

        self.server = HTTPServer((self.host, self.port), APIHandler)
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

        logger.info("Internal API server started on %s:%d", self.host, self.port)

    def _run_server(self):
        """Run the HTTP server (called in thread)."""
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error("API server error: %s", e, exc_info=True)

    def stop(self):
        """Stop the API server."""
        if self.server:
            self.server.shutdown()
            logger.info("Internal API server stopped")

    def set_search_callback(self, callback: Callable[[int], Dict[str, Any]]):
        """Set callback function for manual search triggering."""
        self.state.search_callback = callback

    def update_state(self, **kwargs):
        """Update application state."""
        self.state.update(**kwargs)


class DiscordNotifier:
    """Send notifications to Discord bot via local socket."""

    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.enabled = True

    def _send_message(self, data: Dict[str, Any]) -> bool:
        """Send message to Discord bot listener."""
        try:
            message = json.dumps(data) + "\n"

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.host, self.port))
                sock.sendall(message.encode("utf-8"))

            return True
        except Exception as e:
            logger.debug(t("log.discord_notify_failed"), e)
            return False

    def notify_cycle_report(
        self,
        duration: float,
        total_episodes: int,
        processed: int,
        added: int,
        not_found: int,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        """Send cycle completion report."""
        if not self.enabled:
            return

        fields = [
            {"name": t("discord.report.duration"), "value": f"{duration:.1f}s", "inline": True},
            {
                "name": t("discord.report.total_episodes"),
                "value": str(total_episodes),
                "inline": True,
            },
            {"name": t("discord.report.processed"), "value": str(processed), "inline": True},
            {"name": t("discord.report.added"), "value": str(added), "inline": True},
            {"name": t("discord.report.not_found"), "value": str(not_found), "inline": True},
        ]

        # Add sample of processed episodes
        if details and len(details) > 0:
            sample = details[:5]
            detail_text = "\n".join(
                [
                    f"• {d['series']} - E{d['episode']:02d}: {d['status']}"
                    for d in sample
                ]
            )
            fields.append(
                {
                    "name": t("discord.report.examples"),
                    "value": detail_text,
                    "inline": False,
                }
            )

        data = {
            "type": "cycle_report",
            "title": t("discord.report.cycle_title"),
            "description": t("discord.report.cycle_desc"),
            "color": 0x2ECC71,  # Green
            "fields": fields,
            "timestamp": datetime.now().isoformat(),
        }

        self._send_message(data)
        logger.info("Sent cycle report to Discord")

    def notify_startup(self, config_summary: Optional[Dict[str, str]] = None):
        """Send application startup notification."""
        if not self.enabled:
            return

        fields = []
        if config_summary:
            for key, value in config_summary.items():
                fields.append({"name": key, "value": str(value), "inline": True})

        data = {
            "type": "startup",
            "title": t("discord.bot.app_startup_title"),
            "description": t("discord.bot.app_startup_desc"),
            "color": 0x2ECC71,  # Green
            "fields": fields,
            "timestamp": datetime.now().isoformat(),
        }

        self._send_message(data)
        logger.info("Sent startup notification to Discord")

    def notify_shutdown(self):
        """Send application shutdown notification."""
        if not self.enabled:
            return

        data = {
            "type": "shutdown",
            "title": t("discord.bot.app_shutdown_title"),
            "description": t("discord.bot.app_shutdown_desc"),
            "color": 0xE74C3C,  # Red
            "timestamp": datetime.now().isoformat(),
        }

        self._send_message(data)
        logger.info("Sent shutdown notification to Discord")

    def notify_error(self, title: str, error_message: str):
        """Send error notification."""
        if not self.enabled:
            return

        data = {
            "type": "error",
            "title": t("discord.report.error_title"),
            "description": f"{title}\n\n{error_message[:2000]}",  # Discord limit
            "color": 0xE74C3C,  # Red
            "timestamp": datetime.now().isoformat(),
        }

        self._send_message(data)
        logger.info("Sent error notification to Discord: %s", title)

    def notify_progress(self, message: str, countdown_seconds: int = 0):
        """Send progress notification during search operations."""
        if not self.enabled:
            return

        data = {
            "type": "progress",
            "title": t("discord.report.progress_title"),
            "description": message,
            "color": 0xF39C12,  # Orange
            "timestamp": datetime.now().isoformat(),
        }
        
        if countdown_seconds > 0:
            data["fields"] = [
                {
                    "name": t("discord.report.countdown"),
                    "value": t("discord.report.countdown_value", seconds=countdown_seconds),
                    "inline": True
                }
            ]

        self._send_message(data)

    def notify_episode_found(self, series: str, episode: int, torrent_name: str):
        """Send notification when an episode is found."""
        if not self.enabled:
            return

        data = {
            "type": "episode_found",
            "title": t("discord.report.episode_found_title"),
            "description": t("discord.report.episode_found_desc", series=series, episode=episode),
            "color": 0x3498DB,  # Blue
            "fields": [{"name": t("discord.report.torrent"), "value": torrent_name, "inline": False}],
            "timestamp": datetime.now().isoformat(),
        }

        self._send_message(data)
