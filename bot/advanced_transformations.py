"""
Advanced Text Transformations for Cone Effects
Uses spaCy, NLTK, and other NLP libraries for sophisticated linguistic transformations.
Optimized for Render free tier resource constraints.
"""

import re
import random
import functools
from typing import Dict, List, Optional, Tuple
import logging

# Lazy imports to avoid startup delays if models aren't available
nlp = None
wordnet = None
TextBlob = None

def get_nlp():
    """Lazy load spaCy model with error handling for deployment."""
    global nlp
    if nlp is None:
        try:
            import spacy
            # Try small model first (most likely to work on free tier)
            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                # Fallback to basic English model if small isn't available
                try:
                    nlp = spacy.load("en")
                except OSError:
                    logging.warning("spaCy model not available, falling back to basic transformations")
                    nlp = False  # Mark as unavailable
        except ImportError:
            logging.warning("spaCy not available, falling back to basic transformations")
            nlp = False
    return nlp if nlp is not False else None

def get_wordnet():
    """Lazy load WordNet with NLTK."""
    global wordnet
    if wordnet is None:
        try:
            import nltk
            from nltk.corpus import wordnet as wn
            # Try to access wordnet, download if needed
            try:
                list(wn.all_synsets())[:1]  # Test access
                wordnet = wn
            except LookupError:
                logging.info("Downloading WordNet data...")
                nltk.download('wordnet', quiet=True)
                nltk.download('omw-1.4', quiet=True)  # For non-English WordNet
                wordnet = wn
        except Exception as e:
            logging.warning(f"WordNet not available: {e}")
            wordnet = False
    return wordnet if wordnet is not False else None

def get_textblob():
    """Lazy load TextBlob."""
    global TextBlob
    if TextBlob is None:
        try:
            from textblob import TextBlob as TB
            TextBlob = TB
        except ImportError:
            logging.warning("TextBlob not available")
            TextBlob = False
    return TextBlob if TextBlob is not False else None

@functools.lru_cache(maxsize=256)
def get_synonyms(word: str, pos: str = None) -> List[str]:
    """Get synonyms for a word, cached for performance."""
    wn = get_wordnet()
    if not wn:
        return []
    
    synonyms = set()
    for synset in wn.synsets(word, pos=pos):
        for lemma in synset.lemmas():
            synonym = lemma.name().replace('_', ' ')
            if synonym.lower() != word.lower() and synonym.isalpha():
                synonyms.add(synonym)
    
    return list(synonyms)[:5]  # Limit to prevent overwhelming choice

def analyze_text_structure(text: str) -> Dict:
    """Analyze text structure using spaCy if available."""
    nlp_model = get_nlp()
    if not nlp_model:
        # Fallback basic analysis
        return {
            'tokens': text.split(),
            'sentences': text.split('.'),
            'has_spacy': False
        }
    
    doc = nlp_model(text)
    return {
        'doc': doc,
        'tokens': [(token.text, token.pos_, token.lemma_, token.dep_) for token in doc],
        'sentences': [sent.text for sent in doc.sents],
        'entities': [(ent.text, ent.label_) for ent in doc.ents],
        'has_spacy': True
    }

def calculate_text_quality(original: str, transformed: str) -> Dict[str, float]:
    """Calculate quality metrics for transformed text."""
    metrics = {
        'length_similarity': 0.0,
        'word_overlap': 0.0,
        'character_change_ratio': 0.0,
        'valid_transformation': 1.0
    }
    
    try:
        # Length similarity (penalize extreme changes)
        orig_len = len(original.split())
        trans_len = len(transformed.split())
        if orig_len > 0:
            metrics['length_similarity'] = 1.0 - abs(orig_len - trans_len) / orig_len
        
        # Word overlap (some words should remain the same)
        orig_words = set(original.lower().split())
        trans_words = set(transformed.lower().split())
        if orig_words:
            metrics['word_overlap'] = len(orig_words & trans_words) / len(orig_words)
        
        # Character change ratio
        import difflib
        matcher = difflib.SequenceMatcher(None, original, transformed)
        metrics['character_change_ratio'] = matcher.ratio()
        
        # Basic validation
        if len(transformed.strip()) == 0:
            metrics['valid_transformation'] = 0.0
        elif transformed == original:
            metrics['valid_transformation'] = 0.5  # Not transformed
        
    except Exception as e:
        logging.warning(f"Error calculating text quality: {e}")
    
    return metrics

