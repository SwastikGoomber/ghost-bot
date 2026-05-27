"""
Canadian politeness coning effect.
"""

import re
import random


def apply_canadian(text: str) -> str:
    """Canadian politeness transformation - MAXIMUM POLITENESS, EH"""
    
    # Extensive Canadian vocabulary and politeness patterns
    replacements = {
        # Basic courtesy amplification
        r'\b(please|plz)\b': [
            'if you wouldn\'t mind terribly',
            'if it\'s not too much trouble',
            'when you get a chance, eh',
            'if you could possibly',
            'sorry to bother you, but could you'
        ],
        r'\b(thanks|thank you|thx)\b': [
            'thank you so much, eh',
            'thanks a bunch, bud',
            'much appreciated, friend',
            'thanks kindly',
            'sorry, and thank you'
        ],
        r'\b(yes|yeah|yep|sure)\b': [
            'absolutely, eh',
            'you betcha',
            'for sure, bud',
            'definitely, friend',
            'oh, absolutely'
        ],
        r'\b(no|nope|nah)\b': [
            'sorry, I\'m afraid not',
            'oh gosh, no sorry',
            'sorry about that, but no',
            'afraid I can\'t, eh',
            'sorry, but that\'s not gonna work'
        ],
        
        # Requests become extremely polite
        r'\b(can you|could you|would you)\b': [
            'would you mind terribly if',
            'sorry to bother you, but could you possibly',
            'if it\'s not too much trouble, could you',
            'hate to be a bother, but would you mind',
            'sorry for asking, but could you maybe'
        ],
        r'\b(give me|get me|bring me)\b': [
            'sorry, could I possibly trouble you for',
            'if you wouldn\'t mind, could I have',
            'hate to bother you, but could I get',
            'sorry to ask, but might I have',
            'if it\'s not too much trouble, could you bring'
        ],
        r'\b(do this|do that|help)\b': [
            'lend a hand with this, eh',
            'help out with this if you don\'t mind',
            'give me a hand with this, bud',
            'help a fella out',
            'sorry to ask, but could you help'
        ],
        
        # Emotions with Canadian flavor
        r'\b(angry|mad|pissed|annoyed)\b': [
            'a bit frustrated, sorry',
            'slightly perturbed, eh',
            'not too happy about this, bud',
            'a little steamed, sorry to say',
            'somewhat bothered, I\'m afraid'
        ],
        r'\b(excited|happy|thrilled)\b': [
            'pretty darn excited, eh',
            'happier than a kid with a Timbit',
            'pleased as punch, bud',
            'tickled pink about this',
            'over the moon, eh'
        ],
        r'\b(confused|lost|unsure)\b': [
            'a bit turned around, eh',
            'feeling a little lost, sorry',
            'not quite sure what\'s what',
            'scratching my head about this one',
            'a bit puzzled, I\'m afraid'
        ],
        
        # Actions with Canadian politeness
        r'\b(said|told|mentioned)\b': [
            'mentioned politely',
            'brought up gently',
            'suggested respectfully',
            'shared with respect',
            'mentioned, if I may'
        ],
        r'\b(disagreed|argued|fought)\b': [
            'respectfully disagreed',
            'politely suggested otherwise',
            'had a different perspective, eh',
            'respectfully begged to differ',
            'sorry, but had to disagree'
        ],
        r'\b(left|went|departed)\b': [
            'headed out, eh',
            'took off, bud',
            'made my way out',
            'scooted along',
            'moseyed on out'
        ],
        
        # Food and drinks (Canadian references)
        r'\b(coffee|drink|beverage)\b': [
            'double-double',
            'Tim\'s coffee',
            'cup of joe, eh',
            'coffee from Timmies',
            'brew, bud'
        ],
        r'\b(food|meal|snack)\b': [
            'grub, eh',
            'some good eats',
            'tucker, bud',
            'chow',
            'nosh'
        ],
        r'\b(beer|alcohol)\b': [
            'cold one, eh',
            'brewski, bud',
            'beer, eh',
            'cold brew',
            'pint, friend'
        ],
        
        # Weather (mandatory Canadian conversation)
        r'\b(weather|temperature|climate)\b': [
            'weather (beautiful day, eh?)',
            'temperature (bit nippy today)',
            'weather (sure is something out there)',
            'climate (crazy weather we\'re having)',
            'weather (hot enough for ya?)'
        ],
        
        # Places and locations
        r'\b(home|house|place)\b': [
            'place, eh',
            'home and native land',
            'humble abode',
            'little place',
            'neck of the woods'
        ],
        r'\b(store|shop|mall)\b': [
            'shop, eh',
            'the store, bud',
            'Canadian Tire',
            'local shop',
            'place to pick things up'
        ],
        
        # Canadian slang integration
        r'\b(bathroom|restroom|toilet)\b': [
            'washroom, eh',
            'loo, bud',
            'little boys\'/girls\' room',
            'facilities',
            'washroom'
        ],
        r'\b(soda|pop|soft drink)\b': [
            'pop, eh',
            'soft drink, bud',
            'fizzy drink',
            'pop',
            'soda pop'
        ],
        r'\b(money|cash|dollars)\b': [
            'loonies and toonies',
            'Canadian dollars, eh',
            'cash, bud',
            'money, friend',
            'dough, eh'
        ],
        
        # Intensifiers become Canadian
        r'\b(very|really|super|extremely)\b': [
            'pretty darn',
            'real, real',
            'mighty',
            'pretty',
            'awful (as in awfully good)'
        ],
        r'\b(totally|completely|absolutely)\b': [
            'you betcha',
            'absolutely, eh',
            'for sure, bud',
            'without a doubt',
            'completely, friend'
        ]
    }
    
    result = text
    
    # Apply replacements
    for pattern, options in replacements.items():
        def replace_func(match):
            return random.choice(options)
        result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
    
    # Add random apologies (very Canadian)
    apologies = [
        'sorry about that',
        'my apologies, eh',
        'sorry, bud',
        'pardon me',
        'sorry there, friend'
    ]
    
    # Add "eh" and "bud" strategically
    canadian_additions = ['eh', 'bud', 'friend', 'there', 'eh bud']
    
    # Process sentences
    sentences = re.split(r'[.!?]+', result)
    transformed_sentences = []
    
    for sentence in sentences:
        if sentence.strip():
            # Random apology at start
            if random.random() < 0.3:
                sentence = f"{random.choice(apologies)}, {sentence.strip()}"
            
            # Add "eh" or "bud" at end
            if random.random() < 0.6:
                sentence = f"{sentence.strip()}, {random.choice(canadian_additions)}"
            
            transformed_sentences.append(sentence)
    
    result = '. '.join(transformed_sentences)
    
    # Add Canadian endings
    endings = [
        'Thanks for listening, eh',
        'Hope that helps, bud',
        'Take care now, friend',
        'Have a good one, eh',
        'Sorry for rambling there',
        'Beauty day, isn\'t it?'
    ]
    
    if random.random() < 0.5:
        result += f'. {random.choice(endings)}'
    
    return result
