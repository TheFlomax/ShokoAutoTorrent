import logging
import re
from typing import Dict, List, Optional

RE_MAIN = re.compile(
    r"^(?:\[(?P<group>[^\]]+)\]\s*)?"  # optional [Group]
    r"(?P<title>.+?)\s+S(?P<season>\d{2})E(?P<episode>\d{2,3})(?:v(?P<version>\d+))?\s*"
    r"(?P<lang>VOSTFR|VF|ENG|MULTI)?\s*"
    r"(?P<quality>2160p|1080p|720p|480p)?\s*"
    r"(?P<source>WEB|WEB-DL|WEB\s?DL|BD|BluRay|DVD)?"
    r".*?(?:-\s*(?P<tsundere>Tsundere-Raws))?"  # optional -Tsundere-Raws
    r"(?:\s*\((?P<provider>[^)]+)\))?",
    re.IGNORECASE,
)

RE_FALLBACK_E = re.compile(
    r"^(?:\[(?P<group>[^\]]+)\]\s*)?"  # optional [Group]
    r"(?P<title>.+?)\s+E(?P<episode>\d{2,3})(?:v(?P<version>\d+))?\s*"
    r"(?P<lang>VOSTFR|VF|ENG|MULTI)?\s*"
    r"(?P<quality>2160p|1080p|720p|480p)?",
    re.IGNORECASE,
)


def parse_release_title(title: str) -> Optional[Dict]:
    m = RE_MAIN.search(title)
    if m:
        d = m.groupdict()
        # Post-detect quality/source anywhere in title to handle varying order
        qmatch = re.search(r"\b(2160p|1080p|720p|480p)\b", title, re.IGNORECASE)
        smatch = re.search(r"\b(WEB(?:-?DL)?|BD|BluRay|DVD)\b", title, re.IGNORECASE)
        # Provider often appears as trailing parentheses like (CR)
        pmatch = re.search(r"\(([^)]+)\)\s*$", title)
        return {
            'group': d.get('group'),
            'title': d.get('title'),
            'season': int(d['season']) if d.get('season') else None,
            'episode': int(d['episode']) if d.get('episode') else None,
            'version': int(d['version']) if d.get('version') else None,
            'language': d.get('lang'),
            'quality': (qmatch.group(1) if qmatch else d.get('quality')),
            'source': (smatch.group(1).replace('WEBDL', 'WEB-DL') if smatch else d.get('source')),
            'provider': (pmatch.group(1) if pmatch else d.get('provider')),
        }
    m2 = RE_FALLBACK_E.search(title)
    if m2:
        d = m2.groupdict()
        return {
            'group': d.get('group'),
            'title': d.get('title'),
            'season': None,
            'episode': int(d['episode']) if d.get('episode') else None,
            'version': int(d.get('version')) if d.get('version') else None,
            'language': d.get('lang'),
            'quality': d.get('quality'),
            'source': None,
            'provider': None,
        }
    return None


def build_queries_for_episode(series_title: str, season: Optional[int], episode: int) -> List[str]:
    q = []
    if season:
        q.append(f"{series_title} S{int(season):02d}E{int(episode):02d}")
    q.append(f"{series_title} E{int(episode):02d}")
    # prefer FR
    q.append((q[0] if q else f"{series_title} E{int(episode):02d}") + " VOSTFR")
    return list(dict.fromkeys(q))


def score_release(parsed: Dict, preferred: Optional[Dict]) -> int:
    if not preferred:
        preferred = {}
    score = 0
    # Language
    lang = (parsed.get('language') or '').upper()
    pref_lang = (preferred.get('language') or '').upper()
    if pref_lang and pref_lang in lang:
        score += 50
    # Quality
    qualities = preferred.get('qualities') or []
    if parsed.get('quality') in qualities:
        # Higher index = lower preference, so invert weight
        score += (len(qualities) - qualities.index(parsed['quality'])) * 10
    # Version bonus (v3>v2>v1)
    version = parsed.get('version') or 1
    score += max(0, version - 1) * 3
    # Provider/source tag like (CR|ADN|AMZN)
    providers = preferred.get('sources') or []
    prov = (parsed.get('provider') or '').upper()
    for i, p in enumerate(providers):
        if p.upper() in prov:
            score += (len(providers) - i) * 5
            break
    return score
