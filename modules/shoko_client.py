import logging
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class ShokoClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/') + '/'
        self.api_key = api_key
        self.client = httpx.Client(base_url=self.base_url, timeout=30, headers={
            'accept': 'application/json',
            'apikey': self.api_key,
        })
        self.logger = logging.getLogger(__name__)
        self._series_cache: dict[int, str] = {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True,
           retry=retry_if_exception_type((httpx.HTTPError,)))
    def _get(self, path: str, params: dict) -> httpx.Response:
        r = self.client.get(path, params=params)
        r.raise_for_status()
        return r

    def get_series_name(self, series_id: int) -> Optional[str]:
        if not series_id:
            return None
        if series_id in self._series_cache:
            return self._series_cache[series_id]
        r = self._get(f'Series/{series_id}', params={})
        data = r.json() or {}
        name = data.get('Name') or data.get('AniDB', {}).get('Title')
        if name:
            self._series_cache[series_id] = name
        return name

    def get_missing_episodes(
        self,
        page_size: int = 200,
        include_data_from: Optional[List[str]] = None,
        collecting_only: bool = False,
        include_xrefs: bool = True,
    ) -> List[Dict]:
        # /ReleaseManagement/MissingEpisodes/Episodes
        params = {
            'pageSize': page_size,
            'page': 1,
            'collecting': str(collecting_only).lower(),
            'includeFiles': 'false',
            'includeMediaInfo': 'false',
            'includeAbsolutePaths': 'false',
            'includeXRefs': str(include_xrefs).lower(),
        }
        if include_data_from:
            # Multiple entries allowed
            for src in include_data_from:
                params.setdefault('includeDataFrom', []).append(src)
        results: List[Dict] = []
        while True:
            r = self._get('ReleaseManagement/MissingEpisodes/Episodes', params=params)
            data = r.json() or {}
            items = data.get('List') or data.get('list') or []
            results.extend(items)
            total = data.get('Total', 0)
            page = data.get('Page', params['page'])
            if not items or len(results) >= total:
                break
            params['page'] = page + 1
        return results
