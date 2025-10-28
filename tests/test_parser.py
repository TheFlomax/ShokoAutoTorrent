import pytest

from modules.parser import parse_release_title, build_queries_for_episode


def test_parse_release_title_main_pattern():
    title = "My Hero Academia S07E11 VOSTFR 1080p WEB x264 AAC -Tsundere-Raws (CR)"
    p = parse_release_title(title)
    assert p is not None
    assert p['season'] == 7
    assert p['episode'] == 11
    assert p['language'].upper() == 'VOSTFR'
    assert p['quality'] == '1080p'
    assert p['provider'].upper() == 'CR'


def test_parse_release_title_fallback():
    title = "Some Show E03 720p -Tsundere-Raws"
    p = parse_release_title(title)
    assert p is not None
    assert p['season'] is None
    assert p['episode'] == 3


def test_build_queries_for_episode():
    q = build_queries_for_episode("My Show", 2, 5)
    assert q[0] == "My Show S02E05"
    assert any("VOSTFR" in s for s in q)


def test_parse_arcedo_v2():
    title = "[Team Arcedo] NUKITASHI THE ANIMATION S01E02v2 VOSTFR WEB 1080p H264 AAC"
    p = parse_release_title(title)
    assert p is not None
    assert p['group'] == 'Team Arcedo'
    assert p['season'] == 1
    assert p['episode'] == 2
    assert p['version'] == 2
    assert p['quality'] == '1080p'
    assert (p['language'] or '').upper() == 'VOSTFR'