class AdvancedTransformer:
    """Base class for sophisticated text transformations."""
    
    def __init__(self):
        self.cache = {}  # Simple caching for repeated transformations
        self.quality_threshold = 0.3  # Minimum quality score
    
    def transform(self, text: str) -> str:
        """Main transformation method - override in subclasses."""
        return text
    
    def validate_transformation(self, original: str, transformed: str) -> bool:
        """Validate that transformation meets quality standards."""
        if not transformed or transformed.strip() == "":
            return False
        
        # Don't allow identical transformations
        if transformed == original:
            return False
        
        # Check quality metrics
        quality = calculate_text_quality(original, transformed)
        
        # Ensure reasonable word overlap (not too much change)
        if quality['word_overlap'] < 0.2:
            return False
        
        # Ensure reasonable length similarity
        if quality['length_similarity'] < 0.5:
            return False
        
        return True
    
    def cached_transform(self, text: str) -> str:
        """Cached version of transform for performance."""
        if text in self.cache:
            return self.cache[text]
        
        result = self.transform(text)
        
        # Validate transformation quality
        if not self.validate_transformation(text, result):
            logging.warning(f"Transformation quality check failed, using fallback")
            # Return basic transformation or original
            result = self._fallback_transform(text)
        
        # Keep cache size manageable
        if len(self.cache) > 100:
            self.cache.clear()
        
        self.cache[text] = result
        return result
    
    def _fallback_transform(self, text: str) -> str:
        """Fallback transformation when advanced fails quality check."""
        # Override in subclasses for effect-specific fallback
        return text

