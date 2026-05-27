"""
Oni Censor coning effect.
"""

import re
import random


def apply_oni(text: str) -> str:
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
