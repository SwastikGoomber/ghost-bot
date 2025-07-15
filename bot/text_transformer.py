import re
import random
import logging
from typing import Dict, Callable

logger = logging.getLogger(__name__)

class TextTransformer:
    def __init__(self):
        """Initialize text transformer with all cone effects."""
        # Effect aliases mapping
        self.effect_aliases = {
            # UwUfy
            "uwu": "uwufy",
            "uwufy": "uwufy",
            
            # Pirate
            "pirate": "pirate",
            "arrr": "pirate",
            
            # Shakespeare
            "shakespeare": "bardify",
            "bardify": "bardify",
            
            # Valley Girl
            "valley girl": "slayspeak",
            "slayspeak": "slayspeak",
            
            # Gen Z
            "genz": "brainrot",
            "brainrot": "brainrot",
            
            # Corporate
            "corporate": "scrum master",
            "scrum master": "scrum master",
            
            # Caveman
            "caveman": "unga bunga",
            "unga bunga": "unga bunga",
            
            # Drunk
            "drunk": "drunkard",
            "drunkard": "drunkard",
            
            # Emoji
            "emojify": "linkedin slop",
            "linkedin slop": "linkedin slop",
            
            # Existential
            "question everything": "existential crisis",
            "existential crisis": "existential crisis",
            
            # Polite
            "overly polite": "canadian",
            "canadian": "canadian",
            
            # Conspiracy
            "conspiracy": "vsauce sauce",
            "vsauce sauce": "vsauce sauce",
            
            # British
            "british": "bri'ish",
            "bri'ish": "bri'ish",
            
            # Censor
            "censor": "oni",
            "oni": "oni"
        }
        
        # Effect transformation methods
        self.transformers = {
            "uwufy": self._uwufy,
            "pirate": self._pirate,
            "bardify": self._bardify,
            "slayspeak": self._slayspeak,
            "brainrot": self._brainrot,
            "scrum master": self._scrum_master,
            "unga bunga": self._unga_bunga,
            "drunkard": self._drunkard,
            "linkedin slop": self._linkedin_slop,
            "existential crisis": self._existential_crisis,
            "canadian": self._canadian,
            "vsauce sauce": self._vsauce_sauce,
            "bri'ish": self._briish,
            "oni": self._oni
        }
    
    def transform(self, text: str, effect: str) -> str:
        """Transform text with the specified effect."""
        try:
            # Normalize effect name
            normalized_effect = self.effect_aliases.get(effect.lower(), effect.lower())
            
            # Get transformer function
            transformer = self.transformers.get(normalized_effect)
            if not transformer:
                logger.warning(f"Unknown effect: {effect}")
                return f"🧊 Ghost has frozen me! 🧊"
            
            # Apply transformation
            result = transformer(text)
            return result
            
        except Exception as e:
            logger.error(f"Error transforming text with effect '{effect}': {e}")
            return f"🧊 Something went wrong with my cone effect! 🧊"
    
    def _uwufy(self, text: str) -> str:
        """Transform text to uwu speak."""
        # Replace r and l with w
        text = re.sub(r'[rl]', 'w', text)
        text = re.sub(r'[RL]', 'W', text)
        
        # Replace n + vowel with ny + vowel
        text = re.sub(r'n([aeiouAEIOU])', r'ny\1', text)
        
        # Add uwu expressions
        uwu_endings = ['uwu', 'owo', '^w^', '>w<', '(´・ω・`)', '(◕‿◕)']
        text += ' ' + random.choice(uwu_endings)
        
        return text
    
    def _pirate(self, text: str) -> str:
        """Transform text to pirate speak."""
        pirate_dict = {
            'hello': 'ahoy', 'hi': 'ahoy', 'hey': 'ahoy',
            'you': 'ye', 'your': 'yer', 'yes': 'aye',
            'my': 'me', 'friend': 'matey', 'friends': 'mateys',
            'money': 'doubloons', 'steal': 'plunder', 'bathroom': 'head',
            'stop': 'avast', 'look': 'behold', 'the': 'th\'',
            'and': 'an\'', 'to': 'ter', 'for': 'fer'
        }
        
        words = text.split()
        result = []
        
        for word in words:
            # Clean word for lookup
            clean_word = re.sub(r'[^\w]', '', word.lower())
            replacement = pirate_dict.get(clean_word, word)
            result.append(replacement)
        
        pirate_text = ' '.join(result)
        
        # Add pirate endings
        endings = [' arrr!', ' matey!', ' ye scurvy dog!', ' shiver me timbers!', ' avast!']
        return pirate_text + random.choice(endings)
    
    def _bardify(self, text: str) -> str:
        """Transform text to Shakespearean English."""
        shakespeare_dict = {
            'you': 'thou', 'your': 'thy', 'yours': 'thine',
            'are': 'art', 'is': 'is', 'have': 'hast',
            'do': 'dost', 'does': 'doth', 'will': 'shall',
            'can': 'canst', 'cannot': 'cannot', 'would': 'wouldst'
        }
        
        words = text.split()
        result = []
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            replacement = shakespeare_dict.get(clean_word, word)
            result.append(replacement)
        
        bardified = ' '.join(result)
        
        # Add flowery beginnings/endings
        beginnings = ['Prithee, ', 'Hark! ', 'Verily, ', 'Good sir, ']
        endings = [', good sir!', ', I prithee!', ', mine liege!', ' in sooth!']
        
        if random.choice([True, False]):
            bardified = random.choice(beginnings) + bardified
        
        return bardified + random.choice(endings)
    
    def _slayspeak(self, text: str) -> str:
        """Transform text to valley girl speak."""
        # Add valley girl words
        valley_words = ['like', 'totally', 'literally', 'omg', 'so']
        words = text.split()
        
        result = []
        for i, word in enumerate(words):
            result.append(word)
            if i < len(words) - 1 and random.choice([True, False, False]):  # 1/3 chance
                result.append(random.choice(valley_words))
        
        valley_text = ' '.join(result)
        
        # Add valley endings
        endings = [' slay queen! 💅', ' periodt! ✨', ' that\'s so fetch!', ' totally iconic! 💕']
        return valley_text + random.choice(endings)
    
    def _brainrot(self, text: str) -> str:
        """Transform text to Gen Z brainrot speak."""
        brainrot_words = ['no cap', 'fr fr', 'periodt', 'ohio', 'sigma', 'skibidi', 'gyat']
        
        words = text.split()
        result = []
        
        for word in words:
            result.append(word)
            if random.choice([True, False, False, False]):  # 1/4 chance
                result.append(random.choice(brainrot_words))
        
        # Add brainrot endings
        endings = [' no cap 💀💀', ' fr fr periodt', ' ohio energy 💀', ' sigma grindset']
        brainrot_text = ' '.join(result) + random.choice(endings)
        
        return brainrot_text
    
    def _scrum_master(self, text: str) -> str:
        """Transform text to corporate buzzword speak."""
        corporate_dict = {
            'do': 'leverage', 'make': 'ideate', 'fix': 'optimize',
            'talk': 'synergize', 'meet': 'circle back', 'work': 'collaborate',
            'think': 'strategize', 'plan': 'roadmap', 'idea': 'deliverable',
            'problem': 'pain point', 'solution': 'best practice'
        }
        
        words = text.split()
        result = []
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            replacement = corporate_dict.get(clean_word, word)
            result.append(replacement)
        
        corporate_text = ' '.join(result)
        
        # Add corporate phrases
        phrases = [' going forward', ' to optimize our synergies', ' as a best practice', 
                  ' to drive engagement', ' and circle back on deliverables']
        
        return corporate_text + random.choice(phrases)
    
    def _unga_bunga(self, text: str) -> str:
        """Transform text to caveman speak."""
        # Simplify words
        simplified = re.sub(r'\b\w{5,}\b', lambda m: m.group()[:4], text)
        
        words = simplified.split()
        result = []
        
        for word in words:
            # Replace complex words with simple ones
            if len(word) > 6:
                result.append('thing')
            else:
                result.append(word)
        
        # Add caveman grammar
        caveman_text = ' '.join(result)
        caveman_text = re.sub(r'\bI\b', 'me', caveman_text)
        caveman_text = re.sub(r'\bam\b', 'is', caveman_text)
        
        # Add caveman sounds
        endings = [' *grunts*', ' ugg!', ' *pounds chest*', ' good thing!', ' me like!']
        return caveman_text + random.choice(endings)
    
    def _drunkard(self, text: str) -> str:
        """Transform text to drunk speech."""
        # Add random letter doubling
        drunk_text = re.sub(r'([aeiou])', lambda m: m.group() + m.group() if random.choice([True, False, False]) else m.group(), text)
        
        # Add slurred speech
        drunk_text = re.sub(r'ing\b', 'in\'', drunk_text)
        drunk_text = re.sub(r'the\b', 'da', drunk_text)
        
        # Add drunk sounds
        drunk_sounds = [' *hic*', ' *burp*', ' *hiccup*']
        
        # Randomly insert drunk sounds
        words = drunk_text.split()
        result = []
        for word in words:
            result.append(word)
            if random.choice([True, False, False, False]):  # 1/4 chance
                result.append(random.choice(drunk_sounds))
        
        return ' '.join(result) + random.choice([' *hic*', '... *wobbles*'])
    
    def _linkedin_slop(self, text: str) -> str:
        """Transform text to LinkedIn-style emoji spam."""
        professional_emojis = ['💼', '🚀', '💪', '📈', '🎯', '✨', '👏', '🔥', '💡', '🌟']
        
        words = text.split()
        result = []
        
        for word in words:
            result.append(word)
            if random.choice([True, False]):  # 50% chance
                result.append(random.choice(professional_emojis))
        
        # Add LinkedIn ending
        endings = [' Let\'s connect! 🤝', ' Thoughts? 💭', ' Agree? 👍', ' What do you think? 🤔']
        return ' '.join(result) + random.choice(endings)
    
    def _existential_crisis(self, text: str) -> str:
        """Transform text to questioning everything."""
        # Turn statements into questions
        if not text.endswith('?'):
            text = text.rstrip('.!') + '?'
        
        # Add philosophical doubt
        doubt_phrases = [
            ' But what is reality anyway?',
            ' Or is it?', 
            ' Do we really know?',
            ' What does that even mean?',
            ' Are we sure about anything?',
            ' But why?'
        ]
        
        return text + random.choice(doubt_phrases)
    
    def _canadian(self, text: str) -> str:
        """Transform text to overly polite Canadian speech."""
        # Add excessive politeness
        polite_beginnings = [
            'Oh my, I\'m terribly sorry but ',
            'If you don\'t mind me saying, ',
            'With all due respect, ',
            'I hope this doesn\'t offend, but '
        ]
        
        polite_endings = [
            ', if that\'s quite alright',
            ', sorry for any inconvenience',
            ', eh?',
            ', and I\'m sorry if I\'m wrong'
        ]
        
        # Add sorry randomly
        words = text.split()
        result = []
        for word in words:
            result.append(word)
            if random.choice([True, False, False, False, False]):  # 1/5 chance
                result.append('sorry')
        
        polite_text = ' '.join(result)
        
        if random.choice([True, False]):
            polite_text = random.choice(polite_beginnings) + polite_text
        
        return polite_text + random.choice(polite_endings)
    
    def _vsauce_sauce(self, text: str) -> str:
        """Transform text to conspiracy theorist speak."""
        # Add conspiracy elements
        conspiracy_beginnings = [
            'Wake up sheeple! ',
            'They don\'t want you to know that ',
            'The truth is: ',
            'Think about it: '
        ]
        
        conspiracy_endings = [
            ' ...or is it?',
            ' Wake up!',
            ' *adjusts tin foil hat*',
            ' The government doesn\'t want you to know!',
            ' Follow the money!',
            ' Open your eyes!'
        ]
        
        conspiracy_text = text
        
        if random.choice([True, False]):
            conspiracy_text = random.choice(conspiracy_beginnings) + conspiracy_text
        
        return conspiracy_text + random.choice(conspiracy_endings)
    
    def _briish(self, text: str) -> str:
        """Transform text to aggressive British speak."""
        # Replace with British alternatives
        british_dict = {
            'crazy': 'mental', 'stupid': 'daft', 'annoying': 'mental',
            'angry': 'proper mad', 'cool': 'mint', 'awesome': 'brilliant',
            'that': 'tha\'', 'the': 'th\'', 'nothing': 'nowt'
        }
        
        words = text.split()
        result = []
        
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word.lower())
            replacement = british_dict.get(clean_word, word)
            result.append(replacement)
        
        british_text = ' '.join(result)
        
        # Add British swears and expressions
        british_expressions = [
            ' bloody hell!', ' innit!', ' what a right proper wanker!',
            ' absolute madness!', ' mental!', ' proper mental that is!'
        ]
        
        return british_text + random.choice(british_expressions)
    
    def _oni(self, text: str) -> str:
        """Transform text by censoring random words."""
        words = text.split()
        
        # Censor 20-40% of words
        num_to_censor = max(1, len(words) // random.randint(3, 5))
        
        # Choose random words to censor
        words_to_censor = random.sample(range(len(words)), min(num_to_censor, len(words)))
        
        censors = ['[REDACTED]', '[CLASSIFIED]', '[DATA EXPUNGED]', '[CENSORED]', '█████']
        
        result = []
        for i, word in enumerate(words):
            if i in words_to_censor:
                result.append(random.choice(censors))
            else:
                result.append(word)
        
        return ' '.join(result)
    
    def get_available_effects(self) -> list:
        """Get list of all available effects."""
        return list(self.transformers.keys())
    
    def get_effect_aliases(self) -> dict:
        """Get the effect aliases mapping."""
        return self.effect_aliases.copy() 