import yaml
from pathlib import Path
from functools import lru_cache
from typing import Any, Dict


class I18n:
    def __init__(self, language: str = "fr", locales_dir: Path | None = None):
        self.language = (language or "fr").lower()
        self.locales_dir = locales_dir or Path(__file__).resolve().parent.parent / "locales"
        self._messages = self._load_locale(self.language)

    @lru_cache(maxsize=8)
    def _load_locale(self, lang: str) -> Dict[str, Any]:
        path = (self.locales_dir / f"{lang}.yaml").resolve()
        if not path.exists():
            # Fallback to English if requested locale missing
            fallback = (self.locales_dir / "en.yaml").resolve()
            if fallback.exists():
                with fallback.open("r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            return {}
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def t(self, key: str, **kwargs) -> str:
        text = self._messages
        for part in key.split('.'):
            if isinstance(text, dict) and part in text:
                text = text[part]
            else:
                text = None
                break
        if not isinstance(text, str):
            # Key missing -> return key itself
            text = key
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text


# Singleton-style helper for convenience in modules
_i18n: I18n | None = None


def set_locale(language: str):
    global _i18n
    _i18n = I18n(language=language)


def t(key: str, **kwargs) -> str:
    global _i18n
    if _i18n is None:
        _i18n = I18n(language="fr")
    return _i18n.t(key, **kwargs)