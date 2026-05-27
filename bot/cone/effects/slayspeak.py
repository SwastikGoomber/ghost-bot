"""
Valley Girl / Slayspeak coning effect.
"""

import re
import random


def apply_slayspeak(text: str) -> str:
    """Valley girl/slayspeak transformation - AGGRESSIVE"""
    
    # Massive vocabulary replacement (handles typos/variations)
    replacements = {
        # Basic responses (with variations)
        r'\b(yes|yeah|yep|yup|ya|ye)\b': ['yasss', 'totally', 'absolutely', 'for sure'],
        r'\b(no|nah|nope)\b': ['no way', 'absolutely not', 'not even', 'hard no'],
        r'\b(ok|okay|alright|aight)\b': ['like, okay', 'sure thing', 'gotcha', 'bet'],
        
        # Intensifiers and adjectives  
        r'\b(very|really|super|so)\b': ['literally', 'like SO', 'totally', 'absolutely'],
        r'\b(good|great|nice|cool|awesome|amazing)\b': ['iconic', 'absolutely iconic', 'such a vibe', 'literally perfect', 'so aesthetic'],
        r'\b(bad|terrible|awful|sucks|horrible)\b': ['tragic', 'literally tragic', 'not it', 'absolutely not the vibe', 'so chaotic'],
        r'\b(weird|strange|odd|sus)\b': ['sus', 'giving weird vibes', 'not normal', 'kind of sus'],
        r'\b(pretty|quite|kinda|sorta)\b': ['lowkey', 'like', 'literally'],
        
        # Actions and verbs
        r'\b(said|told|spoke)\b': ['was like', 'literally said', 'was all'],
        r'\b(went|walked|left)\b': ['literally went', 'like went', 'totally left'],
        r'\b(did|made|created)\b': ['literally did', 'totally made', 'like created'],
        r'\b(saw|looked|watched)\b': ['literally saw', 'was watching', 'totally saw'],
        r'\b(think|believe|feel)\b': ['like think', 'totally feel', 'literally believe'],
        
        # Emotions and reactions
        r'\b(happy|excited|glad)\b': ['living for this', 'absolutely living', 'so happy'],
        r'\b(sad|upset|mad|angry)\b': ['literally crying', 'so upset', 'absolutely devastated'],
        r'\b(confused|lost|unsure)\b': ['so confused', 'literally lost', 'absolutely clueless'],
        r'\b(tired|exhausted|sleepy)\b': ['literally dying', 'so tired', 'absolutely exhausted'],
        
        # People and relationships
        r'\b(person|people|guy|girl|dude)\b': ['bestie', 'babe', 'hun', 'literally everyone'],
        r'\b(friend|buddy|pal)\b': ['bestie', 'babe', 'literally my person'],
        r'\b(boyfriend|girlfriend)\b': ['mans', 'my person', 'literally my everything'],
        
        # Time and frequency
        r'\b(always|constantly|forever)\b': ['literally always', 'like constantly', 'absolutely always'],
        r'\b(never|rarely|sometimes)\b': ['literally never', 'like never', 'sometimes but like rarely'],
        r'\b(now|currently|today)\b': ['right now', 'literally right now', 'like today'],
        
        # Objects and things
        r'\b(thing|stuff|item)\b': ['literally everything', 'like the whole thing', 'absolutely everything'],
        r'\b(house|home|place)\b': ['literally home', 'like my place', 'the house'],
        r'\b(car|vehicle)\b': ['literally my car', 'the car', 'my ride'],
        
        # Intensifying common words
        r'\b(love|like|enjoy)\b': ['literally obsessed with', 'absolutely love', 'living for'],
        r'\b(hate|dislike)\b': ['literally cannot', 'absolutely hate', 'not living for'],
        r'\b(want|need|desire)\b': ['literally need', 'absolutely want', 'desperately need'],
        
        # Texting/internet slang normalization then slay-ification
        r'\b(lmao+|lol+|haha+)\b': ['literally dying', 'absolutely deceased', 'cannot even'],
        r'\b(omg+|oh my god+)\b': ['literally omg', 'absolutely cannot', 'I cannot even'],
        r'\b(wtf+|what the fuck+)\b': ['literally what', 'absolutely not', 'I cannot'],
    }
    
    result = text
    
    # Apply replacements
    for pattern, options in replacements.items():
        def replace_func(match):
            return random.choice(options)
        result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
    
    # Add valley girl fillers strategically
    fillers = ['like', 'literally', 'totally', 'absolutely']
    sentences = result.split('.')
    transformed_sentences = []
    
    for sentence in sentences:
        if sentence.strip():
            # Add uptalk (question marks to statements)
            if not sentence.strip().endswith('?') and random.random() < 0.3:
                sentence += '?'
            
            # Insert fillers
            words = sentence.split()
            if len(words) > 2:
                # Add filler at random position
                if random.random() < 0.6:
                    pos = random.randint(1, len(words) - 1)
                    words.insert(pos, random.choice(fillers))
            
            transformed_sentences.append(' '.join(words))
    
    result = '. '.join(transformed_sentences)
    
    # Add ending phrases
    endings = ['periodt', 'omygawwwd', 'no cap', 'literally', 'absolutely']
    if random.random() < 0.4:
        result += f' {random.choice(endings)}'
    
    return result
