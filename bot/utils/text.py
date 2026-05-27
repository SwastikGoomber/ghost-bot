"""
Shared text disruption, scrambling, and normalization utilities.
Highly reusable string and list manipulation functions.
"""

import re
import random


def normalize_word(word: str) -> str:
    """Normalize word variations (lmaoooo -> lmao, sooooo -> so)"""
    # Remove excessive repeated characters (keep max 2)
    return re.sub(r'(.)\1{2,}', r'\1\1', word.lower())


def scramble_word(word: str) -> str:
    """Scramble word keeping first and last letters intact (classic middle scramble)"""
    if len(word) <= 3:
        return word
    
    # Various scrambling patterns
    patterns = [
        lambda w: w[0] + ''.join(random.sample(w[1:-1], len(w[1:-1]))) + w[-1],  # Scramble middle
        lambda w: w[1] + w[0] + w[2:] if len(w) > 2 else w,  # Swap first two
        lambda w: w[:-2] + w[-1] + w[-2] if len(w) > 3 else w,  # Swap last two
    ]
    
    return random.choice(patterns)(word)


def swap_adjacent_words(words: list[str]) -> str:
    """Swap two adjacent words in a list and join them"""
    if len(words) < 2:
        return ' '.join(words)
    
    idx = random.randint(0, len(words) - 2)
    words[idx], words[idx + 1] = words[idx + 1], words[idx]
    return ' '.join(words)


def repeat_word(words: list[str]) -> str:
    """Repeat a word (working memory loop or stutter) in a list and join them"""
    if not words:
        return ' '.join(words)
    
    idx = random.randint(0, len(words) - 1)
    repeat_patterns = [
        f"{words[idx]} {words[idx]}",  # Simple repeat
        f"{words[idx][:2]}-{words[idx]}",  # Stutter pattern
    ]
    words[idx] = random.choice(repeat_patterns)
    return ' '.join(words)


def skip_word(words: list[str]) -> str:
    """Skip a non-critical word in a list and join them"""
    if len(words) <= 2:
        return ' '.join(words)
    
    # Skip a non-critical word (not first or last)
    idx = random.randint(1, len(words) - 2)
    words.pop(idx)
    return ' '.join(words)


def simulate_reading_disruption(text: str) -> str:
    """Simulate attention/focus issues that cause reading word order confusion"""
    words = text.split()
    if len(words) < 3:
        return text
    
    disruption_types = [
        swap_adjacent_words,
        repeat_word,
        skip_word
    ]
    
    disruption = random.choice(disruption_types)
    return disruption(words)


def apply_memory_errors(text: str) -> str:
    """Apply working memory errors (letter drops/additions/doublings)"""
    result = []
    
    for char in text:
        # Letter omission (more common in longer words)
        if char.isalpha() and random.random() < 0.05:  # 5% omission chance
            continue  # Skip this letter
        
        result.append(char)
        
        # Letter addition/doubling (less common)
        if char.isalpha() and random.random() < 0.03:  # 3% addition chance
            if random.random() < 0.7:
                result.append(char)  # Double the letter
            else:
                # Add a visually similar letter
                similar = {'a': 'e', 'e': 'a', 'i': 'l', 'o': 'a', 'u': 'n'}
                result.append(similar.get(char.lower(), char))
    
    return ''.join(result)


def apply_sequence_reversals(text: str) -> str:
    """Apply small sequence reversals (2-3 character flips in longer words)"""
    result = text
    words = result.split()
    
    for i, word in enumerate(words):
        if len(word) > 4 and random.random() < 0.15:  # 15% chance per word
            # Pick a random position to start reversal
            start = random.randint(1, len(word) - 3)
            length = random.choice([2, 3])  # Reverse 2-3 characters
            end = min(start + length, len(word) - 1)
            
            # Reverse the subsequence
            before = word[:start]
            reversed_part = word[start:end][::-1]
            after = word[end:]
            words[i] = before + reversed_part + after
    
    return ' '.join(words)
