import asyncio
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
            from utils.i18n import t
            self.logger.debug(t("log.scrape_magnet_failed"), e)
            return None

    async def _fetch_rss_async(self, base_url: str, query: Optional[str] = None) -> Optional[feedparser.FeedParserDict]:
        """Async wrapper for RSS fetching."""
        url = base_url
        if query:
            url += f"&q={httpx.QueryParams({'q': query})['q']}"
        
        self.logger.debug(f"Fetching RSS: {url}")
        
        cached = self.cache.get_search_cache(url) if self.cache else None
        if cached:
            self.logger.debug(f"Cache hit for: {url}")
            return feedparser.parse(cached)
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text
                if self.cache:
                    self.cache.set_search_cache(url, text)
                return feedparser.parse(text)
        except Exception as e:
            from utils.i18n import t
            self.logger.warning(t("log.rss_fetch_failed"), query, base_url, e)
            return None

    async def _search_query_async(self, query: str) -> List[Dict]:
        """Search a single query across all RSS feeds in parallel."""
        tasks = [self._fetch_rss_async(base_url, query) for base_url in self.rss_urls]
        feeds = await asyncio.gather(*tasks, return_exceptions=False)
        
        results: List[Dict] = []
        seen = set()
        
        for feed in feeds:
            if not feed:
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
        return results

    def search_tsundere(self, queries: List[str], early_exit: bool = True) -> List[Dict]:
        """
        Search for torrents using multiple queries.
        If early_exit=True, stops at first query that returns results.
        """
        self.logger.info(f"Early exit: {'enabled' if early_exit else 'disabled'}")
        results: List[Dict] = []
        seen = set()
        
        for i, q in enumerate(queries):
            if i > 0:
                time.sleep(self.rate_limit_seconds)
            
            self.logger.info(f"Trying query [{i+1}/{len(queries)}]: '{q}'")
            
            # Run async search for this query across all RSS feeds in parallel
            query_results = asyncio.run(self._search_query_async(q))
            
            # Deduplicate and add to overall results
            for r in query_results:
                key = (r['title'], r['magnet'])
                if key not in seen:
                    seen.add(key)
                    results.append(r)
            
            # Early exit: if we found results, stop searching
            if early_exit and results:
                self.logger.debug(f"Early exit: found {len(results)} result(s) with query '{q}'")
                break
        
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
