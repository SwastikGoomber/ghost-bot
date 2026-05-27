"""
Caveman (unga/bunga) coning effect.
Contains both the advanced vector-similarity logic and the basic fallback regex translator.
"""

import re
import random
from typing import Optional
from bot.cone.effects.spacy_loader import is_spacy_available, get_nlp, get_concept_anchors


def apply_caveman(text: str) -> Optional[str]:
    """Advanced vector-similarity and POS-tagging Caveman transformation.
    Returns None if spaCy is not available to trigger fallback.
    """
    if not is_spacy_available():
        return None
    
    nlp = get_nlp()
    if nlp is None:
        return None
        
    doc = nlp(text)
    words = []
    
    anchors = get_concept_anchors()
    concept_home = anchors.get("home")
    concept_money = anchors.get("money")
    concept_vehicle = anchors.get("vehicle")
    concept_food = anchors.get("food")
    concept_fight = anchors.get("fight")
    concept_friend = anchors.get("friend")
    concept_city = anchors.get("city")
    
    for token in doc:
        # 1. Strip grammatical glue (determiners, auxiliary verbs, conjunctions, relative pronouns)
        if token.pos_ in ("AUX", "DET", "CCONJ", "SCONJ"):
            continue
        # Strip non-spatial prepositions
        if token.pos_ == "ADP" and token.text.lower() not in ("in", "on", "at", "under", "above"):
            continue
            
        # 2. Pronoun Accusative Flattening
        if token.pos_ == "PRON":
            lemma = token.lemma_.lower()
            if lemma in ("i", "me", "my", "myself"):
                words.append("me")
            elif lemma in ("we", "us", "our", "ourselves"):
                words.append("us")
            elif lemma in ("he", "him", "his", "she", "her", "hers", "they", "them", "their", "theirs"):
                words.append("them")
            else:
                words.append("you")
            continue
            
        # 3. Vector-Similarity Concept Replacements
        lemma = token.lemma_.lower()
        if concept_home is not None and token.has_vector and not token.is_stop:
            if token.pos_ in ("NOUN", "VERB", "ADJ"):
                try:
                    from bot.utils.config import get_config
                    threshold = get_config().cone.caveman_similarity_threshold
                except Exception:
                    threshold = 0.7

                if token.similarity(concept_home) > threshold:
                    lemma = "cave"
                elif token.similarity(concept_money) > threshold:
                    lemma = "shiny rock"
                elif token.similarity(concept_vehicle) > threshold:
                    lemma = "rolling rock"
                elif token.similarity(concept_food) > threshold:
                    lemma = "grub"
                elif token.similarity(concept_fight) > threshold:
                    lemma = "bonk"
                elif token.similarity(concept_friend) > threshold:
                    lemma = "tribe-mate"
                elif token.similarity(concept_city) > threshold:
                    lemma = "tribe area"
                    
        # 4. Suffix Stripping on the resolved lemma
        lemma = re.sub(r"ly$", "", lemma)
        lemma = re.sub(r"ment$", "", lemma)
        lemma = re.sub(r"ness$", "", lemma)
        
        words.append(lemma)
        
    # Reconstruct text
    result = " ".join(words)
    result = re.sub(r"\s+", " ", result).strip()
    
    # 5. Add random caveman grunts
    sentences = re.split(r"([.!?]+)", result)
    transformed_sentences = []
    grunts = ["Unga!", "Bunga!", "Ooga!", "Bonk!", "Rock good!", "Me smash!"]
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i].strip()
        if not sentence:
            continue
        if random.random() < 0.35:
            sentence = f"{sentence} {random.choice(grunts)}"
        punctuation = sentences[i+1] if i+1 < len(sentences) else ""
        transformed_sentences.append(sentence + punctuation)
        
    result = " ".join(transformed_sentences)
    return result


def transform_caveman(text: str) -> str:
    """Basic fallback Caveman transformation using regex and pronoun-flattening."""
    # Upgraded basic fallback: pronoun flattening + basic grammatical glue stripping
    text = re.sub(r"\bI\b", "me", text)
    text = re.sub(r"\bmy\b", "me", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwe\b", "us", text, flags=re.IGNORECASE)
    text = re.sub(r"\bour\b", "us", text, flags=re.IGNORECASE)
    text = re.sub(r"\bhe\b", "him", text, flags=re.IGNORECASE)
    text = re.sub(r"\bshe\b", "her", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthey\b", "them", text, flags=re.IGNORECASE)
    
    # Strip basic linking verbs & articles
    glue = [r"\bam\b", r"\bis\b", r"\bare\b", r"\bthe\b", r"\ba\b", r"\ban\b"]
    for pattern in glue:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
        
    text = " ".join(text.split())
    text += random.choice([" Unga!", " Ooga!", " Bunga!", " Me smash!"])
    return text
