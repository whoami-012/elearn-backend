import re
import unicodedata

from app.messaging.exceptions import unprocessable


# Unicode ranges with Emoji/Emoji_Presentation semantics. Kept explicit so the
# validator is deterministic without a platform-specific regex dependency.
_EMOJI_RANGES = re.compile(
    "["
    "\\U0001F000-\\U0001FAFF"  # pictographs, emoticons, transport, symbols
    "\\U0001FC00-\\U0001FFFF"
    "\\u00a9\\u00ae\\u203c\\u2049\\u2122\\u2139"
    "\\u2194-\\u2199\\u21a9-\\u21aa\\u231a-\\u231b\\u2328\\u23cf"
    "\\u23e9-\\u23f3\\u23f8-\\u23fa\\u24c2\\u25aa-\\u25ab\\u25b6"
    "\\u25c0\\u25fb-\\u25fe\\u2600-\\u2604\\u260e\\u2611\\u2614-\\u2615"
    "\\u2618\\u261d\\u2620\\u2622-\\u2623\\u2626\\u262a\\u262e-\\u262f"
    "\\u2638-\\u263a\\u2640\\u2642\\u2648-\\u2653\\u265f-\\u2660\\u2663"
    "\\u2665-\\u2666\\u2668\\u267b\\u267e-\\u267f\\u2692-\\u2697\\u2699"
    "\\u269b-\\u269c\\u26a0-\\u26a1\\u26a7\\u26aa-\\u26ab\\u26b0-\\u26b1"
    "\\u26bd-\\u26be\\u26c4-\\u26c5\\u26c8\\u26ce-\\u26cf\\u26d1\\u26d3-\\u26d4"
    "\\u26e9-\\u26ea\\u26f0-\\u26f5\\u26f7-\\u26fa\\u26fd\\u2702\\u2705"
    "\\u2708-\\u270d\\u270f\\u2712\\u2714\\u2716\\u271d\\u2721\\u2728"
    "\\u2733-\\u2734\\u2744\\u2747\\u274c\\u274e\\u2753-\\u2755\\u2757"
    "\\u2763-\\u2764\\u2795-\\u2797\\u27a1\\u27b0\\u27bf\\u2934-\\u2935"
    "\\u2b05-\\u2b07\\u2b1b-\\u2b1c\\u2b50\\u2b55\\u3030\\u303d\\u3297\\u3299"
    "]"
)
_REGIONAL_INDICATOR = re.compile("[\\U0001F1E6-\\U0001F1FF]")
_SKIN_TONE = re.compile("[\\U0001F3FB-\\U0001F3FF]")
_TAG_CHARACTER = re.compile("[\\U000E0020-\\U000E007F]")
_KEYCAP = re.compile(r"[0-9#*]\\ufe0f?\\u20e3")


def contains_emoji(value: str) -> bool:
    normalized = unicodedata.normalize("NFC", value)
    return bool(
        _EMOJI_RANGES.search(normalized)
        or _REGIONAL_INDICATOR.search(normalized)
        or _SKIN_TONE.search(normalized)
        or _TAG_CHARACTER.search(normalized)
        or _KEYCAP.search(normalized)
        or "\u200d" in normalized
        or "\ufe0f" in normalized
    )


def validate_no_emoji(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    if contains_emoji(value):
        raise unprocessable("EMOJI_NOT_ALLOWED", "Emojis are not allowed in messages.")
    return value
