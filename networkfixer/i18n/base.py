import logging
from typing import Dict

logger = logging.getLogger(__name__)

_translations: Dict[str, Dict[str, str]] = {}


def register_translations(lang: str, translations: Dict[str, str]) -> None:
    _translations[lang] = translations
    logger.debug(f"Registered translations for {lang}")


def t(key: str, lang: str = "zh_CN", **kwargs) -> str:
    lang_dict = _translations.get(lang, {})
    text = lang_dict.get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            pass

    return text


def get_available_languages() -> list:
    return list(_translations.keys())


def detect_system_language() -> str:
    import locale

    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            lang = lang.replace("-", "_")
            if lang in _translations:
                return lang
            main_lang = lang.split("_")[0]
            for available in _translations:
                if available.startswith(main_lang):
                    return available
    except Exception:
        pass

    return "zh_CN"
