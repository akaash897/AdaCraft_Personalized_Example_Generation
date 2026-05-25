"""
Language detection utility for AdaCraft.

Detects the language of a given text and returns a (code, name) tuple.
Uses Unicode script ranges as the primary signal (zero-cost, works offline),
with langdetect as a fallback for ambiguous or Latin-script inputs.

Supported languages for Indic scripts: Hindi, Bengali, Tamil, Telugu, Gujarati,
Punjabi, Malayalam, Kannada, Odia.
Latin-script languages (French, Spanish, German, etc.) use langdetect.
"""

from typing import Tuple

# Maps langdetect / ISO 639-1 codes → display names
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "bn": "Bengali",
    "ta": "Tamil",
    "te": "Telugu",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ml": "Malayalam",
    "kn": "Kannada",
    "or": "Odia",
    "mr": "Marathi",
    "ur": "Urdu",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
    "ru": "Russian",
    "ar": "Arabic",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
}

# Unicode block ranges → (lang_code, lang_name)
# Checked in order; first match wins.
_UNICODE_RANGES = [
    (0x0900, 0x097F, "hi", "Hindi"),        # Devanagari
    (0x0980, 0x09FF, "bn", "Bengali"),       # Bengali
    (0x0B80, 0x0BFF, "ta", "Tamil"),         # Tamil
    (0x0C00, 0x0C7F, "te", "Telugu"),        # Telugu
    (0x0A80, 0x0AFF, "gu", "Gujarati"),      # Gujarati
    (0x0A00, 0x0A7F, "pa", "Punjabi"),       # Gurmukhi (Punjabi)
    (0x0D00, 0x0D7F, "ml", "Malayalam"),     # Malayalam
    (0x0C80, 0x0CFF, "kn", "Kannada"),       # Kannada
    (0x0B00, 0x0B7F, "or", "Odia"),          # Odia
    (0x0600, 0x06FF, "ar", "Arabic"),        # Arabic / Urdu
    (0x0400, 0x04FF, "ru", "Russian"),       # Cyrillic
    (0x4E00, 0x9FFF, "zh-cn", "Chinese (Simplified)"),  # CJK Unified
    (0x3040, 0x309F, "ja", "Japanese"),      # Hiragana
    (0x30A0, 0x30FF, "ja", "Japanese"),      # Katakana
    (0xAC00, 0xD7AF, "ko", "Korean"),        # Hangul
    (0x0E00, 0x0E7F, "th", "Thai"),          # Thai
]


def _detect_by_unicode(text: str) -> Tuple[str, str]:
    """
    Count characters per Unicode block and return the dominant non-Latin script.
    Returns ("en", "English") if the text is predominantly ASCII/Latin.

    Note: Devanagari (0x0900–0x097F) and Bengali (0x0980–0x09FF) are adjacent
    blocks; some fonts/encodings cause cross-block leakage. We resolve ambiguity
    by comparing raw character counts for both blocks and picking the winner.
    """
    block_counts: dict = {}
    for ch in text:
        cp = ord(ch)
        for start, end, code, name in _UNICODE_RANGES:
            if start <= cp <= end:
                key = (code, name)
                block_counts[key] = block_counts.get(key, 0) + 1
                break

    if not block_counts:
        return "en", "English"

    # Devanagari/Bengali disambiguation: if both are present, keep only the
    # dominant one so max() below picks the correct language.
    hi_key = ("hi", "Hindi")
    bn_key = ("bn", "Bengali")
    if hi_key in block_counts and bn_key in block_counts:
        if block_counts[hi_key] >= block_counts[bn_key]:
            del block_counts[bn_key]
        else:
            del block_counts[hi_key]

    # Only use Unicode result if at least 10% of characters are in a non-Latin block
    total = len([c for c in text if not c.isspace()])
    dominant, count = max(block_counts.items(), key=lambda x: x[1])
    if total > 0 and count / total >= 0.10:
        return dominant
    return "en", "English"


def detect_language(text: str) -> Tuple[str, str]:
    """
    Detect the language of ``text``.

    Returns:
        (lang_code, lang_name)  e.g. ("hi", "Hindi") or ("en", "English")

    Strategy:
      1. Unicode block scan — used as the sole signal for non-Latin scripts
         (Indic, CJK, Arabic, Cyrillic, Thai). Highly reliable, zero cost.
      2. Latin-script text always returns ("en", "English") — langdetect is
         not used for Latin because it produces too many false positives on
         short phrases (e.g. "Cognitive Bias" → Italian).
    """
    if not text or not text.strip():
        return "en", "English"

    code, name = _detect_by_unicode(text)
    return code, name
