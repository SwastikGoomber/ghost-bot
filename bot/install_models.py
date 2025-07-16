#!/usr/bin/env python3
"""
Install NLP models and data for advanced text transformations.
This script is run during deployment to download necessary language models.
"""

import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_spacy_model():
    """Install spaCy English model."""
    try:
        logger.info("Installing spaCy English model...")
        # Use the small model for better performance on free tier
        result = subprocess.run([
            sys.executable, "-m", "spacy", "download", "en_core_web_sm"
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            logger.info("✅ spaCy model installed successfully")
            return True
        else:
            logger.warning(f"spaCy model installation failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning("spaCy model installation timed out")
        return False
    except Exception as e:
        logger.warning(f"Error installing spaCy model: {e}")
        return False

def install_nltk_data():
    """Install required NLTK data."""
    try:
        logger.info("Installing NLTK data...")
        import nltk
        
        # Download required NLTK data quietly
        nltk.download('wordnet', quiet=True)
        nltk.download('omw-1.4', quiet=True)  # For multilingual WordNet
        nltk.download('punkt', quiet=True)    # For tokenization
        
        logger.info("✅ NLTK data installed successfully")
        return True
        
    except Exception as e:
        logger.warning(f"Error installing NLTK data: {e}")
        return False

def main():
    """Install all required models and data."""
    logger.info("🚀 Installing NLP models for advanced cone transformations...")
    
    spacy_success = install_spacy_model()
    nltk_success = install_nltk_data()
    
    if spacy_success and nltk_success:
        logger.info("🎉 All models installed successfully!")
        return 0
    elif nltk_success:
        logger.info("⚠️ NLTK installed, spaCy failed - will use basic transformations")
        return 0
    else:
        logger.warning("❌ Model installation had issues - will fallback to basic transformations")
        return 0  # Don't fail deployment, just use basic transformations

if __name__ == "__main__":
    sys.exit(main()) 