class AdvancedShakespeareTransformer(AdvancedTransformer):
    """Sophisticated Shakespearean/Early Modern English transformation."""
    
    def __init__(self):
        super().__init__()
        # Greatly expanded grammatical transformations
        self.verb_transforms = {
            # Existing verbs
            'are': 'art', 'is': 'ist', 'have': 'hast', 'do': 'dost',
            'will': 'wilt', 'shall': 'shalt', 'can': 'canst', 'may': 'mayst',
            # Additional verbs
            'know': 'knowest', 'go': 'goest', 'come': 'comest', 'see': 'seest',
            'hear': 'hearest', 'speak': 'speakest', 'say': 'sayest', 'tell': 'tellest',
            'give': 'givest', 'take': 'takest', 'make': 'makest', 'get': 'gettest',
            'want': 'wantest', 'need': 'needest', 'love': 'lovest', 'hate': 'hatest',
            'help': 'helpest', 'find': 'findest', 'think': 'thinkest', 'feel': 'feelest',
            'believe': 'believest', 'understand': 'understandest', 'remember': 'rememberest'
        }
        
        self.pronoun_transforms = {
            'you': 'thou', 'your': 'thy', 'yours': 'thine',
            'yourself': 'thyself', 'you\'re': 'thou art', 'you\'ve': 'thou hast',
            'you\'ll': 'thou wilt', 'you\'d': 'thou wouldst'
        }
        
        # Massively expanded vocabulary - hundreds of words
        self.vocab_replacements = {
            # Time and frequency
            'because': 'for', 'before': 'ere', 'often': 'oft', 'always': 'ever',
            'never': 'ne\'er', 'forever': 'for aye', 'again': 'once more',
            'when': 'whence', 'while': 'whilst', 'until': 'till', 'since': 'sith',
            'now': 'anon', 'soon': 'anon', 'today': 'this day', 'tonight': 'this eve',
            'yesterday': 'yesternight', 'tomorrow': 'on the morrow',
            
            # Places and directions
            'between': 'betwixt', 'nothing': 'naught', 'here': 'hither',
            'there': 'thither', 'where': 'whither', 'everywhere': 'everywither',
            'somewhere': 'somewhither', 'anywhere': 'anywhither', 'home': 'hearth',
            'inside': 'within', 'outside': 'without', 'above': 'aloft',
            'below': 'beneath', 'near': 'nigh', 'far': 'afar',
            
            # Actions and states
            'think': 'methinks', 'said': 'quoth', 'look': 'behold', 'see': 'espy',
            'listen': 'hearken', 'hear': 'hark', 'call': 'cry', 'shout': 'proclaim',
            'whisper': 'murmur', 'speak': 'discourse', 'talk': 'converse',
            'walk': 'stroll', 'run': 'hasten', 'hurry': 'make haste', 'stop': 'cease',
            'begin': 'commence', 'end': 'conclude', 'finish': 'complete',
            'start': 'embark', 'continue': 'proceed', 'return': 'retreat',
            
            # Emotions and feelings
            'happy': 'merry', 'sad': 'melancholy', 'angry': 'wrathful', 'mad': 'wrathful',
            'excited': 'elated', 'scared': 'afrighted', 'worried': 'troubled',
            'surprised': 'amazed', 'confused': 'perplexed', 'tired': 'weary',
            'brave': 'valiant', 'coward': 'craven', 'beautiful': 'fair',
            'ugly': 'foul', 'smart': 'wise', 'stupid': 'foolish',
            
            # Common objects and concepts
            'clothes': 'garments', 'dress': 'gown', 'hat': 'cap', 'shoes': 'slippers',
            'house': 'dwelling', 'room': 'chamber', 'bed': 'couch', 'door': 'portal',
            'window': 'casement', 'food': 'victuals', 'drink': 'beverage',
            'money': 'coin', 'work': 'labour', 'job': 'occupation', 'business': 'affairs',
            
            # People and relationships
            'person': 'soul', 'people': 'folk', 'man': 'gentleman', 'woman': 'lady',
            'girl': 'maiden', 'boy': 'lad', 'child': 'youngling', 'baby': 'babe',
            'friend': 'companion', 'enemy': 'foe', 'stranger': 'unknown',
            'family': 'kin', 'mother': 'dame', 'father': 'sire', 'sister': 'sibling',
            
            # Intensifiers and qualifiers
            'very': 'most', 'really': 'verily', 'truly': 'forsooth', 'certainly': 'certes',
            'maybe': 'mayhap', 'perhaps': 'perchance', 'probably': 'belike',
            'definitely': 'assuredly', 'absolutely': 'verily', 'quite': 'rather',
            'completely': 'wholly', 'totally': 'entirely', 'almost': 'nigh',
            
            # Questions and responses
            'what': 'what ho', 'why': 'wherefore', 'how': 'by what means',
            'yes': 'aye', 'no': 'nay', 'okay': 'very well', 'alright': 'well then',
            'thanks': 'grammercy', 'please': 'prithee', 'excuse me': 'pardon',
            'sorry': 'forgive me', 'hello': 'well met', 'goodbye': 'fare thee well',
            
            # Misc common words
            'thing': 'matter', 'stuff': 'things', 'great': 'grand', 'good': 'fair',
            'bad': 'ill', 'wrong': 'amiss', 'right': 'just', 'weird': 'strange',
            'cool': 'fair', 'awesome': 'wondrous', 'terrible': 'dreadful',
            'amazing': 'marvellous', 'interesting': 'curious', 'boring': 'tedious'
        }
        
        self.endings = [
            ' prithee!', ' good sir!', ' fair maiden!', ' marry!', 
            ' forsooth!', ' hark!', ' verily!', ' marry, \'tis true!',
            ' by my troth!', ' odds bodkins!', ' marry come up!',
            ' i\' faith!', ' marry, \'tis so!', ' by\'r lady!', ' grammercy!'
        ]
    
    def transform(self, text: str) -> str:
        structure = analyze_text_structure(text)
        
        if structure['has_spacy']:
            return self._advanced_transform(structure)
        else:
            return self._basic_transform(text)
    
    def _fallback_transform(self, text: str) -> str:
        """Fallback to basic Shakespeare transformation."""
        return self._basic_transform(text)
    
    def _advanced_transform(self, structure: Dict) -> str:
        """Use spaCy analysis for grammatically aware transformation."""
        doc = structure['doc']
        transformed_tokens = []
        
        for token in doc:
            word = token.text
            lemma = token.lemma_.lower()
            pos = token.pos_
            
            # Handle different parts of speech appropriately
            if pos == 'PRON' and lemma in self.pronoun_transforms:
                # Pronoun transformation with case handling
                if word.isupper():
                    transformed_tokens.append(self.pronoun_transforms[lemma].upper())
                elif word.istitle():
                    transformed_tokens.append(self.pronoun_transforms[lemma].title())
                else:
                    transformed_tokens.append(self.pronoun_transforms[lemma])
                    
            elif pos == 'VERB' and lemma in self.verb_transforms:
                # Verb transformation (more complex - could analyze tense/person)
                if token.tag_ in ['VBZ', 'VBP']:  # Present tense
                    transformed_tokens.append(self.verb_transforms[lemma])
                else:
                    transformed_tokens.append(word)
                    
            elif pos in ['NOUN', 'ADJ', 'ADV'] and lemma in self.vocab_replacements:
                # Vocabulary replacement with case preservation
                replacement = self.vocab_replacements[lemma]
                if word.isupper():
                    transformed_tokens.append(replacement.upper())
                elif word.istitle():
                    transformed_tokens.append(replacement.title())
                else:
                    transformed_tokens.append(replacement)
                    
            else:
                transformed_tokens.append(word)
            
            # Add space after token unless it's punctuation
            if not token.is_punct and token.i < len(doc) - 1:
                transformed_tokens.append(' ')
        
        result = ''.join(transformed_tokens)
        
        # Add appropriate ending
        if not any(result.endswith(punct) for punct in '.!?'):
            result += random.choice(self.endings)
        
        return result
    
    def _basic_transform(self, text: str) -> str:
        """Fallback transformation without spaCy."""
        # Apply basic word replacements
        for old, new in {**self.pronoun_transforms, **self.verb_transforms, **self.vocab_replacements}.items():
            # Case-sensitive replacement
            text = re.sub(r'\b' + re.escape(old) + r'\b', new, text, flags=re.IGNORECASE)
            text = re.sub(r'\b' + re.escape(old.title()) + r'\b', new.title(), text)
        
        if not any(text.endswith(punct) for punct in '.!?'):
            text += random.choice(self.endings)
        
        return text

