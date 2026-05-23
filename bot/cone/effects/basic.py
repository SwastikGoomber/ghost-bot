"""
Basic cone text transformation functions.

All functions have the signature: transform(text: str) -> str
They are intentionally kept simple (regex + word replacement) with no external deps.
Advanced / spaCy-powered equivalents live in advanced.py.
"""

import random
import re


def transform_uwu(text: str) -> str:
    replacements = {
        "r": "w", "R": "W", "l": "w", "L": "W",
        "no": "nyo", "No": "Nyo", "NO": "NYO",
        "yes": "yesh", "Yes": "Yesh", "YES": "YESH",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text += random.choice([" uwu", " owo", " >w<", " (◕‿◕)", " ♪(´▽｀)"])
    return text


def transform_pirate(text: str) -> str:
    replacements = {
        "you": "ye", "your": "yer", "You": "Ye", "Your": "Yer",
        "my": "me", "My": "Me", "is": "be", "are": "be",
        "yes": "aye", "Yes": "Aye", "hello": "ahoy", "Hello": "Ahoy",
        "for": "fer", "over": "o'er",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text += random.choice([" arrr!", " ye scurvy dog!", " shiver me timbers!", " ahoy matey!"])
    return text


def transform_shakespeare(text: str) -> str:
    replacements = {
        "you": "thou", "your": "thy", "You": "Thou", "Your": "Thy",
        "are": "art", "is": "ist", "it": "'tis",
        "yes": "verily", "no": "nay", "because": "for",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text += random.choice([" good sir!", " fair maiden!", " thou art wise!", " verily!"])
    return text


def transform_caveman(text: str) -> str:
    text = text.replace("I", "Me").replace(" am ", " ").replace(" is ", " ")
    text = " ".join(word for word in text.split() if len(word) <= 6)
    text += random.choice([" Me hungry!", " Fire good!", " Ooga booga!"])
    return text


def transform_drunk(text: str) -> str:
    text = text.replace("s", "sh").replace("S", "Sh")
    words = text.split()
    for i in range(len(words)):
        if random.random() < 0.3:
            words[i] = words[i] + words[i][:2]
    text = " ".join(words) + random.choice([" *hic*", " *burp*", " I'm not drunk!", " *stumbles*"])
    return text
