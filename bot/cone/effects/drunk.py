"""
Drunk coning effect.
"""

import random


def transform_drunk(text: str) -> str:
    """Transform text into drunk slurred speech."""
    text = text.replace("s", "sh").replace("S", "Sh")
    words = text.split()
    for i in range(len(words)):
        if random.random() < 0.3:
            words[i] = words[i] + words[i][:2]
    text = " ".join(words) + random.choice([" *hic*", " *burp*", " I'm not drunk!", " *stumbles*"])
    return text
