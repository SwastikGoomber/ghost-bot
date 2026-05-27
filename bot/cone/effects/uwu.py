"""
UWU (cute speak) coning effect.
"""

import re
import random


def transform_uwu(text: str) -> str:
    """Transform text into cute 'uwu' speak."""
    # 1. Custom Cute Vocabulary Mapping
    vocab = {
        r"\b(hello|hi|hey)\b": "hewo",
        r"\b(Hello|Hi|Hey)\b": "Hewo",
        r"\b(please|plz)\b": "pwease",
        r"\b(Please|Plz)\b": "Pwease",
        r"\b(small|little)\b": "smol",
        r"\b(Small|Little)\b": "Smol",
        r"\b(friend|buddy|dude|bro)\b": "fwend",
        r"\b(Friend|Buddy|Dude|Bro)\b": "Fwend",
        r"\b(cute|pretty)\b": "kawaii",
        r"\b(Cute|Pretty)\b": "Kawaii",
        r"\bstop\b": "stoppi",
        r"\bStop\b": "Stoppi",
        r"\b(god|oh my god)\b": "gawd",
        r"\b(God|Oh my God)\b": "Gawd",
    }
    for pattern, replacement in vocab.items():
        text = re.sub(pattern, replacement, text)

    # 2. Phonetics & Consonant Shifts
    # r/R -> w/W, l/L -> w/W
    text = text.replace("r", "w").replace("R", "W").replace("l", "w").replace("L", "W")

    # Hard "Th" Shifts:
    # this/that/there/they/them/their -> dis/dat/deww/dey/dem/deiw
    text = re.sub(r"\bthis\b", "dis", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthat\b", "dat", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthere\b", "deww", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthey\b", "dey", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthem\b", "dem", text, flags=re.IGNORECASE)
    text = re.sub(r"\btheir\b", "deiw", text, flags=re.IGNORECASE)
    # think/thing -> fink/fing
    text = re.sub(r"\bthink\b", "fink", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthing\b", "fing", text, flags=re.IGNORECASE)

    # N-vowels & M-vowels:
    # na/ne/ni/no/nu -> nya/nye/nyi/nyo/nyu
    text = re.sub(r"\bn([aeiou])", r"ny\1", text)
    text = re.sub(r"\bN([aeiou])", r"Ny\1", text)
    text = re.sub(r"\bm([aeiou])", r"my\1", text)
    text = re.sub(r"\bM([aeiou])", r"My\1", text)

    # Yes/no/love adjustments
    text = re.sub(r"\byes\b", "yesh", text, flags=re.IGNORECASE)
    text = re.sub(r"\bno\b", "nyo", text, flags=re.IGNORECASE)
    text = re.sub(r"ove", "uv", text)

    # 3. Randomized Stuttering
    words = text.split()
    stuttered_words = []
    for word in words:
        if len(word) >= 3 and re.match(r"^[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]", word):
            if random.random() < 0.2:
                first_char = word[0]
                word = f"{first_char}-{word.lower()}"
        stuttered_words.append(word)
    text = " ".join(stuttered_words)

    # Append standard cute emoticon
    text += random.choice([" uwu", " owo", " >w<", " (◕‿◕)", " ♪(´▽｀)"])
    return text
