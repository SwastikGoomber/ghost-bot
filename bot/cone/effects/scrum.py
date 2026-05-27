"""
Agile Scrum Master jargon coning effect.
"""

import re
import random


def apply_scrum(text: str) -> str:
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
