"""
Shakespearean coning effect.
"""

import random


def transform_shakespeare(text: str) -> str:
    """Transform text into Shakespearean English."""
    replacements = {
        "you": "thou", "your": "thy", "You": "Thou", "Your": "Thy",
        "are": "art", "is": "ist", "it": "'tis",
        "yes": "verily", "no": "nay", "because": "for",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text += random.choice([" good sir!", " fair maiden!", " thou art wise!", " verily!"])
    return text
