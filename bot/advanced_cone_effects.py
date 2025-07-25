#!/usr/bin/env python3
"""
Advanced Cone Effects with Massive Vocabulary and Intelligent Transformations
Handles typos, variations, and transforms entire sentences aggressively
"""

import re
import random
import spacy
from typing import Dict, List, Tuple, Optional

class AdvancedConeEffects:
    def __init__(self):
        """Initialize with spaCy model for advanced text processing"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.spacy_available = True
        except OSError:
            print("spaCy model not available, using basic transformations")
            self.nlp = None
            self.spacy_available = False
    
    def normalize_word(self, word: str) -> str:
        """Normalize word variations (lmaoooo -> lmao, sooooo -> so)"""
        # Remove excessive repeated characters (keep max 2)
        normalized = re.sub(r'(.)\1{2,}', r'\1\1', word.lower())
        return normalized
    
    def apply_slayspeak(self, text: str) -> str:
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

    def apply_brainrot(self, text: str) -> str:
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

    def apply_scrum(self, text: str) -> str:
        """Agile scrum master jargon transformation - MAXIMUM CORPORATE AGILE BS"""
        
        # Inspired by Anthony Sistilli's content - pure agile buzzword hell
        replacements = {
            # Basic actions -> corporate agile speak
            r'\b(do|doing|make|making|work|working)\b': [
                'deliver value', 'execute against', 'operationalize', 'action this',
                'move the needle on', 'drive outcomes for', 'iterate on'
            ],
            r'\b(fix|fixing|solve|solving)\b': [
                'remediate', 'optimize', 'address the pain points of', 'unblock',
                'course-correct', 'pivot on', 'right-size'
            ],
            r'\b(plan|planning|organize)\b': [
                'roadmap', 'strategize around', 'align on', 'socialize the approach for',
                'get alignment on', 'create visibility into'
            ],
            r'\b(talk|talking|discuss|discussing)\b': [
                'circle back on', 'sync on', 'align on', 'socialize',
                'workshop together', 'ideate around', 'jam on'
            ],
            r'\b(meet|meeting)\b': [
                'sync', 'standup', 'retrospective', 'planning session',
                'alignment meeting', 'working session', 'ceremony'
            ],
            
            # Time and urgency
            r'\b(now|today|immediately|soon)\b': [
                'this sprint', 'in the current iteration', 'this cycle',
                'within the sprint boundary', 'in this timebox'
            ],
            r'\b(later|eventually|someday)\b': [
                'future iteration', 'next sprint', 'in the backlog',
                'post-MVP', 'in a future release', 'parking lot item'
            ],
            r'\b(quick|quickly|fast|urgent)\b': [
                'time-boxed', 'sprint-scoped', 'MVP approach',
                'lean and mean', 'agile delivery', 'iterative approach'
            ],
            r'\b(deadline|due date)\b': [
                'sprint commitment', 'milestone', 'delivery target',
                'sprint goal', 'iteration boundary'
            ],
            
            # People and roles
            r'\b(person|people|someone|team|group)\b': [
                'stakeholder', 'team member', 'scrum team', 'squad',
                'delivery team', 'cross-functional team'
            ],
            r'\b(boss|manager|leader)\b': [
                'product owner', 'scrum master', 'delivery lead',
                'squad lead', 'chapter lead'
            ],
            r'\b(user|customer|client)\b': [
                'end user', 'stakeholder', 'persona', 'user segment',
                'customer journey touchpoint'
            ],
            
            # Work and tasks
            r'\b(task|job|work|thing)\b': [
                'user story', 'epic', 'deliverable', 'backlog item',
                'sprint commitment', 'acceptance criteria'
            ],
            r'\b(goal|target|objective)\b': [
                'sprint goal', 'OKR', 'success metric', 'KPI',
                'outcome', 'business value'
            ],
            r'\b(problem|issue|bug)\b': [
                'pain point', 'blocker', 'impediment', 'technical debt',
                'risk', 'dependency'
            ],
            
            # Quality and improvement
            r'\b(good|great|perfect|excellent)\b': [
                'value-driving', 'optimized', 'right-sized', 'scalable',
                'maintainable', 'sustainable'
            ],
            r'\b(bad|wrong|terrible)\b': [
                'sub-optimal', 'technical debt', 'anti-pattern',
                'blockers', 'impediments to velocity'
            ],
            r'\b(better|improve|upgrade|enhance)\b': [
                'optimize', 'right-size', 'scale up', 'mature',
                'uplevel', 'enhance velocity'
            ],
            
            # Communication and process
            r'\b(tell|inform|update|report)\b': [
                'socialize', 'provide visibility into', 'communicate out',
                'cascade the message', 'align stakeholders on'
            ],
            r'\b(learn|understand|know)\b': [
                'gain insights into', 'develop domain expertise in',
                'build knowledge capital around'
            ],
            r'\b(decide|choose|pick)\b': [
                'align on', 'prioritize', 'roadmap', 'sequence',
                'make data-driven decisions about'
            ],
            
            # Regular chat words -> corporate speak
            r'\b(yes|yeah|ok|okay|sure)\b': [
                'absolutely, let\'s action that', 'that aligns with our objectives',
                'that\'s value-driving', 'let\'s move forward on that'
            ],
            r'\b(no|nope|can\'t)\b': [
                'that\'s not in scope for this sprint', 'let\'s parking lot that',
                'that\'s a dependency we need to unblock first'
            ],
            r'\b(maybe|possibly|perhaps)\b': [
                'let\'s validate that assumption', 'we should spike on that',
                'that needs to be socialized with stakeholders'
            ],
            
            # Common casual expressions
            r'\b(going|going to)\b': ['delivering on', 'executing against', 'operationalizing'],
            r'\b(have|has|had)\b': ['own', 'maintain accountability for', 'drive'],
            r'\b(get|getting)\b': ['secure', 'obtain buy-in for', 'action'],
            r'\b(put|putting)\b': ['position', 'align', 'operationalize'],
        }
        
        result = text
        
        # Apply replacements
        for pattern, options in replacements.items():
            def replace_func(match):
                return random.choice(options)
            result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
        
        # Add random corporate agile interjections
        interjections = [
            'from a delivery perspective', 'thinking about this strategically',
            'to align on this', 'from a velocity standpoint', 'looking at our OKRs',
            'considering our sprint goals', 'from a stakeholder perspective',
            'thinking about our MVP', 'from a roadmap perspective',
            'considering our technical debt', 'looking at our capacity',
            'from a cross-functional lens', 'thinking about scalability'
        ]
        
        # Add jargon to sentences
        sentences = re.split(r'[.!?]+', result)
        transformed_sentences = []
        
        for sentence in sentences:
            if sentence.strip():
                # Add corporate interjection
                if random.random() < 0.4:
                    sentence = f"{random.choice(interjections)}, {sentence.strip()}"
                
                transformed_sentences.append(sentence)
        
        result = '. '.join(transformed_sentences)
        
        # Add corporate endings
        endings = [
            'Let\'s circle back on this offline',
            'I\'ll action this and provide visibility',
            'Let\'s align stakeholders on this',
            'This drives significant business value',
            'Let\'s iterate on this in our next sprint',
            'We should socialize this with the broader team'
        ]
        
        if random.random() < 0.6:
            result += f'. {random.choice(endings)}'
        
        return result

    def apply_linkedin(self, text: str) -> str:
        """LinkedIn influencer transformation - MAXIMUM CRINGE PROFESSIONAL"""
        
        # Exaggerated LinkedIn humble-bragging and AI-generated soulless content
        replacements = {
            # Achievement humble-bragging
            r'\b(did|made|created|built|finished)\b': [
                'I\'m humbled to share that I delivered 💼',
                'Thrilled to announce that I spearheaded 🚀',
                'Excited to share that I pioneered 💡',
                'Proud to have architected ⚡',
                'Grateful for the opportunity to execute 🎯'
            ],
            r'\b(learned|discovered|found out)\b': [
                'gained invaluable insights into 💡',
                'had the privilege of discovering 🔍',
                'was fortunate enough to uncover 💎',
                'had the honor of learning about 📚',
                'was blessed to gain expertise in 🧠'
            ],
            r'\b(succeeded|won|achieved)\b': [
                'exceeded expectations by delivering 📈',
                'I\'m humbled to share we achieved 🏆',
                'thrilled to announce we surpassed 🎉',
                'grateful to have accomplished 💯',
                'honored to have driven 🚀'
            ],
            
            # Emotional amplification
            r'\b(happy|glad|pleased)\b': [
                'absolutely thrilled 😊', 'incredibly grateful 🙏',
                'beyond excited 🎉', 'deeply honored 💫',
                'tremendously blessed ✨'
            ],
            r'\b(proud|satisfied|content)\b': [
                'immensely proud 💪', 'deeply humbled 🙏',
                'incredibly fulfilled 💯', 'profoundly grateful 🌟',
                'tremendously honored 👑'
            ],
            r'\b(excited|enthusiastic|eager)\b': [
                'absolutely energized ⚡', 'incredibly passionate 🔥',
                'deeply inspired 💫', 'tremendously motivated 🚀',
                'profoundly excited 🎯'
            ],
            
            # Work and collaboration
            r'\b(worked|collaborated|partnered)\b': [
                'had the privilege of collaborating 🤝',
                'was honored to partner 💼',
                'had the opportunity to work alongside 👥',
                'was blessed to team up 🌟',
                'got to co-create magic ✨'
            ],
            r'\b(team|group|colleagues)\b': [
                'incredible dream team 👥', 'amazing squad 🌟',
                'phenomenal collective 💫', 'outstanding crew ⚡',
                'inspiring group of changemakers 🚀'
            ],
            r'\b(helped|assisted|supported)\b': [
                'had the honor of empowering 💪',
                'was privileged to enable 🔧',
                'got to uplift and support 🙌',
                'had the chance to champion 🏆',
                'was able to guide and mentor 📈'
            ],
            
            # Business and innovation
            r'\b(innovative|creative|new|unique)\b': [
                'groundbreaking 🚀', 'revolutionary 💡',
                'game-changing ⚡', 'disruptive 💥',
                'paradigm-shifting 🌟'
            ],
            r'\b(solution|answer|fix)\b': [
                'breakthrough solution 💡', 'innovative approach 🚀',
                'transformative strategy ⚡', 'revolutionary framework 🎯',
                'cutting-edge methodology 💫'
            ],
            r'\b(growth|progress|improvement)\b': [
                'exponential growth 📈', 'transformational progress 🚀',
                'unprecedented improvement 💯', 'remarkable evolution ⚡',
                'phenomenal advancement 🌟'
            ],
            
            # Networking and connections
            r'\b(people|person|everyone)\b': [
                'amazing connections 🤝', 'inspiring individuals 🌟',
                'phenomenal human beings 💫', 'incredible thought leaders 🧠',
                'outstanding professionals 👔'
            ],
            r'\b(met|connected|networked)\b': [
                'had the privilege of connecting 🤝',
                'was honored to network 💼',
                'got to build meaningful relationships 🌟',
                'had amazing conversations 💬',
                'forged incredible partnerships ✨'
            ],
            
            # Time and opportunity
            r'\b(opportunity|chance|experience)\b': [
                'incredible opportunity 🌟', 'life-changing experience 💫',
                'transformational journey 🚀', 'amazing privilege 🙏',
                'phenomenal adventure ⚡'
            ],
            r'\b(journey|path|career)\b': [
                'incredible journey 🌟', 'transformational path 🚀',
                'amazing adventure 💫', 'phenomenal voyage ⚡',
                'inspiring odyssey 🎯'
            ],
            
            # Gratitude and humility (fake)
            r'\b(thank|thanks|grateful)\b': [
                'incredibly grateful 🙏', 'deeply thankful 💫',
                'immensely appreciative 🌟', 'profoundly blessed ✨',
                'tremendously honored 👑'
            ],
            
            # Regular expressions -> LinkedIn speak
            r'\b(good|great|nice|cool)\b': [
                'absolutely phenomenal 🌟', 'incredibly inspiring 💫',
                'tremendously impactful 🚀', 'deeply meaningful ⚡',
                'profoundly transformative 💡'
            ],
            r'\b(yes|yeah|agreed|true)\b': [
                'Absolutely agree! 💯', 'This resonates deeply! 🎯',
                'So much truth here! ✨', 'Couldn\'t agree more! 🙌',
                'This hits different! 🚀'
            ],
        }
        
        result = text
        
        # Apply replacements
        for pattern, options in replacements.items():
            def replace_func(match):
                return random.choice(options)
            result = re.sub(pattern, replace_func, result, flags=re.IGNORECASE)
        
        # Add LinkedIn-style intros and connectors
        intros = [
            'I\'m thrilled to share that',
            'Excited to announce that',
            'Grateful to share that',
            'Humbled to report that',
            'Honored to share that',
            'Blessed to announce that'
        ]
        
        connectors = [
            'Building on this momentum 🚀',
            'Looking forward to what\'s next 💫',
            'Excited for the journey ahead ⚡',
            'Grateful for these opportunities 🙏',
            'Inspired by what\'s possible 💡'
        ]
        
        # Transform sentences with LinkedIn structure
        sentences = re.split(r'[.!?]+', result)
        if sentences and sentences[0].strip():
            # Add intro to first sentence
            if random.random() < 0.5:
                sentences[0] = f"{random.choice(intros)} {sentences[0].strip()}"
        
        # Add engagement hooks
        engagement_hooks = [
            'Thoughts? 💭', 'What\'s your experience? 🤔',
            'Would love to hear your perspective! 💬',
            'How has this impacted your journey? 🚀',
            'What are your thoughts on this? 💡',
            'Anyone else experiencing this? 🙋‍♂️'
        ]
        
        result = '. '.join([s for s in sentences if s.strip()])
        
        # Add connector and engagement hook
        if random.random() < 0.6:
            result += f'. {random.choice(connectors)}'
        
        if random.random() < 0.7:
            result += f' {random.choice(engagement_hooks)}'
        
        # Add hashtag explosion
        hashtags = [
            '#Leadership #Growth #Innovation',
            '#Inspiration #Success #Mindset',
            '#Networking #Professional #Career',
            '#Grateful #Blessed #Opportunity',
            '#Teamwork #Collaboration #Excellence'
        ]
        
        if random.random() < 0.5:
            result += f'\n\n{random.choice(hashtags)}'
        
        return result 

    def apply_crisis(self, text: str) -> str:
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
            r'\b(sad|depressed|upset|unhappy)\b': [
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

    def apply_canadian(self, text: str) -> str:
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

    def apply_vsauce(self, text: str) -> str:
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

    def apply_british(self, text: str) -> str:
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

    def apply_oni(self, text: str) -> str:
        """Oni censor transformation - RANDOM AGGRESSIVE CENSORING"""
        
        # Words to potentially redact (mix of innocent and slightly questionable)
        redaction_targets = [
            # Innocent words that sound suspicious
            r'\b(analysis|analyze)\b', r'\b(basement|cellar)\b', r'\b(contact|contacts)\b',
            r'\b(private|personal)\b', r'\b(secret|secrets)\b', r'\b(hidden|hiding)\b',
            r'\b(meeting|meetings)\b', r'\b(plan|plans|planning)\b', r'\b(strategy|tactics)\b',
            r'\b(group|groups)\b', r'\b(organization|org)\b', r'\b(network|networking)\b',
            r'\b(data|information)\b', r'\b(research|studying)\b', r'\b(investigation)\b',
            r'\b(location|address)\b', r'\b(identity|identities)\b', r'\b(profile|profiles)\b',
            
            # Normal words that become suspicious when censored
            r'\b(government|authority)\b', r'\b(official|officials)\b', r'\b(system|systems)\b',
            r'\b(control|controlling)\b', r'\b(power|powers)\b', r'\b(influence|influences)\b',
            r'\b(money|cash|funds)\b', r'\b(business|company)\b', r'\b(project|projects)\b',
            r'\b(operation|operations)\b', r'\b(mission|missions)\b', r'\b(target|targets)\b',
            
            # Everyday words that seem weird when censored
            r'\b(party|parties)\b', r'\b(friend|friends)\b', r'\b(family|families)\b',
            r'\b(house|home)\b', r'\b(school|college)\b', r'\b(work|job)\b',
            r'\b(phone|computer)\b', r'\b(internet|online)\b', r'\b(social|media)\b',
            r'\b(message|messages)\b', r'\b(email|emails)\b', r'\b(call|calls)\b',
            
            # Random common words
            r'\b(kitchen|bedroom)\b', r'\b(garden|yard)\b', r'\b(car|vehicle)\b',
            r'\b(book|books)\b', r'\b(music|songs)\b', r'\b(movie|movies)\b',
            r'\b(game|games)\b', r'\b(sport|sports)\b', r'\b(food|eating)\b',
            r'\b(water|drink)\b', r'\b(clothes|clothing)\b', r'\b(money|payment)\b'
        ]
        
        # Discord spoiler words (words that get ||censored||)
        spoiler_targets = [
            r'\b(important|significant)\b', r'\b(special|unique)\b', r'\b(interesting|fascinating)\b',
            r'\b(dangerous|risky)\b', r'\b(suspicious|questionable)\b', r'\b(confidential|classified)\b',
            r'\b(sensitive|delicate)\b', r'\b(controversial|disputed)\b', r'\b(illegal|unlawful)\b',
            r'\b(evidence|proof)\b', r'\b(documents|files)\b', r'\b(photos|pictures)\b',
            r'\b(video|footage)\b', r'\b(recording|audio)\b', r'\b(witness|witnesses)\b',
            r'\b(source|sources)\b', r'\b(insider|informant)\b', r'\b(leak|leaked)\b'
        ]
        
        result = text
        
        # Randomly redact words completely
        for pattern in redaction_targets:
            if random.random() < 0.9:  # 40% chance to redact each pattern
                def redact_func(match):
                    redactions = ['[REDACTED]', '[CENSORED]', '[CLASSIFIED]', '[EXPUNGED]', 
                                 '[DATA EXPUNGED]', '[REMOVED]', '[■■■■■]', '[BLOCKED]']
                    return random.choice(redactions)
                result = re.sub(pattern, redact_func, result, flags=re.IGNORECASE)
        
        # Add Discord spoiler formatting to some words
        for pattern in spoiler_targets:
            if random.random() < 0.6:  # 50% chance to spoiler each pattern
                def spoiler_func(match):
                    return f"||{match.group()}||"
                result = re.sub(pattern, spoiler_func, result, flags=re.IGNORECASE)
        
        # Randomly censor words (both long words and random words)
        words = result.split()
        censored_words = []
        
        for word in words:
            # Clean word for length check (remove punctuation)
            clean_word = re.sub(r'[^\w]', '', word)
            
            # Skip very short words and common words
            if len(clean_word) <= 2 or clean_word.lower() in ['the', 'and', 'or', 'is', 'a', 'an', 'to', 'of', 'in', 'for', 'on', 'at', 'by']:
                censored_words.append(word)
                continue
            
            # Censor longer words (higher chance)
            if len(clean_word) > 6 and random.random() < 0.4:
                # Censor middle part of word
                start = clean_word[:2]
                end = clean_word[-2:]
                middle_length = len(clean_word) - 4
                censored = f"{start}{'█' * middle_length}{end}"
                
                # Preserve punctuation
                punctuation = re.findall(r'[^\w]', word)
                if punctuation:
                    censored += ''.join(punctuation)
                
                censored_words.append(censored)
            # Censor random shorter words too
            elif len(clean_word) >= 3 and random.random() < 0.25:
                # Different censoring styles for random words
                censor_style = random.choice(['full_block', 'partial_block', 'spoiler', 'redacted'])
                
                if censor_style == 'full_block':
                    censored = '█' * len(clean_word)
                elif censor_style == 'partial_block':
                    if len(clean_word) >= 4:
                        start = clean_word[0]
                        end = clean_word[-1]
                        middle_length = len(clean_word) - 2
                        censored = f"{start}{'█' * middle_length}{end}"
                    else:
                        censored = '█' * len(clean_word)
                elif censor_style == 'spoiler':
                    censored = f"||{clean_word}||"
                else:  # redacted
                    redaction_types = ['[REDACTED]', '[CENSORED]', '[BLOCKED]', '[■■■]', '[***]']
                    censored = random.choice(redaction_types)
                
                # Preserve punctuation for non-redacted styles
                if censor_style != 'redacted':
                    punctuation = re.findall(r'[^\w]', word)
                    if punctuation:
                        censored += ''.join(punctuation)
                
                censored_words.append(censored)
            else:
                censored_words.append(word)
        
        result = ' '.join(censored_words)
        
        # Randomly insert [CENSORED] in middle of sentences (more aggressive)
        sentences = result.split('.')
        processed_sentences = []
        
        for sentence in sentences:
            if sentence.strip() and random.random() < 0.5:  # Increased from 30% to 50%
                words = sentence.split()
                if len(words) > 3:
                    # Insert random censorship (sometimes multiple)
                    num_censors = random.choice([1, 1, 1, 2])  # Mostly 1, sometimes 2
                    for _ in range(num_censors):
                        if len(words) > 3:
                            pos = random.randint(1, len(words) - 1)
                            censors = [
                                '[REDACTED]', '[CENSORED BY MODERATOR]', '[REMOVED FOR SAFETY]', 
                                '[CONTENT VIOLATION]', '[INAPPROPRIATE]', '[BLOCKED]',
                                '[DATA EXPUNGED]', '[CLASSIFIED]', '[■■■■■]', '[ACCESS DENIED]',
                                '[REMOVED BY ONI]', '[SECURITY BREACH]'
                            ]
                            words.insert(pos, random.choice(censors))
                    sentence = ' '.join(words)
            
            processed_sentences.append(sentence)
        
        result = '.'.join(processed_sentences)
        
        # Add warning at end sometimes
        warnings = [
            '[This message has been processed by content moderation]',
            '[Some content removed for community safety]',
            '[Message filtered for inappropriate content]',
            '[Content reviewed and modified]',
            '[Automated content screening applied]',
            '[Censored as per Office of Naval Intelligence guidelines]'
        ]
        
        if random.random() < 0.4:
            result += f' {random.choice(warnings)}'
        
        return result

    def apply_dyslexia(self, text: str) -> str:
        """Advanced dyslexia transformation using NLP libraries for dynamic, realistic effects"""
        
        # Character-level visual confusion mappings (based on actual letter shape similarities)
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
        
        # Apply transformations with different probability layers
        
        # 1. CHARACTER-LEVEL VISUAL CONFUSION (works on any text)
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
        
        # 2. PHONETIC PATTERN SUBSTITUTIONS (probability-based)
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
        
        # 3. SYLLABLE AND WORD-LEVEL SCRAMBLING (using spaCy if available)
        if self.spacy_available:
            doc = self.nlp(result)
            words = []
            for token in doc:
                if token.is_alpha and len(token.text) > 3:
                    scrambled = self._advanced_word_scramble(token.text, token.pos_)
                    words.append(scrambled)
                else:
                    words.append(token.text_with_ws)
            result = ''.join(words).strip()
        else:
            # Fallback: simple word scrambling
            words = result.split()
            for i, word in enumerate(words):
                if len(word) > 4 and word.isalpha() and random.random() < 0.2:
                    words[i] = self._simple_scramble(word)
            result = ' '.join(words)
        
        # 4. READING PATTERN SIMULATION (attention/focus issues)
        if random.random() < 0.3:  # 30% chance to apply reading disruption
            result = self._simulate_reading_disruption(result)
        
        # 5. WORKING MEMORY ERRORS (letter additions/omissions)
        result = self._apply_memory_errors(result)
        
        # 6. SEQUENCE REVERSAL (small chunks occasionally get flipped)
        if random.random() < 0.25:  # 25% chance
            result = self._apply_sequence_reversals(result)
        
        return result
    
    def _advanced_word_scramble(self, word: str, pos: str) -> str:
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
    
    def _simple_scramble(self, word: str) -> str:
        """Simple scrambling for when spaCy isn't available"""
        if len(word) <= 3:
            return word
        
        # Various scrambling patterns
        patterns = [
            lambda w: w[0] + ''.join(random.sample(w[1:-1], len(w[1:-1]))) + w[-1],  # Scramble middle
            lambda w: w[1] + w[0] + w[2:] if len(w) > 2 else w,  # Swap first two
            lambda w: w[:-2] + w[-1] + w[-2] if len(w) > 3 else w,  # Swap last two
        ]
        
        return random.choice(patterns)(word)
    
    def _simulate_reading_disruption(self, text: str) -> str:
        """Simulate attention/focus issues that cause reading disruption"""
        words = text.split()
        if len(words) < 3:
            return text
        
        # Simulate jumping around while reading (word order confusion)
        disruption_types = [
            self._swap_adjacent_words,
            self._repeat_word,
            self._skip_word
        ]
        
        disruption = random.choice(disruption_types)
        return disruption(words)
    
    def _swap_adjacent_words(self, words: list) -> str:
        """Swap two adjacent words"""
        if len(words) < 2:
            return ' '.join(words)
        
        idx = random.randint(0, len(words) - 2)
        words[idx], words[idx + 1] = words[idx + 1], words[idx]
        return ' '.join(words)
    
    def _repeat_word(self, words: list) -> str:
        """Repeat a word (working memory loop)"""
        if not words:
            return ' '.join(words)
        
        idx = random.randint(0, len(words) - 1)
        repeat_patterns = [
            f"{words[idx]} {words[idx]}",  # Simple repeat
            f"{words[idx][:2]}-{words[idx]}",  # Stutter pattern
        ]
        words[idx] = random.choice(repeat_patterns)
        return ' '.join(words)
    
    def _skip_word(self, words: list) -> str:
        """Skip a word (attention lapse)"""
        if len(words) <= 2:
            return ' '.join(words)
        
        # Skip a non-critical word (not first or last)
        idx = random.randint(1, len(words) - 2)
        words.pop(idx)
        return ' '.join(words)
    
    def _apply_memory_errors(self, text: str) -> str:
        """Apply working memory errors (letter drops/additions)"""
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
    
    def _apply_sequence_reversals(self, text: str) -> str:
        """Apply small sequence reversals (2-3 character flips)"""
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

