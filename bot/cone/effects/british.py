"""
British slang coning effect.
"""

import re
import random


def apply_british(text: str) -> str:
    """British transformation - MAXIMUM BRITISH AGGRESSION"""
    
    # Massive British slang, insults, and dialect changes
    replacements = {
        # Basic greetings and responses
        r'\b(hello|hi|hey)\b': [
            'alright mate', 'morning', 'alright there', 'wotcher',
            'watcha', 'oi oi', 'right then'
        ],
        r'\b(yes|yeah|yep)\b': [
            'yeah mate', 'right', 'innit', 'too right',
            'bloody right', 'course', 'aye'
        ],
        r'\b(no|nope|nah)\b': [
            'nah mate', 'bollocks', 'not a chance', 'piss off',
            'do one', 'naff off', 'sod off'
        ],
        r'\b(ok|okay|alright)\b': [
            'right then', 'fair enough', 'sound', 'cushty',
            'bob\'s your uncle', 'sorted'
        ],
        
        # Intensifiers become British
        r'\b(very|really|super|extremely)\b': [
            'bloody', 'proper', 'dead', 'well', 'right',
            'absolutely', 'blimey', 'crikey'
        ],
        r'\b(totally|completely|absolutely)\b': [
            'proper', 'dead', 'absolutely', 'well',
            'bloody hell', 'stone me'
        ],
        
        # Quality descriptors
        r'\b(good|great|awesome|amazing|cool)\b': [
            'brilliant', 'ace', 'smashing', 'top notch', 'bang on',
            'spot on', 'the dog\'s bollocks', 'proper good', 'mint',
            'tidy', 'cushty', 'sound as a pound'
        ],
        r'\b(bad|terrible|awful|horrible|sucks)\b': [
            'rubbish', 'pants', 'naff', 'grim', 'rank',
            'manky', 'minging', 'proper shit', 'absolute bollocks',
            'dire', 'utter toss', 'complete codswallop'
        ],
        r'\b(weird|strange|odd|crazy)\b': [
            'mental', 'barmy', 'daft', 'bonkers', 'crackers',
            'potty', 'round the bend', 'off their rocker',
            'few sandwiches short of a picnic'
        ],
        r'\b(stupid|dumb|idiotic)\b': [
            'thick', 'dim', 'dense', 'thick as two short planks',
            'not the sharpest tool in the shed', 'few cards short of a deck',
            'thick as mince', 'daft as a brush'
        ],
        
        # Actions and verbs
        r'\b(going|walking|leaving)\b': [
            'popping round', 'legging it', 'scarping', 'sodding off',
            'buggering off', 'making tracks', 'doing a runner'
        ],
        r'\b(looking|watching|seeing)\b': [
            'having a butcher\'s', 'taking a gander', 'having a look-see',
            'having a dekko', 'eyeballing', 'clocking'
        ],
        r'\b(talking|speaking|chatting)\b': [
            'having a chinwag', 'nattering', 'rabbiting on',
            'wittering', 'gassing', 'having a natter'
        ],
        r'\b(eating|having food)\b': [
            'having a scoff', 'tucking in', 'getting some grub',
            'having a bite', 'scoffing', 'munching'
        ],
        r'\b(drinking|having a drink)\b': [
            'having a bevvy', 'sinking a pint', 'having a tipple',
            'getting pissed', 'having a swift one'
        ],
        r'\b(sleeping|tired|exhausted)\b': [
            'knackered', 'shattered', 'cream crackered', 'done in',
            'jiggered', 'zonked', 'ready for kip'
        ],
        
        # Emotions
        r'\b(angry|mad|pissed off)\b': [
            'fuming', 'livid', 'seeing red', 'cheesed off',
            'brassed off', 'narked', 'proper wound up'
        ],
        r'\b(happy|excited|pleased)\b': [
            'chuffed', 'made up', 'over the moon', 'pleased as punch',
            'tickled pink', 'buzzing', 'dead chuffed'
        ],
        r'\b(confused|lost|puzzled)\b': [
            'all at sea', 'haven\'t got a clue', 'in a right state',
            'all over the shop', 'not with it'
        ],
        r'\b(drunk|wasted|hammered)\b': [
            'pissed', 'bladdered', 'legless', 'steaming',
            'trollied', 'plastered', 'off their tits'
        ],
        
        # Food and drink
        r'\b(food|meal|dinner)\b': [
            'grub', 'scoff', 'tucker', 'nosh', 'tea'
        ],
        r'\b(breakfast|lunch|dinner)\b': [
            'brekkie', 'elevenses', 'tea', 'supper'
        ],
        r'\b(sandwich|sub)\b': [
            'sarnie', 'butty', 'roll'
        ],
        r'\b(soda|pop|soft drink)\b': [
            'fizzy drink', 'pop', 'soft drink'
        ],
        r'\b(french fries|fries)\b': [
            'chips', 'chippy chips'
        ],
        r'\b(candy|sweets)\b': [
            'sweets', 'sweeties'
        ],
        
        # People and insults
        r'\b(person|guy|dude|man)\b': [
            'bloke', 'geezer', 'fella', 'mate', 'lad'
        ],
        r'\b(woman|girl|lady)\b': [
            'bird', 'lass', 'love', 'darling', 'sweetheart'
        ],
        r'\b(friend|buddy|pal)\b': [
            'mate', 'bruv', 'geezer', 'mucka', 'old bean'
        ],
        r'\b(idiot|moron|fool)\b': [
            'numpty', 'muppet', 'plonker', 'div', 'melt',
            'bellend', 'knobhead', 'tosser', 'wanker', 'prat'
        ],
        
        # Places
        r'\b(bathroom|restroom|toilet)\b': [
            'loo', 'bog', 'khazi', 'dunny', 'lavvy'
        ],
        r'\b(house|home)\b': [
            'gaff', 'pad', 'place', 'drum'
        ],
        r'\b(store|shop)\b': [
            'shop', 'chippy', 'offie', 'corner shop'
        ],
        r'\b(car|vehicle)\b': [
            'motor', 'motor car', 'wheels', 'jam jar'
        ],
        
        # Money and value
        r'\b(money|cash|dollars)\b': [
            'dosh', 'brass', 'dough', 'readies', 'shrapnel',
            'wonga', 'lolly'
        ],
        r'\b(expensive|costly)\b': [
            'dear', 'steep', 'bit pricey', 'costs a bomb'
        ],
        r'\b(cheap|inexpensive)\b': [
            'cheap as chips', 'bargain', 'dead cheap'
        ],
        
        # Time expressions
        r'\b(soon|quickly|fast)\b': [
            'in a jiffy', 'quick as you like', 'double quick',
            'in two shakes', 'before you can say Jack Robinson'
        ],
        r'\b(never|not at all)\b': [
            'not on your nelly', 'when pigs fly', 'not bloody likely'
        ]
    }
    
    result = text
    
    # Apply replacements
    for pattern, options in replacements.items():
        def replace_func(match):
            return random.choice(options)
        result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
    
    # Add British expressions and interjections
    interjections = [
        'blimey', 'crikey', 'bloody hell', 'stone me',
        'gordon bennett', 'flip me', 'strewth'
    ]
    
    # Add British sentence starters
    starters = [
        'Right then', 'I say', 'Look here', 'Hang on',
        'Bloody hell', 'Stone the crows'
    ]
    
    # Weather comments (mandatory British conversation)
    weather_comments = [
        'lovely weather we\'re having, innit',
        'bit nippy today', 'proper grim out there',
        'could murder a cup of tea in this weather'
    ]
    
    # Process sentences
    sentences = re.split(r'[.!?]+', result)
    transformed_sentences = []
    
    for i, sentence in enumerate(sentences):
        if sentence.strip():
            # Add British starter sometimes
            if random.random() < 0.3 and i == 0:
                sentence = f"{random.choice(starters)}, {sentence.strip().lower()}"
            
            # Add interjection sometimes
            if random.random() < 0.4:
                sentence = f"{random.choice(interjections)}, {sentence.strip()}"
            
            # Add "innit" or "eh" at end
            if random.random() < 0.5:
                enders = ['innit', 'eh', 'mate', 'bruv', 'yeah']
                sentence = f"{sentence.strip()}, {random.choice(enders)}"
            
            transformed_sentences.append(sentence)
    
    result = '. '.join(transformed_sentences)
    
    # Add weather comment sometimes
    if random.random() < 0.3:
        result += f'. {random.choice(weather_comments)}'
    
    # Add British endings
    endings = [
        'Cheerio then', 'Bob\'s your uncle', 'Right, I\'m off',
        'Toodle pip', 'Keep your pecker up', 'Mind how you go'
    ]
    
    if random.random() < 0.4:
        result += f'. {random.choice(endings)}.'
    
    return result
