"""
LinkedIn cringe coning effect.
"""

import re
import random


def apply_linkedin(text: str) -> str:
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
