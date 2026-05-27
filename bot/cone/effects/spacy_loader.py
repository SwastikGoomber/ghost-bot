"""
spaCy model loader and dynamic downloader singleton.
Ensures en_core_web_md is programmatically available for NLP transformations.
"""

from __future__ import annotations

import logging
import spacy
from typing import Optional

logger = logging.getLogger(__name__)


class SpacyLoader:
    def __init__(self):
        """Initialize and automatically manage the en_core_web_md model startup lifecycle."""
        self.nlp: Optional[spacy.Language] = None
        self.spacy_available = False
        
        # Concept anchors (loaded once if medium model vector size > 0)
        self.concept_home = None
        self.concept_money = None
        self.concept_vehicle = None
        self.concept_food = None
        self.concept_fight = None
        self.concept_friend = None
        self.concept_city = None
        
        try:
            # 1. Try to load the medium model directly
            self.nlp = spacy.load("en_core_web_md")
            self.spacy_available = True
        except OSError:
            # 2. Automatically download the medium model
            try:
                logger.info("spaCy model 'en_core_web_md' not found. Attempting automatic download...")
                from spacy.cli import download
                download("en_core_web_md")
                self.nlp = spacy.load("en_core_web_md")
                self.spacy_available = True
                logger.info("spaCy model 'en_core_web_md' downloaded and loaded successfully.")
            except Exception as e:
                logger.warning(
                    "spaCy model 'en_core_web_md' is not available and automatic download failed: %s. "
                    "Advanced cone effects will be disabled.", e
                )
                self.nlp = None
                self.spacy_available = False
        
        # Load concept anchors only if the spaCy model has active vectors
        if self.spacy_available and self.nlp is not None and self.nlp.vocab.vectors.size > 0:
            self.concept_home = self.nlp("home shelter house place building apartment quarters")
            self.concept_money = self.nlp("money gold cash wealth coin bill finance")
            self.concept_vehicle = self.nlp("car vehicle truck train transportation chariot carriage")
            self.concept_food = self.nlp("food eat dinner meal meat grub victuals")
            self.concept_fight = self.nlp("fight attack bonk smash violence weapon hit")
            self.concept_friend = self.nlp("friend buddy bro shipmate companion tribe-mate")
            self.concept_city = self.nlp("city town village settlement street area block")


# Global module-level singleton instance
_loader_singleton = SpacyLoader()


def get_nlp() -> Optional[spacy.Language]:
    """Returns the loaded spaCy Language model if available."""
    return _loader_singleton.nlp


def is_spacy_available() -> bool:
    """Returns True if the spaCy Language model loaded successfully."""
    return _loader_singleton.spacy_available


def get_concept_anchors() -> dict[str, Optional[object]]:
    """Returns a dictionary of pre-loaded semantic concept anchors."""
    return {
        "home": _loader_singleton.concept_home,
        "money": _loader_singleton.concept_money,
        "vehicle": _loader_singleton.concept_vehicle,
        "food": _loader_singleton.concept_food,
        "fight": _loader_singleton.concept_fight,
        "friend": _loader_singleton.concept_friend,
        "city": _loader_singleton.concept_city,
    }
