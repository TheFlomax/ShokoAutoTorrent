# MULTI Language Support Fix

## Issue

The parser was unable to find episodes when they were released with `MULTi` language tag (e.g., releases containing VF, FRENCH, and VOSTFR audio tracks).

### Example Case

**Anime**: Disney Twisted-Wonderland The Animation S01E01

**Available on Nyaa**: 
```
Disney Twisted-Wonderland The Animation S01E01 MULTi 1080p WEB H.264 AAC -Tsundere-Raws (DSNP) (VF, FRENCH, VOSTFR, Disney Twisted-Wonderland The Animation: Episode of Heartslabyul)
```

**Problem**: When searching with preferred language `VOSTFR`, the release was being filtered out because:
- Parser correctly identified `language='MULTi'`
- Filter checked: `if 'vostfr' in 'multi'` → FALSE
- Result was **skipped** even though MULTI releases contain VOSTFR audio

## Root Cause

In `modules/nyaa_search.py` line 113:

```python
# OLD CODE - This rejected MULTI releases
if pref_lang and parsed.get('language') and pref_lang.lower() not in parsed['language'].lower():
    continue
```

This logic rejected any release where the preferred language string wasn't literally found in the release's language tag. Since "vostfr" is not a substring of "multi", MULTI releases were always rejected.

## Solution

### 1. Language Filter Fix (`modules/nyaa_search.py`)

Updated the filter to explicitly allow MULTI releases:

```python
# NEW CODE - Accepts MULTI releases for any language preference
parsed_lang = parsed.get('language')
# MULTI releases contain all languages, so always accept them
if pref_lang and parsed_lang and parsed_lang.upper() != 'MULTI' and pref_lang.lower() not in parsed_lang.lower():
    continue
```

**Logic**: If a release is tagged as `MULTI`, it means it contains multiple language tracks (including the preferred one), so we should NOT filter it out.

### 2. Scoring Enhancement (`modules/parser.py`)

Updated `score_release()` to give MULTI releases appropriate scores:

```python
# Language scoring
if pref_lang:
    if pref_lang in lang:
        score += 50  # Exact match (e.g., VOSTFR when preferring VOSTFR)
    # MULTI releases contain all languages, give them a good score too
    elif lang == 'MULTI':
        score += 40  # Slightly less than exact match, but still high
```

**Scoring Priority**:
1. Exact language match (VOSTFR): +50 points
2. MULTI release: +40 points
3. No language match: +0 points

This ensures that if both a VOSTFR-only release and a MULTI release are available, the VOSTFR-only release is preferred, but MULTI releases are still highly scored and will be selected if no exact match exists.

## Testing

Added two test cases in `tests/test_parser.py`:

### 1. `test_parse_multi_language_release()`
Verifies that MULTI releases are parsed correctly:
```python
title = "Disney Twisted-Wonderland The Animation S01E01 MULTi 1080p WEB H.264 AAC -Tsundere-Raws (DSNP)"
p = parse_release_title(title)
assert p['language'].upper() == 'MULTI'
```

### 2. `test_multi_language_scoring()`
Verifies scoring priorities:
```python
# With VOSTFR preference:
# VOSTFR release: 70 points (50 language + 20 quality)
# MULTI release:  60 points (40 language + 20 quality)
# VF release:     20 points (0 language + 20 quality)
assert score_vostfr > score_multi > score_vf
```

## Impact

- ✅ MULTI releases are now properly found and downloaded
- ✅ Exact language matches are still preferred over MULTI
- ✅ MULTI releases are scored higher than non-matching languages
- ✅ No breaking changes to existing functionality
- ✅ Works with all language preferences (VOSTFR, VF, ENG, etc.)

## Example Behavior

**Before Fix**:
```
Searching: Disney Twisted-Wonderland The Animation S01E01
Query 1/6: 'Disney Twisted-Wonderland The Animation S01E01'
  → Found: Disney... S01E01 MULTi 1080p... → language='MULTi'
  → Filter: 'vostfr' not in 'multi' → REJECTED ❌
Result: No results found
```

**After Fix**:
```
Searching: Disney Twisted-Wonderland The Animation S01E01
Query 1/6: 'Disney Twisted-Wonderland The Animation S01E01'
  → Found: Disney... S01E01 MULTi 1080p... → language='MULTi'
  → Filter: language is 'MULTI' → ACCEPTED ✅
  → Score: 60 points (40 language + 20 quality)
Result: Added to qBittorrent
```

## Related Files Modified

- `modules/nyaa_search.py` - Line 113-115: Language filter logic
- `modules/parser.py` - Line 156-161: Scoring logic for MULTI
- `tests/test_parser.py` - Added 2 test cases for MULTI support