class AdvancedPirateTransformer(AdvancedTransformer):
    """Context-aware pirate speak transformation."""
    
    def __init__(self):
        super().__init__()
        # Greatly expanded basic replacements
        self.basic_replacements = {
            'you': 'ye', 'your': 'yer', 'my': 'me', 'over': "o'er",
            'for': 'fer', 'of': "o'", 'between': 'betwixt', 'to': 'ter',
            'the': 'th\'', 'them': 'em', 'they': 'they be', 'their': 'theirr',
            'there': 'thar', 'here': 'har', 'where': 'whar', 'when': 'wen',
            'what': 'wot', 'who': 'who be', 'how': 'har', 'why': 'why be',
            'with': 'wit\'', 'from': 'fram', 'about': 'aboot', 'after': 'arter',
            'before': 'afore', 'around': 'aroond', 'through': 'thru',
            'because': 'cause', 'without': 'withooot', 'until': 'till'
        }
        
        # Massively expanded pirate vocabulary - hundreds of maritime and pirate terms
        self.pirate_vocab = {
            # Basic replacements from before
            'money': 'doubloons', 'gold': 'treasure', 'steal': 'plunder',
            'fight': 'battle', 'ship': 'vessel', 'captain': 'cap\'n',
            'friend': 'matey', 'enemy': 'scurvy dog', 'drink': 'grog',
            'food': 'grub', 'bathroom': 'head', 'kitchen': 'galley',
            
            # Maritime terms
            'boat': 'vessel', 'sail': 'hoist the colors', 'ocean': 'briny deep',
            'sea': 'seven seas', 'water': 'briny', 'wave': 'swell', 'storm': 'tempest',
            'wind': 'gale', 'rope': 'line', 'flag': 'colors', 'anchor': 'hook',
            'dock': 'pier', 'port': 'harbor', 'island': 'isle', 'map': 'chart',
            'compass': 'navigation', 'telescope': 'spyglass', 'wheel': 'helm',
            
            # Pirate life
            'treasure': 'booty', 'chest': 'strongbox', 'sword': 'cutlass',
            'gun': 'pistol', 'knife': 'dirk', 'hat': 'tricorn', 'coat': 'greatcoat',
            'boots': 'sea boots', 'shirt': 'tunic', 'pants': 'breeches',
            'belt': 'sash', 'jewelry': 'baubles', 'ring': 'band',
            
            # Actions and verbs
            'walk': 'swagger', 'run': 'scurry', 'climb': 'scale the rigging',
            'jump': 'leap', 'fall': 'tumble', 'grab': 'snatch', 'hold': 'grip',
            'throw': 'hurl', 'catch': 'snare', 'hide': 'stash', 'find': 'discover',
            'search': 'hunt', 'look': 'spy', 'watch': 'keep watch', 'listen': 'hark',
            'speak': 'parley', 'shout': 'bellow', 'whisper': 'mutter',
            'laugh': 'chortle', 'cry': 'weep', 'sing': 'shanty', 'dance': 'jig',
            
            # People and relationships
            'person': 'soul', 'people': 'crew', 'group': 'crew', 'team': 'crew',
            'leader': 'captain', 'boss': 'commodore', 'worker': 'deck hand',
            'stranger': 'landlubber', 'coward': 'yellow belly', 'hero': 'brave soul',
            'thief': 'scallywag', 'liar': 'bilge rat', 'fool': 'scurvy cur',
            'woman': 'lass', 'man': 'lad', 'girl': 'young lass', 'boy': 'cabin boy',
            'mother': 'dear mother', 'father': 'old salt', 'child': 'young one',
            
            # Places and locations
            'home': 'port', 'house': 'quarters', 'room': 'cabin', 'bed': 'hammock',
            'floor': 'deck', 'ceiling': 'overhead', 'wall': 'bulkhead',
            'door': 'hatch', 'window': 'porthole', 'stairs': 'ladder',
            'basement': 'bilge', 'attic': 'crow\'s nest', 'garage': 'dry dock',
            'yard': 'deck', 'street': 'waterfront', 'city': 'port town',
            'country': 'waters', 'world': 'seven seas',
            
            # Food and drink
            'beer': 'ale', 'wine': 'rum', 'water': 'fresh water', 'coffee': 'grog',
            'tea': 'brew', 'soup': 'stew', 'bread': 'hardtack', 'meat': 'salt pork',
            'fish': 'catch of the day', 'fruit': 'provisions', 'vegetables': 'ship\'s stores',
            'meal': 'mess', 'dinner': 'supper', 'breakfast': 'morning mess',
            
            # Emotions and states
            'happy': 'merry', 'sad': 'down in the doldrums', 'angry': 'steaming mad',
            'excited': 'fired up', 'tired': 'dog tired', 'sick': 'under the weather',
            'healthy': 'shipshape', 'strong': 'hearty', 'weak': 'scurvy',
            'brave': 'bold', 'scared': 'yellow', 'worried': 'troubled',
            'surprised': 'taken aback', 'confused': 'all at sea',
            
            # Common objects
            'car': 'land ship', 'truck': 'cargo wagon', 'bike': 'two-wheeler',
            'computer': 'thinking box', 'phone': 'speaking device', 'book': 'tome',
            'pen': 'quill', 'paper': 'parchment', 'bag': 'sea bag', 'box': 'crate',
            'bottle': 'flask', 'cup': 'mug', 'plate': 'mess tin', 'spoon': 'ladle',
            
            # Time
            'day': 'sun', 'night': 'dark watch', 'morning': 'dawn watch',
            'evening': 'dusk', 'hour': 'bell', 'minute': 'moment', 'second': 'tick',
            'week': 'seven suns', 'month': 'moon cycle', 'year': 'voyage',
            'time': 'chronometer', 'clock': 'timepiece', 'watch': 'pocket piece',
            
            # Weather and nature
            'sun': 'blazing orb', 'moon': 'night lantern', 'star': 'navigation point',
            'cloud': 'sky sail', 'rain': 'squall', 'snow': 'white caps',
            'fire': 'flame', 'ice': 'frozen bilge', 'rock': 'reef', 'sand': 'shore',
            'tree': 'mast timber', 'flower': 'shore bloom', 'grass': 'land weed'
        }
        
        self.verb_endings = {
            'ing': "in'", 'ed': "ed"  # Transform -ing endings
        }
        
        # Expanded pirate interjections and exclamations
        self.pirate_interjections = [
            'Arrr!', 'Avast!', 'Shiver me timbers!', 'Yo ho ho!',
            'Batten down the hatches!', 'All hands on deck!', 'Ahoy there!',
            'Blimey!', 'Splice the mainbrace!', 'Dead men tell no tales!',
            'Fifteen men on a dead man\'s chest!', 'Hoist the colors!',
            'Weigh anchor!', 'Land ho!', 'By Blackbeard\'s ghost!',
            'Scuttle me bones!', 'Blast ye!', 'Thunder and tarnation!',
            'By the powers!', 'Sink me!', 'Heave ho!', 'Avast ye landlubbers!'
        ]
        
        # Expanded pirate endings
        self.endings = [
            ' arrr!', ' ye scurvy dog!', ' shiver me timbers!', 
            ' ahoy matey!', ' yo ho ho!', ' savvy?', ' me hearty!',
            ' ye landlubber!', ' avast!', ' by thunder!', ' ye scallywag!',
            ' or I\'ll make ye walk the plank!', ' ye bilge rat!',
            ' me bucko!', ' ye sea dog!', ' or ye\'ll be feeding the fishes!',
            ' blimey!', ' splice the mainbrace!', ' batten down the hatches!',
            ' ye barnacle-bottom!', ' me fine buccaneer!', ' savvy me meaning?',
            ' or face Davy Jones\' locker!', ' ye salty sea bass!'
        ]
    
    def transform(self, text: str) -> str:
        structure = analyze_text_structure(text)
        
        if structure['has_spacy']:
            return self._advanced_transform(structure)
        else:
            return self._basic_transform(text)
    
    def _fallback_transform(self, text: str) -> str:
        """Fallback to basic pirate transformation."""
        return self._basic_transform(text)
    
    def _advanced_transform(self, structure: Dict) -> str:
        """Use linguistic analysis for context-aware pirate transformation."""
        doc = structure['doc']
        transformed_tokens = []
        
        for token in doc:
            word = token.text
            lemma = token.lemma_.lower()
            pos = token.pos_
            
            # Transform based on part of speech and context
            if pos == 'PRON' and lemma in self.basic_replacements:
                transformed_tokens.append(self._apply_case(self.basic_replacements[lemma], word))
                
            elif pos in ['NOUN', 'VERB'] and lemma in self.pirate_vocab:
                transformed_tokens.append(self._apply_case(self.pirate_vocab[lemma], word))
                
            elif pos == 'VERB' and word.endswith('ing'):
                # Transform -ing verbs to -in'
                transformed_tokens.append(word[:-3] + "in'")
                
            elif token.ent_type_ == 'PERSON':
                # Add pirate titles to people
                if random.random() < 0.3:
                    titles = ['Captain', 'Admiral', 'Commodore', 'First Mate']
                    transformed_tokens.append(f"{random.choice(titles)} {word}")
                else:
                    transformed_tokens.append(word)
                    
            else:
                transformed_tokens.append(word)
            
            # Add space after token unless it's punctuation
            if not token.is_punct and token.i < len(doc) - 1:
                transformed_tokens.append(' ')
        
        result = ''.join(transformed_tokens)
        
        # Occasionally add pirate interjections
        if random.random() < 0.2:
            result = f"{random.choice(self.pirate_interjections)} {result}"
        
        if not any(result.endswith(punct) for punct in '.!?'):
            result += random.choice(self.endings)
        
        return result
    
    def _basic_transform(self, text: str) -> str:
        """Fallback transformation without spaCy."""
        # Basic word replacements
        for old, new in {**self.basic_replacements, **self.pirate_vocab}.items():
            text = re.sub(r'\b' + re.escape(old) + r'\b', new, text, flags=re.IGNORECASE)
        
        # Transform -ing endings
        text = re.sub(r'\b(\w+)ing\b', r"\1in'", text)
        
        if not any(text.endswith(punct) for punct in '.!?'):
            text += random.choice(self.endings)
        
        return text
    
    def _apply_case(self, replacement: str, original: str) -> str:
        """Apply the case pattern of original word to replacement."""
        if original.isupper():
            return replacement.upper()
        elif original.istitle():
            return replacement.title()
        else:
            return replacement

