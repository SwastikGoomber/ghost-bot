"""
Gen-Z Brainrot coning effect.
"""

import re
import random


def apply_brainrot(text: str) -> str:
    """Gen-Z brainrot transformation - MAXIMUM BRAIN ROT"""
    
    # Massive Gen-Z vocabulary (actual current slang)
    replacements = {
        # Truth/agreement markers
        r'\b(really|seriously|actually|truly)\b': ['no cap', 'fr fr', 'on god', 'deadass', 'facts'],
        r'\b(yes|yeah|true|right|correct)\b': ['based', 'valid', 'facts', 'periodt', 'slay'],
        r'\b(no|wrong|false|nah)\b': ['cap', 'L take', 'ratio', 'cringe', 'not it'],
        
        # Quality descriptors
        r'\b(good|great|amazing|awesome|cool)\b': ['slaps', 'hits different', 'bussin', 'fire', 'goated', 'sends me'],
        r'\b(bad|terrible|awful|horrible|sucks)\b': ['mid', 'trash', 'cringe', 'L', 'ratio worthy', 'not it'],
        r'\b(weird|strange|odd|funny)\b': ['sus', 'sending me', 'unhinged', 'chaotic', 'built different'],
        r'\b(boring|dull|lame)\b': ['dry', 'mid', 'NPC behavior', 'no rizz', 'ratio'],
        
        # Actions and behaviors
        r'\b(lying|fibbing|deceiving)\b': ['capping', 'straight capping', 'no cap that\'s cap'],
        r'\b(showing off|bragging|flexing)\b': ['flexing', 'showing out', 'doing the most'],
        r'\b(embarrassing|cringe|awkward)\b': ['cringe', 'secondhand embarrassment', 'giving me the ick'],
        r'\b(trying hard|attempting|working)\b': ['doing the most', 'giving main character energy'],
        r'\b(ignoring|avoiding|dismissing)\b': ['leaving on read', 'ghosting', 'giving cold shoulder'],
        
        # Emotions and states
        r'\b(excited|hyped|pumped)\b': ['hyped', 'absolutely sending me', 'living for this'],
        r'\b(sad|depressed|down)\b': ['in my feels', 'down bad', 'not vibing'],
        r'\b(angry|mad|furious)\b': ['pressed', 'big mad', 'seeing red'],
        r'\b(confused|lost|puzzled)\b': ['??? moment', 'not computing', 'brain.exe stopped'],
        r'\b(tired|exhausted|sleepy)\b': ['dead', 'absolutely deceased', 'running on fumes'],
        
        # People and relationships
        r'\b(attractive|hot|cute|pretty)\b': ['absolutely goated', 'serving looks', 'main character energy'],
        r'\b(boyfriend|girlfriend|partner)\b': ['mans', 'my person', 'literally my Roman Empire'],
        r'\b(friend|buddy|bestie)\b': ['bestie', 'my person', 'literally family'],
        r'\b(person|people|someone)\b': ['this person', 'bestie', 'main character'],
        
        # Internet/phone behavior
        r'\b(texting|messaging|calling)\b': ['sliding into DMs', 'hitting up', 'dropping texts'],
        r'\b(posting|sharing|uploading)\b': ['dropping content', 'serving looks', 'posting for the timeline'],
        r'\b(scrolling|browsing|looking)\b': ['doom scrolling', 'living on the timeline', 'chronically online'],
        
        # Intensifiers
        r'\b(very|really|super|extremely)\b': ['absolutely', 'lowkey', 'highkey', 'literally'],
        r'\b(totally|completely|absolutely)\b': ['deadass', 'no cap', 'absolutely'],
        
        # Common expressions
        r'\b(whatever|anyways|okay)\b': ['anyways chile', 'periodt', 'and what about it'],
        r'\b(understand|get it|comprehend)\b': ['it\'s giving', 'I see the vision', 'absolutely vibing with'],
        
        # Texting variations (handle elongated versions)
        r'\b(lmao+|lol+|haha+)\b': ['SENDING ME', 'absolutely deceased', 'can\'t even', 'I\'m gone'],
        r'\b(omg+|oh my god+)\b': ['NOT THE', 'absolutely not', 'I cannot even', 'bestie what'],
        r'\b(wtf+|what the f+)\b': ['bestie what', 'absolutely not', 'this ain\'t it'],
    }
    
    result = text
    
    # Apply replacements with random selection
    for pattern, options in replacements.items():
        def replace_func(match):
            return random.choice(options)
        result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
    
    # Add random brainrot interjections
    interjections = [
        'periodt', 'no cap', 'fr fr', 'deadass', 'on god', 'facts', 'slay', 
        'bestie', 'not me', 'the way', 'I cannot', 'sending me', 'absolutely not',
        'this is it', 'main character moment', 'it\'s giving', 'serves'
    ]
    
    # Split into sentences and add interjections
    sentences = re.split(r'[.!?]+', result)
    transformed_sentences = []
    
    for sentence in sentences:
        if sentence.strip():
            # Random chance to add interjection at start
            if random.random() < 0.3:
                sentence = f"{random.choice(interjections)} {sentence.strip()}"
            
            # Random chance to add at end
            if random.random() < 0.4:
                sentence = f"{sentence.strip()} {random.choice(interjections)}"
            
            transformed_sentences.append(sentence)
    
    result = '. '.join(transformed_sentences)
    
    # Final brainrot touches
    endings = ['periodt', 'and that\'s on periodt', 'no cap', 'slay', 'absolutely sending me']
    if random.random() < 0.5:
        result += f' {random.choice(endings)}'
    
    return result
