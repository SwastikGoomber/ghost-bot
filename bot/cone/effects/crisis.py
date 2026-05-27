"""
Existential crisis coning effect.
"""

import re
import random


def apply_crisis(text: str) -> str:
    """Existential crisis transformation - MAXIMUM EXISTENTIAL DREAD"""
    
    # Advanced existential vocabulary
    replacements = {
        # Time becomes existentially loaded
        r'\b(now|today|currently|present)\b': [
            'in this fleeting moment of existence',
            'during this brief respite from the void',
            'in this temporary illusion of now',
            'while consciousness persists',
            'in this meaningless instant'
        ],
        r'\b(future|tomorrow|later|eventually)\b': [
            'the inevitable march toward oblivion',
            'the uncertain void that awaits',
            'the meaningless tomorrow',
            'our inevitable dissolution',
            'the approaching heat death'
        ],
        r'\b(past|before|previously|earlier)\b': [
            'those equally meaningless moments',
            'the illusion of a meaningful past',
            'our manufactured memories',
            'the arbitrary sequence of events',
            'those fleeting neurochemical patterns'
        ],
        
        # Emotions become existentially questioning
        r'\b(happy|joy|excited|glad|pleased)\b': [
            'temporarily distracted from the void',
            'experiencing fleeting neurochemical pleasure',
            'momentarily forgetting our cosmic insignificance',
            'chemically induced contentment',
            'brief respite from existential dread'
        ],
        r'\b(sad|depressed|down|unhappy)\b': [
            'confronting the fundamental emptiness',
            'experiencing appropriate cosmic despair',
            'recognizing our meaningless existence',
            'feeling the weight of inevitable entropy',
            'acknowledging universal suffering'
        ],
        r'\b(love|care|affection)\b': [
            'evolutionary manipulation disguised as meaning',
            'biochemical processes we call connection',
            'desperate attempts to feel less alone in the universe',
            'temporary bonding before mutual annihilation',
            'chemical reactions masquerading as purpose'
        ],
        
        # Actions become meaningless
        r'\b(do|doing|make|work|create)\b': [
            'engage in ultimately meaningless tasks',
            'perform arbitrary actions to avoid confronting the void',
            'participate in the illusion of purpose',
            'distract ourselves from our impending doom',
            'pretend our actions have cosmic significance'
        ],
        r'\b(achieve|accomplish|succeed|win)\b': [
            'temporarily convince ourselves we matter',
            'participate in society\'s collective delusion',
            'reach arbitrary milestones before death',
            'achieve meaningless victories in a pointless game',
            'accumulate hollow achievements before the void'
        ],
        r'\b(try|attempt|effort|strive)\b': [
            'desperately cling to the illusion of control',
            'struggle against inevitable entropy',
            'persist despite cosmic meaninglessness',
            'fight the unwinnable battle against time',
            'attempt to matter in an indifferent universe'
        ],
        
        # Life and existence
        r'\b(life|living|alive|existence)\b': [
            'this brief flicker of consciousness',
            'our temporary arrangement of atoms',
            'the cosmic joke of self-aware matter',
            'this fleeting dance of particles',
            'our meaningless biological processes'
        ],
        r'\b(purpose|meaning|reason|point)\b': [
            'the desperate search for non-existent meaning',
            'our manufactured sense of purpose',
            'the comforting lie of significance',
            'humanity\'s collective delusion',
            'the void we try to fill with false meaning'
        ],
        r'\b(important|significant|matters|valuable)\b': [
            'temporarily significant in our tiny perspective',
            'meaningful only to our deluded consciousness',
            'important in the context of our cosmic insignificance',
            'arbitrarily valued by pattern-seeking minds',
            'significant only until heat death'
        ],
        
        # People and relationships
        r'\b(people|person|human|everyone)\b': [
            'fellow passengers on spaceship Earth',
            'other temporary arrangements of consciousness',
            'co-conspirators in the meaning-making delusion',
            'fellow victims of cosmic indifference',
            'other atoms temporarily pretending to be important'
        ],
        r'\b(friend|family|relationship)\b': [
            'temporary alliances against the void',
            'shared delusions of connection',
            'mutual distractions from existential truth',
            'biochemical bonding experiments',
            'fellow travelers toward mutual oblivion'
        ],
        
        # Regular words get existential treatment
        r'\b(good|great|awesome|amazing)\b': [
            'temporarily pleasant in this meaningless existence',
            'chemically satisfying despite cosmic irrelevance',
            'subjectively positive in our brief flicker',
            'arbitrarily categorized as beneficial',
            'momentarily distracting from the void'
        ],
        r'\b(bad|terrible|awful|horrible)\b': [
            'appropriately reflecting reality\'s indifference',
            'honestly representing cosmic meaninglessness',
            'accurately depicting our doomed existence',
            'truthfully showing life\'s fundamental suffering',
            'correctly displaying universal entropy'
        ],
        
        # Certainty becomes doubt
        r'\b(know|certain|sure|definitely|obvious)\b': [
            'think we know (but what do we really know?)',
            'assume in our limited perception',
            'believe based on incomplete information',
            'pretend certainty exists in chaos',
            'convince ourselves despite universal uncertainty'
        ]
    }
    
    result = text
    
    # Apply replacements
    for pattern, options in replacements.items():
        def replace_func(match):
            return random.choice(options)
        result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
    
    # Add existential questions randomly
    questions = [
        'But what does any of this really mean?',
        'Does any of this matter in the grand scheme?',
        'Are we just avoiding the inevitable truth?',
        'What\'s the point in a universe that doesn\'t care?',
        'Why do we pretend our actions have meaning?',
        'Is this just elaborate procrastination before death?',
        'Are we simply animals creating stories to cope?'
    ]
    
    # Insert existential doubt
    if random.random() < 0.6:
        result += f' {random.choice(questions)}'
    
    # Add philosophical endings
    endings = [
        'In the end, we\'re all just stardust pretending to matter.',
        'The universe doesn\'t care about our tiny human concerns.',
        'We\'re all just waiting for the heat death anyway.',
        'Nothing we do will matter in a billion years.',
        'The void is patient, but it\'s always watching.',
        'Consciousness is just the universe questioning itself.'
    ]
    
    if random.random() < 0.4:
        result += f' {random.choice(endings)}'
    
    return result
