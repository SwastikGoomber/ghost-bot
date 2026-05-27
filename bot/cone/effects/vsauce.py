"""
VSauce conspiracy coning effect.
"""

import re
import random


def apply_vsauce(text: str) -> str:
    """VSauce conspiracy transformation - MICHAEL HERE WITH QUESTIONS"""
    
    # VSauce-style questioning and conspiracy thinking
    replacements = {
        # Certainty becomes questioning
        r'\b(is|are|was|were)\b': [
            'appears to be', 'seems to be', 'is allegedly', 'is supposedly',
            'is what they want you to believe', 'might be', 'could possibly be'
        ],
        r'\b(happened|occurred|took place)\b': [
            'allegedly happened', 'supposedly occurred', 'is said to have happened',
            'happened (or did it?)', 'occurred according to official sources',
            'took place in what we call reality'
        ],
        r'\b(true|real|actual|factual)\b': [
            'what they want you to believe is true',
            'supposedly real', 'allegedly factual',
            'true according to mainstream sources',
            'real in our perceived reality'
        ],
        r'\b(know|knew|understand|realize)\b': [
            'think we know', 'are told to believe',
            'supposedly understand', 'are led to believe',
            'think we realize', 'assume we know'
        ],
        
        # Simple statements become questions
        r'\b(because|since|due to)\b': [
            'but WHY exactly?', 'but what if', 'but here\'s the thing',
            'but wait, what if', 'but consider this', 'but think about it'
        ],
        r'\b(normal|usual|typical|standard)\b': [
            'what society calls normal', 'supposedly normal',
            'normal according to who?', 'normal (but what IS normal?)',
            'typical in our constructed reality'
        ],
        r'\b(everyone|people|society)\b': [
            'what we call society', 'the masses',
            'people (or ARE they?)', 'everyone who\'s paying attention',
            'society as we know it'
        ],
        
        # Facts become suspicious
        r'\b(fact|evidence|proof|data)\b': [
            'supposed fact', 'what they call evidence',
            'so-called proof', 'data (from questionable sources)',
            'facts according to official sources'
        ],
        r'\b(study|research|science|expert)\b': [
            'study (funded by whom?)', 'research (with questionable motives)',
            'science (controlled by institutions)', 'expert (according to who?)'
        ],
        r'\b(government|official|authority)\b': [
            'government (with hidden agendas)', 'official sources (wink wink)',
            'authorities (who benefit from this)', 'establishment figures'
        ],
        
        # Time becomes questionable
        r'\b(always|never|forever)\b': [
            'always (or so they say)', 'never according to official records',
            'forever in this reality', 'always in what we call time'
        ],
        r'\b(history|past|before)\b': [
            'official history', 'what they teach us about the past',
            'recorded history (by the winners)', 'the past as we\'re told it happened'
        ],
        r'\b(future|will|going to)\b': [
            'future (if there is one)', 'will supposedly',
            'future according to their plans', 'going to (in theory)'
        ],
        
        # Actions become suspicious
        r'\b(told|said|claimed|stated)\b': [
            'allegedly told', 'claimed (without proof)',
            'stated according to official sources', 'said (but can we trust it?)'
        ],
        r'\b(found|discovered|revealed)\b': [
            'supposedly found', 'discovered (or planted?)',
            'revealed by questionable sources', 'found (how convenient)'
        ],
        r'\b(decided|chose|selected)\b': [
            'decided for us', 'chose for their own benefit',
            'selected by unknown forces', 'decided by powers that be'
        ],
        
        # Common words get VSauce treatment
        r'\b(good|bad|right|wrong)\b': [
            'good (according to whose standards?)', 'bad (or exactly as planned?)',
            'right (in whose opinion?)', 'wrong (or perfectly calculated?)'
        ],
        r'\b(random|coincidence|accident)\b': [
            'random (nothing is random)', 'coincidence (there are no coincidences)',
            'accident (or was it?)', 'supposedly random'
        ],
        
        # Questions amplification
        r'\b(what|how|why|when|where|who)\b': [
            'but WHAT really', 'but HOW exactly', 'but WHY though',
            'but WHEN exactly', 'but WHERE specifically', 'but WHO benefits'
        ]
    }
    
    result = text
    
    # Apply replacements with random selection
    for pattern, options in replacements.items():
        def replace_func(match):
            return random.choice(options)
        result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
    
    # Add VSauce-style interjections
    interjections = [
        'But here\'s the thing',
        'But wait, there\'s more',
        'But what if I told you',
        'But here\'s what they don\'t want you to know',
        'But think about it',
        'But consider this',
        'But here\'s the real question',
        'But that\'s exactly what they want you to think'
    ]
    
    # Add conspiracy questions
    questions = [
        'But what if that\'s exactly what they want?',
        'Or IS it?',
        'But who\'s really pulling the strings?',
        'But what if it\'s all connected?',
        'But what are they hiding?',
        'But what if nothing is as it seems?',
        'But who benefits from this narrative?',
        'But what if we\'re asking the wrong questions?'
    ]
    
    # Process sentences with random VSauce treatment
    sentences = re.split(r'[.!?]+', result)
    transformed_sentences = []
    
    for i, sentence in enumerate(sentences):
        if sentence.strip():
            # Add interjection at start sometimes
            if random.random() < 0.4 and i > 0:
                sentence = f"{random.choice(interjections)}: {sentence.strip()}"
            
            # Add questioning at end sometimes
            if random.random() < 0.5:
                sentence = f"{sentence.strip()}... {random.choice(questions)}"
            
            transformed_sentences.append(sentence)
    
    result = '. '.join(transformed_sentences)
    
    # Add classic VSauce endings
    endings = [
        'And as always, thanks for watching',
        'But that\'s just what they want you to think',
        'The rabbit hole goes deeper than you imagine',
        'Question everything, believe nothing',
        'Wake up, sheeple',
        'Connect the dots',
        'Open your eyes to the truth'
    ]
    
    if random.random() < 0.6:
        result += f'... {random.choice(endings)}.'
    
    return result
