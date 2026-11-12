"""Local Roman Urdu -> Urdu-script speech preparation (no extra AI request).

Text stays in the regular Roman Urdu chat bubble. Only the spoken copy is
transliterated. The conversion is statistical and can misread names or
English/code-mixed words; do not reuse this for commands.
"""
from functools import lru_cache
import re

URDU_SCRIPT = re.compile(r'[\u0600-\u06ff]')
ROMAN_WORDS = re.compile(r'[A-Za-z]+')

# Distinguish normal English sentences from conversational Roman Urdu.
# Avoid turning English product names or explanations into nonsense Urdu words.
URDU_MARKERS = frozenset((
    'aap', 'ap', 'apka', 'aapka', 'aapki', 'aapke', 'apne', 'main', 'mein',
    'mai', 'mujhe', 'mera', 'meri', 'mere', 'hum', 'ham', 'tum', 'tumhe',
    'tumhara', 'tumhari', 'kya', 'kyun', 'kaise', 'kesay', 'kab', 'kahan',
    'hai', 'hain', 'han', 'hoon', 'hun', 'ho', 'tha', 'thi',
    'nahi', 'nahin', 'nhi', 'bilkul', 'acha', 'achha', 'theek', 'thik',
    'kar', 'karo', 'karna', 'karta', 'karti', 'kiya', 'kiye', 'ki',
    'ka', 'ke', 'ko', 'se', 'par', 'aur', 'lekin', 'magar', 'bhi',
    'ye', 'yeh', 'woh', 'wo', 'is', 'us', 'kaam', 'batao', 'bata',
    'bol', 'bolo', 'suno', 'sunao', 'chahiye', 'chahye', 'zaroor',
    'jaldi', 'shukriya', 'bohat', 'bahut', 'bohot', 'boht',
    'tayyar', 'tarah', 'sahi', 'abhi', 'phir', 'wala', 'wali',
))


@lru_cache(maxsize=96)
def spoken_urdu(text):
    """Return bounded Urdu-script TTS input, keeping English-only text as-is."""
    text = str(text).strip()[:1800]
    if not text or not ROMAN_WORDS.search(text):
        return text
    words = [token.casefold() for token in ROMAN_WORDS.findall(text)]
    if not any(token in URDU_MARKERS for token in words):
        return text
    from urdunlp import transliterate_to_urdu
    result = transliterate_to_urdu(text, keep_english=False).strip()
    # Do not let a broken dependency silently speak unusable text.
    if not result or not URDU_SCRIPT.search(result):
        raise RuntimeError('Local Urdu pronunciation conversion failed.')
    return result
