import logging
import time
from typing import Dict, List, Optional, Sequence

import feedparser
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from modules.parser import parse_release_title, score_release


class NyaaSearcher:
    def __init__(self, users: Sequence[str], rss_urls: Optional[Sequence[str]], preferred: Dict, rate_limit_seconds: int = 3, cache=None):
        self.users = list(users or [])
        self.rss_urls = list(rss_urls or [])
        # Generate rss urls from users if not provided
        if not self.rss_urls:
            self.rss_urls = [f"https://nyaa.si/?page=rss&u={u}" for u in self.users]
        self.preferred = preferred or {}
        self.rate_limit_seconds = rate_limit_seconds
        self.cache = cache
        self.logger = logging.getLogger(__name__)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True,
           retry=retry_if_exception_type((httpx.HTTPError,)))
    def _http_get_text(self, url: str) -> str:
        resp = httpx.get(url, timeout=20)
        resp.raise_for_status()
        return resp.text

    def _fetch_rss(self, base_url: str, query: Optional[str] = None) -> feedparser.FeedParserDict:
        url = base_url
        if query:
            url += f"&q={httpx.QueryParams({'q': query})['q']}"
        cached = self.cache.get_search_cache(url) if self.cache else None
        if cached:
            return feedparser.parse(cached)
        text = self._http_get_text(url)
        if self.cache:
            self.cache.set_search_cache(url, text)
        return feedparser.parse(text)

    def _extract_magnet(self, entry: feedparser.FeedParserDict) -> Optional[str]:
        # Try feedparser magnet field
        magnet = entry.get('torrent_magneturi') or entry.get('magnet')
        if magnet:
            return magnet
        # Fallback parse links
        links = entry.get('links', [])
        for l in links:
            href = l.get('href', '')
            if href.startswith('magnet:?'):
                return href
        # Last resort: fetch page and scrape magnet link
        page_url = entry.get('link')
        if not page_url:
            return None
        try:
            text = self._http_get_text(page_url)
            soup = BeautifulSoup(text, 'lxml')
            a = soup.select_one('a[href^="magnet:"]')
            return a['href'] if a else None
        except Exception as e:
            self.logger.debug("Scrape magnet failed: %s", e)
            return None

    def search_tsundere(self, queries: List[str]) -> List[Dict]:
        results: List[Dict] = []
        seen = set()
        for q in queries:
            for base_url in self.rss_urls:
                time.sleep(self.rate_limit_seconds)
                try:
                    feed = self._fetch_rss(base_url, q)
                except Exception as e:
                    self.logger.warning("RSS fetch failed for '%s' on %s: %s", q, base_url, e)
                    continue
                for entry in feed.entries:
                    title = entry.get('title', '')
                    parsed = parse_release_title(title)
                    if not parsed:
                        continue
                    # Basic language/source filter
                    pref_lang = (self.preferred or {}).get('language')
                    if pref_lang and parsed.get('language') and pref_lang.lower() not in parsed['language'].lower():
                        continue
                    # Score
                    sc = score_release(parsed, self.preferred)
                    magnet = self._extract_magnet(entry)
                    key = (title, magnet)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        'title': title,
                        'magnet': magnet,
                        'score': sc,
                        'parsed': parsed,
                        'link': entry.get('link')
                    })
        # Prefer higher score, then version desc, then quality desc, then title
        def sort_key(x):
            parsed = x['parsed']
            version = parsed.get('version') or 1
            qual_rank = 0
            q = (parsed.get('quality') or '').lower()
            if q == '2160p':
                qual_rank = 2
            elif q == '1080p':
                qual_rank = 1
            else:
                qual_rank = 0
            return (x['score'], version, qual_rank, x['title'])
        results.sort(key=sort_key, reverse=True)
        return results
