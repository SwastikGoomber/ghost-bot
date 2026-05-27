"""
Dyslexia coning effect.
"""

import re
import random
from typing import Optional
import spacy

from bot.cone.effects.spacy_loader import is_spacy_available, get_nlp
from bot.utils.text import (
    scramble_word,
    simulate_reading_disruption,
    apply_memory_errors,
    apply_sequence_reversals,
)


def apply_dyslexia(text: str) -> str:
    """Advanced dyslexia transformation using NLP shape and phonetic confusion models."""
    
    # Character-level visual confusion mappings (based on shape similarity)
    visual_confusion = {
        'b': ['d', 'p', 'q'], 'd': ['b', 'p', 'q'], 'p': ['b', 'd', 'q'], 'q': ['b', 'd', 'p'],
        'm': ['w', 'n'], 'w': ['m', 'v'], 'n': ['m', 'u', 'h'], 'u': ['n', 'v'],
        'f': ['t', 'l'], 't': ['f', 'l'], 'l': ['i', 'j', '1'], 'i': ['l', 'j', '1'],
        'a': ['e', 'o'], 'e': ['a', 'o'], 'o': ['a', 'e'], 's': ['z', '5'], 'z': ['s', '2'],
        'g': ['6', '9'], '6': ['9', 'g'], '9': ['6', 'g'], '0': ['o', 'O'], 'O': ['0', 'o'],
        'S': ['5', 'Z'], 'Z': ['S', '2'], 'I': ['l', '1', 'L'], 'L': ['I', '1', 'l']
    }
    
    # Phonetic confusion patterns (common sound-alike errors)
    phonetic_patterns = [
        (r'tion\b', ['shun', 'sion', 'shon']),
        (r'ough\b', ['uf', 'off', 'ow']),
        (r'augh\b', ['af', 'aw', 'alf']),
        (r'eigh\b', ['ay', 'ey', 'a']),
        (r'ph', ['f', 'pf']),
        (r'ch', ['k', 'sh', 'tch']),
        (r'th', ['f', 'd', 't']),
        (r'ck\b', ['k', 'c']),
        (r'qu', ['kw', 'q']),
        (r'x', ['ks', 'z']),
    ]
    
    result = text
    
    # 1. CHARACTER-LEVEL VISUAL CONFUSION
    char_result = []
    for char in result:
        if char.lower() in visual_confusion and random.random() < 0.12:  # 12% chance per character
            confusion_options = visual_confusion[char.lower()]
            new_char = random.choice(confusion_options)
            # Preserve original case
            if char.isupper():
                new_char = new_char.upper()
            char_result.append(new_char)
        else:
            char_result.append(char)
    result = ''.join(char_result)
    
    # 2. PHONETIC PATTERN SUBSTITUTIONS
    for pattern, replacements in phonetic_patterns:
        if random.random() < 0.25:  # 25% chance to apply each pattern
            matches = re.finditer(pattern, result, re.IGNORECASE)
            for match in reversed(list(matches)):  # Reverse to maintain positions
                if random.random() < 0.4:  # 40% chance to replace each match
                    replacement = random.choice(replacements)
                    # Preserve case of original
                    if match.group().isupper():
                        replacement = replacement.upper()
                    elif match.group()[0].isupper():
                        replacement = replacement.capitalize()
                    result = result[:match.start()] + replacement + result[match.end():]
    
    # 3. SYLLABLE AND WORD-LEVEL SCRAMBLING
    if is_spacy_available():
        nlp = get_nlp()
        if nlp is not None:
            doc = nlp(result)
            words = []
            for token in doc:
                if token.is_alpha and len(token.text) > 3:
                    scrambled = _advanced_word_scramble(token.text, token.pos_)
                    words.append(scrambled)
                else:
                    words.append(token.text_with_ws)
            result = ''.join(words).strip()
    else:
        # Fallback: simple word scrambling
        words = result.split()
        for i, word in enumerate(words):
            if len(word) > 4 and word.isalpha() and random.random() < 0.2:
                words[i] = scramble_word(word)
        result = ' '.join(words)
    
    # 4. READING PATTERN SIMULATION
    if random.random() < 0.3:  # 30% chance to apply reading disruption
        result = simulate_reading_disruption(result)
    
    # 5. WORKING MEMORY ERRORS
    result = apply_memory_errors(result)
    
    # 6. SEQUENCE REVERSAL
    if random.random() < 0.25:  # 25% chance
        result = apply_sequence_reversals(result)
    
    return result


def _advanced_word_scramble(word: str, pos: str) -> str:
    """Advanced word scrambling based on POS tag and word characteristics"""
    if len(word) <= 3:
        return word
    
    # Different scrambling strategies based on part of speech
    scramble_probability = {
        'NOUN': 0.3, 'VERB': 0.35, 'ADJ': 0.25, 'ADV': 0.4,  # Content words more likely
        'DET': 0.1, 'PREP': 0.15, 'CONJ': 0.1  # Function words less likely
    }
    
    prob = scramble_probability.get(pos, 0.2)
    if random.random() > prob:
        return word
    
    # Keep first and last, scramble middle (classic dyslexic pattern)
    if len(word) > 4:
        first, middle, last = word[0], list(word[1:-1]), word[-1]
        random.shuffle(middle)
        return first + ''.join(middle) + last
    else:
        # For shorter words, just swap adjacent letters sometimes
        if random.random() < 0.5 and len(word) == 4:
            return word[0] + word[2] + word[1] + word[3]
    
    return word