# Helper function to apply effects
def apply_cone_effect(text: str, effect: str) -> str:
    """Apply the specified cone effect to text"""
    processor = AdvancedConeEffects()
    
    effect_map = {
        'slayspeak': processor.apply_slayspeak,
        'valley': processor.apply_slayspeak,  # alias
        'brainrot': processor.apply_brainrot,
        'genz': processor.apply_brainrot,  # alias
        'scrum': processor.apply_scrum,
        'corporate': processor.apply_scrum,  # alias (keeping old corporate)
        'linkedin': processor.apply_linkedin,
        'emoji': processor.apply_linkedin,  # alias
        'crisis': processor.apply_crisis,
        'existential': processor.apply_crisis,  # alias
        'canadian': processor.apply_canadian,
        'polite': processor.apply_canadian,  # alias
        'vsauce': processor.apply_vsauce,
        'conspiracy': processor.apply_vsauce,  # alias
        'bri': processor.apply_british,
        'british': processor.apply_british,  # alias
        'oni': processor.apply_oni,
        'censor': processor.apply_oni,  # alias
        'dyslexia': processor.apply_dyslexia,
        'dickslexia': processor.apply_dyslexia,  # alias
        'ro': processor.apply_dyslexia  # alias
    }
    
    if effect.lower() in effect_map:
        return effect_map[effect.lower()](text)
    else:
        return text  # Return unchanged if effect not found 