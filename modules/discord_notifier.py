import logging
from typing import Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class DiscordNotifier:
    """Sends Discord webhook notifications with rich embeds for anime downloads."""
    
    def __init__(self, webhook_url: Optional[str], dry_run: bool = False):
        self.webhook_url = webhook_url
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
        self.enabled = bool(webhook_url and webhook_url.strip())
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=False,
           retry=retry_if_exception_type((httpx.HTTPError,)))
    def _send_webhook(self, payload: Dict) -> None:
        """Send Discord webhook with retry logic."""
        if not self.enabled:
            return
        
        with httpx.Client(timeout=10) as client:
            response = client.post(self.webhook_url, json=payload)
            response.raise_for_status()
    
    def notify_download(
        self,
        series_title: str,
        season: int,
        episode: int,
        release_title: str,
        episode_details: Optional[Dict] = None
    ) -> None:
        """Send Discord notification for successful episode download.
        
        Args:
            series_title: Anime series name
            season: Season number
            episode: Episode number
            release_title: Full release title from torrent
            episode_details: Episode metadata from Shoko API (optional)
        """
        if not self.enabled:
            self.logger.debug("Discord notifications disabled (no webhook URL)")
            return
        
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would send Discord notification: {series_title} S{season:02d}E{episode:02d}")
            return
        
        # Build embed
        embed = {
            "title": f"📥 {series_title}",
            "description": f"**Season {season} • Episode {episode}**",
            "color": 3447003,  # Blue color
            "fields": [
                {
                    "name": "Release",
                    "value": release_title[:1024],  # Discord field value limit
                    "inline": False
                }
            ],
            "footer": {
                "text": "ShokoAutoTorrent"
            }
        }
        
        # Add episode metadata if available
        if episode_details:
            # Try to get synopsis from AniDB or TmDB
            synopsis = None
            anidb = episode_details.get("AniDB", {})
            tmdb = episode_details.get("TmDB", {})
            
            if anidb and anidb.get("Description"):
                synopsis = anidb["Description"]
            elif tmdb and isinstance(tmdb, list) and len(tmdb) > 0:
                # TmDB can return array of episodes
                synopsis = tmdb[0].get("Overview")
            
            if synopsis:
                # Truncate synopsis if too long (embed description limit is 4096)
                if len(synopsis) > 300:
                    synopsis = synopsis[:297] + "..."
                embed["fields"].insert(0, {
                    "name": "Synopsis",
                    "value": synopsis,
                    "inline": False
                })
            
            # Try to get episode title
            episode_title = None
            if anidb and anidb.get("Titles"):
                # Get English or romaji title
                for title_obj in anidb["Titles"]:
                    if title_obj.get("Language") in ["en", "x-jat"]:
                        episode_title = title_obj.get("Name")
                        break
            elif tmdb and isinstance(tmdb, list) and len(tmdb) > 0:
                episode_title = tmdb[0].get("Title")
            
            if episode_title:
                embed["fields"].insert(0, {
                    "name": "Episode Title",
                    "value": episode_title[:256],
                    "inline": False
                })
            
            # Try to get poster/thumbnail image
            poster_url = None
            
            # Try TmDB first (usually better quality)
            if tmdb and isinstance(tmdb, list) and len(tmdb) > 0:
                tmdb_ep = tmdb[0]
                if tmdb_ep.get("Thumbnail"):
                    poster_url = tmdb_ep["Thumbnail"]
            
            # Fallback to AniDB
            if not poster_url and anidb:
                poster_url = anidb.get("Thumbnail")
            
            # Set image in embed
            if poster_url:
                embed["thumbnail"] = {"url": poster_url}
        
        payload = {
            "embeds": [embed]
        }
        
        try:
            self._send_webhook(payload)
            self.logger.info(f"Discord notification sent: {series_title} S{season:02d}E{episode:02d}")
        except Exception as e:
            self.logger.error(f"Failed to send Discord notification: {e}")
