import pytest

from modules.parser import parse_release_title, build_queries_for_episode, sanitize_title_for_nyaa, score_release


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


def test_sanitize_preserves_hyphens_in_words():
    # Hyphens within words should be preserved (Twisted-Wonderland)
    assert sanitize_title_for_nyaa("Disney Twisted-Wonderland: The Animation") == "Disney Twisted-Wonderland The Animation"
    # Hyphens as separators should be removed
    assert sanitize_title_for_nyaa("My Show - Part 2") == "My Show Part 2"
    # Multiple punctuation
    assert sanitize_title_for_nyaa("Show's Title: Part 2!") == "Shows Title Part 2"


def test_build_queries_for_hyphenated_title():
    # Test that hyphenated titles generate correct queries
    q = build_queries_for_episode("Disney Twisted-Wonderland: The Animation", 1, 2)
    # First query should preserve the hyphen
    assert "Twisted-Wonderland" in q[0]
    assert q[0] == "Disney Twisted-Wonderland The Animation S01E02"


def test_parse_multi_language_release():
    """Test that MULTI language releases are parsed correctly."""
    title = "Disney Twisted-Wonderland The Animation S01E01 MULTi 1080p WEB H.264 AAC -Tsundere-Raws (DSNP)"
    p = parse_release_title(title)
    assert p is not None
    assert p['title'] == 'Disney Twisted-Wonderland The Animation'
    assert p['season'] == 1
    assert p['episode'] == 1
    assert p['language'].upper() == 'MULTI'
    assert p['quality'] == '1080p'
    assert p['source'] == 'WEB'
    assert p['provider'] == 'DSNP'


def test_multi_language_scoring():
    """Test that MULTI releases get appropriate scores with language preferences."""
    parsed_multi = {'language': 'MULTi', 'quality': '1080p'}
    parsed_vostfr = {'language': 'VOSTFR', 'quality': '1080p'}
    parsed_vf = {'language': 'VF', 'quality': '1080p'}
    
    preferred = {'language': 'VOSTFR', 'qualities': ['1080p', '720p']}
    
    # VOSTFR should score highest (50 for exact match + 20 for quality)
    score_vostfr = score_release(parsed_vostfr, preferred)
    # MULTI should score well but slightly less (40 for MULTI + 20 for quality)
    score_multi = score_release(parsed_multi, preferred)
    # VF should score lowest (only 20 for quality, no language match)
    score_vf = score_release(parsed_vf, preferred)
    
    assert score_vostfr == 70  # 50 + 20
    assert score_multi == 60   # 40 + 20
    assert score_vf == 20      # 0 + 20
    assert score_vostfr > score_multi > score_vf