class AdvancedCorporateTransformer(AdvancedTransformer):
    """Sophisticated corporate speak transformation."""
    
    def __init__(self):
        super().__init__()
        # Massively expanded corporate vocabulary
        self.corporate_phrases = {
            # Original verbs
            'think': 'ideate', 'use': 'leverage', 'help': 'facilitate',
            'do': 'execute', 'make': 'generate', 'work': 'collaborate',
            'talk': 'interface', 'meet': 'sync up', 'plan': 'strategize',
            'fix': 'optimize', 'change': 'pivot', 'start': 'kick off',
            
            # Expanded action verbs
            'improve': 'enhance', 'increase': 'scale up', 'decrease': 'right-size',
            'finish': 'deliver', 'begin': 'initiate', 'end': 'sunset',
            'create': 'architect', 'build': 'operationalize', 'design': 'blueprint',
            'test': 'validate', 'check': 'audit', 'review': 'assess',
            'update': 'refresh', 'upgrade': 'modernize', 'replace': 'migrate',
            'remove': 'deprecate', 'add': 'onboard', 'include': 'incorporate',
            'exclude': 'decouple', 'combine': 'consolidate', 'separate': 'decouple',
            'organize': 'streamline', 'manage': 'orchestrate', 'control': 'govern',
            'lead': 'champion', 'follow': 'align with', 'support': 'enable',
            'decide': 'determine', 'choose': 'prioritize', 'agree': 'align',
            'disagree': 'pushback on', 'refuse': 'decline to proceed',
            'accept': 'green-light', 'reject': 'table', 'delay': 'defer',
            
            # Communication verbs
            'say': 'communicate', 'tell': 'inform', 'ask': 'inquire',
            'explain': 'clarify', 'describe': 'outline', 'show': 'demonstrate',
            'prove': 'validate', 'argue': 'advocate for', 'discuss': 'workshop',
            'debate': 'socialize', 'negotiate': 'align on terms',
            'present': 'share out', 'report': 'provide visibility',
            'announce': 'cascade', 'warn': 'flag', 'complain': 'escalate concerns',
            
            # Mental/cognitive verbs
            'understand': 'internalize', 'learn': 'upskill', 'remember': 'retain',
            'forget': 'lose context', 'know': 'have visibility into',
            'believe': 'buy into', 'doubt': 'have concerns around',
            'hope': 'anticipate', 'expect': 'forecast', 'predict': 'model',
            'worry': 'identify risks', 'fear': 'see challenges with',
            
            # Simple adjectives to corporate speak
            'good': 'optimal', 'bad': 'suboptimal', 'big': 'enterprise-scale',
            'small': 'granular', 'fast': 'agile', 'slow': 'deliberate',
            'easy': 'turnkey', 'hard': 'complex', 'simple': 'streamlined',
            'difficult': 'challenging', 'important': 'mission-critical',
            'urgent': 'high-priority', 'new': 'innovative', 'old': 'legacy',
            'broken': 'degraded', 'working': 'operational', 'ready': 'production-ready',
            
            # Common nouns
            'problem': 'pain point', 'solution': 'deliverable', 'idea': 'initiative',
            'goal': 'objective', 'result': 'outcome', 'effect': 'impact',
            'reason': 'driver', 'way': 'approach', 'method': 'methodology',
            'process': 'workflow', 'step': 'milestone', 'part': 'component',
            'piece': 'element', 'thing': 'deliverable', 'stuff': 'assets',
            'issue': 'blocker', 'mistake': 'learnings', 'error': 'gap',
            'failure': 'learning opportunity', 'success': 'win',
            'opportunity': 'value proposition', 'challenge': 'headwind',
            'risk': 'exposure', 'benefit': 'value-add', 'cost': 'investment',
            'price': 'cost structure', 'value': 'ROI', 'profit': 'margin'
        }
        
        # Massively expanded buzzwords and phrases
        self.buzzwords = [
            # Classic buzzwords
            'synergy', 'paradigm shift', 'low-hanging fruit', 'circle back',
            'deep dive', 'touch base', 'move the needle', 'scalable solution',
            'disruptive innovation', 'actionable insights', 'best practices',
            
            # Strategic buzzwords
            'value proposition', 'competitive advantage', 'market penetration',
            'customer-centric', 'data-driven', 'results-oriented', 'goal-oriented',
            'performance-driven', 'innovation-focused', 'agile methodology',
            'digital transformation', 'omnichannel approach', 'holistic view',
            'end-to-end solution', 'turnkey implementation', 'seamless integration',
            
            # Process buzzwords
            'streamlined workflow', 'optimized pipeline', 'efficient throughput',
            'lean operations', 'continuous improvement', 'iterative process',
            'scalable framework', 'robust architecture', 'flexible infrastructure',
            'sustainable growth', 'organic development', 'strategic alignment',
            
            # Team/people buzzwords
            'cross-functional collaboration', 'stakeholder engagement', 'team synergy',
            'cultural transformation', 'change management', 'talent acquisition',
            'skill development', 'capacity building', 'resource optimization',
            'human capital', 'intellectual property', 'knowledge transfer',
            
            # Technology buzzwords
            'cloud-first strategy', 'AI-powered solution', 'machine learning insights',
            'predictive analytics', 'real-time monitoring', 'automated workflows',
            'intelligent automation', 'digital ecosystem', 'platform integration',
            'API-driven architecture', 'microservices approach', 'DevOps culture',
            
            # Business buzzwords
            'revenue optimization', 'cost efficiency', 'profit maximization',
            'market leadership', 'customer satisfaction', 'brand loyalty',
            'stakeholder value', 'shareholder returns', 'sustainable practices',
            'corporate responsibility', 'ethical framework', 'compliance adherence'
        ]
        
        # Expanded corporate prefixes and conversation starters
        self.prefixes = [
            'As per our previous discussion,',
            'Moving forward,',
            'To circle back on this,',
            'From a strategic perspective,',
            'In terms of deliverables,',
            'At the end of the day,',
            'From a high-level view,',
            'To be completely transparent,',
            'In the spirit of continuous improvement,',
            'Leveraging our core competencies,',
            'To optimize our value proposition,',
            'With respect to our key stakeholders,',
            'Aligning with our strategic objectives,',
            'To ensure seamless integration,',
            'From an operational standpoint,',
            'In pursuit of operational excellence,',
            'To maximize stakeholder value,',
            'Considering our competitive landscape,',
            'To enhance our market position,',
            'With a customer-centric approach,',
            'To drive meaningful results,',
            'In terms of scalable solutions,',
            'To leverage synergistic opportunities,',
            'From a data-driven perspective,'
        ]
        
        # Expanded corporate endings and conversation closers
        self.endings = [
            ' Let\'s take this offline.',
            ' I\'ll ping you with an update.',
            ' Let\'s schedule a follow-up.',
            ' This aligns with our core values.',
            ' Let\'s put a pin in this.',
            ' We should circle back on this.',
            ' I\'ll loop you in on next steps.',
            ' Let\'s touch base early next week.',
            ' This should move the needle.',
            ' We can optimize this going forward.',
            ' Let\'s leverage this opportunity.',
            ' This is a real game-changer.',
            ' We need to think outside the box.',
            ' Let\'s drill down on the details.',
            ' This requires a paradigm shift.',
            ' We should streamline this process.',
            ' Let\'s ideate some solutions.',
            ' This will scale our impact.',
            ' We need to pivot our approach.',
            ' Let\'s operationalize this strategy.',
            ' This delivers real value-add.',
            ' We should socialize this concept.',
            ' Let\'s align on the deliverables.',
            ' This enhances our competitive advantage.',
            ' We need to right-size our expectations.',
            ' Let\'s table this for now.',
            ' This requires stakeholder buy-in.',
            ' We should green-light this initiative.',
            ' Let\'s workshop this further.',
            ' This needs executive visibility.'
        ]
    
    def transform(self, text: str) -> str:
        structure = analyze_text_structure(text)
        
        if structure['has_spacy']:
            return self._advanced_transform(structure)
        else:
            return self._basic_transform(text)
    
    def _fallback_transform(self, text: str) -> str:
        """Fallback to basic corporate transformation."""
        return self._basic_transform(text)
    
    def _advanced_transform(self, structure: Dict) -> str:
        """Use NLP analysis for sophisticated corporate transformation."""
        doc = structure['doc']
        transformed_tokens = []
        
        # Add corporate prefix occasionally
        if random.random() < 0.4:
            result_prefix = f"{random.choice(self.prefixes)} "
        else:
            result_prefix = ""
        
        for token in doc:
            word = token.text
            lemma = token.lemma_.lower()
            pos = token.pos_
            
            # Transform verbs to corporate speak
            if pos == 'VERB' and lemma in self.corporate_phrases:
                transformed_tokens.append(self._apply_case(self.corporate_phrases[lemma], word))
                
            # Inject buzzwords occasionally for nouns
            elif pos == 'NOUN' and random.random() < 0.15:
                buzzword = random.choice(self.buzzwords)
                transformed_tokens.append(f"{buzzword}-driven {word}")
                
            # Make statements more passive/indirect
            elif lemma in ['will', 'must', 'need']:
                transformed_tokens.append('should ideally')
                
            else:
                transformed_tokens.append(word)
            
            # Add space after token unless it's punctuation
            if not token.is_punct and token.i < len(doc) - 1:
                transformed_tokens.append(' ')
        
        result = result_prefix + ''.join(transformed_tokens)
        
        if not any(result.endswith(punct) for punct in '.!?'):
            result += random.choice(self.endings)
        
        return result
    
    def _basic_transform(self, text: str) -> str:
        """Fallback transformation without spaCy."""
        # Add prefix
        if random.random() < 0.4:
            text = f"{random.choice(self.prefixes)} {text.lower()}"
        
        # Basic replacements
        for old, new in self.corporate_phrases.items():
            text = re.sub(r'\b' + re.escape(old) + r'\b', new, text, flags=re.IGNORECASE)
        
        if not any(text.endswith(punct) for punct in '.!?'):
            text += random.choice(self.endings)
        
        return text
    
    def _apply_case(self, replacement: str, original: str) -> str:
        """Apply the case pattern of original word to replacement."""
        if original.isupper():
            return replacement.upper()
        elif original.istitle():
            return replacement.title()
        else:
            return replacement

# Factory function to get transformers
def get_advanced_transformer(effect_name: str) -> Optional[AdvancedTransformer]:
    """Get an advanced transformer by name."""
    transformers = {
        'shakespeare': AdvancedShakespeareTransformer,
        'bardify': AdvancedShakespeareTransformer,
        'pirate': AdvancedPirateTransformer,
        'corporate': AdvancedCorporateTransformer,
        'scrum': AdvancedCorporateTransformer,
    }
    
    transformer_class = transformers.get(effect_name.lower())
    if transformer_class:
        return transformer_class()
    return None 