from typing import Dict, List, Tuple
import aiohttp
import sys
import os
import re
import traceback
import json
import base64
try:
    from config import (
        OPENROUTER_CHAT_KEY,
        OPENROUTER_SUMMARY_KEY,
        BOT_PERSONA,
        PLATFORM_SETTINGS,
        BOT_NAME,
        IDLE_MESSAGES,
        SLEEP_RESPONSES,
        ERROR_RESPONSES,
        CHAT_MODEL,
        VISION_MODEL,
        SUMMARY_MODEL,
        CONE_PERMISSIONS
    )
except Exception as e:
    print(f"Config Error: {e}")
    raise

import random
import re
import time
import re
from datetime import datetime, timedelta

# Import advanced transformations
try:
    from advanced_transformations import get_advanced_transformer
    ADVANCED_TRANSFORMATIONS_AVAILABLE = True
except ImportError:
    print("Advanced transformations not available, using basic fallback")
    ADVANCED_TRANSFORMATIONS_AVAILABLE = False

# Cone Text Transformation Functions
def transform_uwufy(text):
    """Transform text to uwu speak."""
    replacements = {
        'r': 'w', 'R': 'W', 'l': 'w', 'L': 'W',
        'no': 'nyo', 'No': 'Nyo', 'NO': 'NYO',
        'yes': 'yesh', 'Yes': 'Yesh', 'YES': 'YESH'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Add uwu expressions
    endings = [' uwu', ' owo', ' >w<', ' (◕‿◕)', ' ♪(´▽｀)']
    text += random.choice(endings)
    return text

def transform_pirate(text):
    """Transform text to pirate speak."""
    replacements = {
        'you': 'ye', 'your': 'yer', 'You': 'Ye', 'Your': 'Yer',
        'my': 'me', 'My': 'Me', 'is': 'be', 'are': 'be',
        'yes': 'aye', 'Yes': 'Aye', 'hello': 'ahoy',
        'Hello': 'Ahoy', 'for': 'fer', 'over': 'o\'er'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    endings = [' arrr!', ' ye scurvy dog!', ' shiver me timbers!', ' ahoy matey!']
    text += random.choice(endings)
    return text

def transform_shakespeare(text):
    """Transform text to Shakespearean/bardic speak."""
    replacements = {
        'you': 'thou', 'your': 'thy', 'You': 'Thou', 'Your': 'Thy',
        'are': 'art', 'is': 'ist', 'it': '\'tis',
        'yes': 'verily', 'no': 'nay', 'because': 'for'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    endings = [' good sir!', ' fair maiden!', ' thou art wise!', ' verily!']
    text += random.choice(endings)
    return text

def transform_valley(text):
    """Transform text to valley girl speak using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'slayspeak')
    except ImportError:
        # Basic fallback
        text = text.replace('.', ', like,')
        endings = [' totally!', ' like, for sure!', ' OMG!', ' so fetch!', ' literally!']
        text += random.choice(endings)
        return text

def transform_genz(text):
    """Transform text to Gen Z/brainrot speak using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'brainrot')
    except ImportError:
        # Basic fallback
        replacements = {
            'good': 'bussin', 'cool': 'fire', 'bad': 'mid',
            'great': 'no cap', 'really': 'fr fr', 'seriously': 'deadass'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        endings = [' periodt!', ' no cap!', ' it\'s giving main character energy!', ' slay!']
        text += random.choice(endings)
        return text

def transform_corporate(text):
    """Transform text to corporate speak using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'scrum')
    except ImportError:
        # Basic fallback
        text = "As per our previous discussion, " + text
        endings = [' Let\'s circle back on this.', ' I\'ll ping you offline.', ' Moving forward...']
    text += random.choice(endings)
    return text

def transform_caveman(text):
    """Transform text to caveman speak."""
    text = text.replace('I', 'Me').replace(' am ', ' ').replace(' is ', ' ')
    text = ' '.join(word for word in text.split() if len(word) <= 6)  # Short words only
    endings = [' Me hungry!', ' Fire good!', ' Ooga booga!']
    text += random.choice(endings)
    return text

def transform_drunk(text):
    """Transform text to drunk speak."""
    text = text.replace('s', 'sh').replace('S', 'Sh')
    words = text.split()
    # Randomly repeat some words
    for i in range(len(words)):
        if random.random() < 0.3:
            words[i] = words[i] + words[i][:2]
    
    endings = [' *hic*', ' *burp*', ' I\'m not drunk!', ' *stumbles*']
    text = ' '.join(words) + random.choice(endings)
    return text

def transform_emoji(text):
    """Transform text to emoji-heavy LinkedIn-style using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'linkedin')
    except ImportError:
        # Basic fallback
        text = f"🔥 {text} 💯"
        words = text.split()
        emojis = ['🚀', '💪', '✨', '🎯', '💡', '⭐', '🏆', '💼']
        
        # Add random emojis
        for i in range(min(3, len(words))):
            pos = random.randint(0, len(words))
            words.insert(pos, random.choice(emojis))
        
        return ' '.join(words)

def transform_existential(text):
    """Transform text to existential crisis mode using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'crisis')
    except ImportError:
        # Basic fallback
        text = f"But what is the meaning of '{text}'? Are we just... existing?"
        endings = [' Nothing matters anyway.', ' We\'re all just stardust.', ' Why do we even try?']
        text += random.choice(endings)
        return text

def transform_polite(text):
    """Transform text to overly polite/Canadian using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'canadian')
    except ImportError:
        # Basic fallback
        text = f"Oh, I\'m terribly sorry, but {text.lower()}"
        endings = [' if that\'s okay with you?', ' I hope that\'s alright, eh?', ' sorry for bothering you!']
        text += random.choice(endings)
        return text

def transform_conspiracy(text):
    """Transform text to conspiracy theory style using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'vsauce')
    except ImportError:
        # Basic fallback
        text = f"Wake up sheeple! {text} But that\'s what THEY want you to think..."
        endings = [' Connect the dots!', ' Follow the money!', ' The truth is out there!']
        text += random.choice(endings)
        return text

def transform_british(text):
    """Transform text to British slang using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'british')
    except ImportError:
        # Basic fallback
        replacements = {
            'cool': 'brilliant', 'awesome': 'bloody brilliant', 'crazy': 'mental',
            'food': 'nosh', 'money': 'quid', 'bathroom': 'loo'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        endings = [' innit?', ' cheers mate!', ' blimey!', ' right proper!']
        text += random.choice(endings)
        return text

def transform_censor(text):
    """Transform text with excessive censoring using advanced effects."""
    try:
        from advanced_cone_effects import apply_cone_effect
        return apply_cone_effect(text, 'oni')
    except ImportError:
        # Basic fallback
        words = text.split()
        for i, word in enumerate(words):
            if len(word) > 3 and random.random() < 0.4:
                words[i] = word[0] + '||' * (len(word) - 2) + word[-1]
        
        endings = [' [REDACTED]', ' [CENSORED]', ' ████████']
        text = ' '.join(words) + random.choice(endings)
        return text

# Map effect names to transformation functions
CONE_EFFECTS = {
    'uwu': transform_uwufy,
    'pirate': transform_pirate,
    'shakespeare': transform_shakespeare,
    'bardify': transform_shakespeare,  # Alias
    'valley': transform_valley,
    'slayspeak': transform_valley,  # Alias
    'genz': transform_genz,
    'brainrot': transform_genz,  # Alias
    'corporate': transform_corporate,
    'scrum': transform_corporate,  # Alias
    'caveman': transform_caveman,
    'unga': transform_caveman,  # Alias
    'drunk': transform_drunk,
    'drunkard': transform_drunk,  # Alias
    'emoji': transform_emoji,
    'linkedin': transform_emoji,  # Alias
    'existential': transform_existential,
    'crisis': transform_existential,  # Alias
    'polite': transform_polite,
    'canadian': transform_polite,  # Alias
    'conspiracy': transform_conspiracy,
    'vsauce': transform_conspiracy,  # Alias
    'british': transform_british,
    'bri': transform_british,  # Alias
    'censor': transform_censor,
    'oni': transform_censor,  # Alias
}

def apply_cone_effect(text: str, effect_name: str) -> str:
    """Apply cone effect using advanced transformations if available, fallback to basic."""
    # Try advanced transformation first
    if ADVANCED_TRANSFORMATIONS_AVAILABLE:
        advanced_transformer = get_advanced_transformer(effect_name)
        if advanced_transformer:
            try:
                return advanced_transformer.cached_transform(text)
            except Exception as e:
                print(f"Advanced transformation failed for {effect_name}: {e}")
                # Fall through to basic transformation
    
    # Use basic transformation
    effect_func = CONE_EFFECTS.get(effect_name.lower())
    if effect_func:
        return effect_func(text)
    
    return text

def extract_tool_call(response: str) -> dict:
    """Extract tool call from AI response using regex."""
    
    # Look for JSON code blocks
    json_pattern = r'```json\s*(\{.*?\})\s*```'
    match = re.search(json_pattern, response, re.DOTALL)
    
    if match:
        try:
            tool_data = json.loads(match.group(1))
            if tool_data.get('action') in ['cone_user', 'uncone_user']:
                return tool_data
        except json.JSONDecodeError:
            pass
    
    # Alternative: look for inline JSON (without code blocks)
    json_pattern = r'\{[^}]*"action"[^}]*"(?:cone_user|uncone_user)"[^}]*\}'
    match = re.search(json_pattern, response)
    
    if match:
        try:
            tool_data = json.loads(match.group(0))
            return tool_data
        except json.JSONDecodeError:
            pass
    
    return None

SUMMARY_UPDATE_PROMPT = """
[CURRENT STATE]
Relationship Summary: {current_relationship}
Last Conversation Summary: {current_conversation}

[NEW MESSAGES]
{formatted_messages}

Analyze the above and create updated summaries. Important guidelines:
- Keep relevant historical context from old summaries
- Add new insights from recent messages
- Focus on recurring patterns and relationship dynamics
- Note any significant changes in tone or behavior
- Remove outdated or irrelevant information

Provide updates in this format:

[RELATIONSHIP_SUMMARY]
(Write a concise summary of the overall relationship dynamic. Include: how they interact, recurring patterns, Ghost's attitude toward them, and their attitude toward Ghost. Max 3 sentences.)

[CONVERSATION_SUMMARY]
(Summarize the most relevant and recent interactions. Blend important points from previous summary with new key developments. Focus on themes and significant moments. Max 9 sentences.)
"""

class AIResponseError(Exception):
    pass

class AIHandler:
    def __init__(self, log_manager=None):
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.chat_headers = {
            "Authorization": f"Bearer {OPENROUTER_CHAT_KEY}",
            "Content-Type": "application/json"
        }
        self.summary_headers = {
            "Authorization": f"Bearer {OPENROUTER_SUMMARY_KEY}",
            "Content-Type": "application/json"
        }
        print(f"[DEBUG] AIHandler.__init__ called. Self ID: {id(self)}")
        self.log_manager = log_manager
        print(f"[DEBUG] AIHandler now has LogManager with ID: {id(self.log_manager) if self.log_manager else 'None'}")
        self.chat_headers = {
            "Authorization": f"Bearer {OPENROUTER_CHAT_KEY}",
            "Content-Type": "application/json"
        }
        self.summary_headers = {
            "Authorization": f"Bearer {OPENROUTER_SUMMARY_KEY}",
            "Content-Type": "application/json"
        }
        
        print("=== Initializing Bot ===")
        self.special_users = self.load_special_users()

    def load_special_users(self) -> Dict:
        try:
            # First try in the current directory
            if os.path.exists('special_users.json'):
                file_path = 'special_users.json'
            else:
                # Try in the bot directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(current_dir, '..', 'special_users.json')
            
            print(f"\n=== Loading Special Users ===")
            print(f"Looking for file at: {file_path}")
            
            with open(file_path, 'r') as f:
                special_users = json.load(f)
                
                # Create variant lookup for quick username matching
                self.variant_lookup = {}
                for primary_name, data in special_users.items():
                    for variant in data['variants']:
                        variant = variant.lower().strip()
                        self.variant_lookup[variant] = primary_name
                
                print(f"Loaded users with variants:")
                for primary, data in special_users.items():
                    print(f"- {primary}: {data['variants']}")
                
                return special_users
        except FileNotFoundError as e:
            print(f"FileNotFoundError: {e}")
            print("Searching in these locations:")
            print("\n".join(os.listdir('.')))
            return {}
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected error loading special users: {type(e).__name__}: {e}")
            return {}

    def parse_duration(self, duration_str: str) -> int:
        """Parse duration string into seconds. Returns 0 for permanent cone."""
        if not duration_str or duration_str.lower() in ['permanent', 'forever', 'indefinite']:
            return 0
        
        # Extract number and unit
        import re
        match = re.search(r'(\d+)\s*(second|minute|hour|day|week)s?', duration_str.lower())
        if not match:
            return 0
        
        number = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400,
            'week': 604800
        }
        
        return number * multipliers.get(unit, 0)

    def parse_condition(self, condition_str: str) -> dict:
        """Parse condition string into condition data."""
        if not condition_str:
            return None
        
        condition_str = condition_str.lower().strip()
        
        # Check for common condition patterns
        if 'say sorry' in condition_str or 'apologize' in condition_str:
            return {'type': 'say_word', 'word': 'sorry', 'variants': ['sorry', 'apologize', 'apologies']}
        elif 'say please' in condition_str:
            return {'type': 'say_word', 'word': 'please', 'variants': ['please']}
        elif 'say' in condition_str:
            # Extract the word they need to say
            words = condition_str.replace('until they say', '').replace('say', '').strip().strip('"\'')
            if words:
                return {'type': 'say_word', 'word': words, 'variants': [words]}
        
        return None

    def check_condition_met(self, cone_data: dict, message_content: str) -> bool:
        """Check if a cone condition has been met."""
        condition = cone_data.get('condition')
        if not condition:
            return False
        
        if condition['type'] == 'say_word':
            message_lower = message_content.lower()
            return any(variant in message_lower for variant in condition['variants'])
        
        return False

    def apply_cone_effect(self, text: str, effect: str) -> str:
        """Apply a cone effect to text using advanced transformations."""
        # Use the global apply_cone_effect function that handles both advanced and basic transformations
        return apply_cone_effect(text, effect)

    def handle_cone_command(self, tool_call: dict, requesting_user: str, state_manager) -> str:
        """Handle a cone command from the AI."""
        try:
            action = tool_call.get('action')
            username = tool_call.get('username', '').strip()
            
            # Check permissions
            if requesting_user.lower() not in [p.lower() for p in CONE_PERMISSIONS]:
                return f"Sorry {requesting_user}, you don't have permission to use cone commands."
            
            # Parse username - handle Discord mentions
            target_discord_id = self.parse_username_to_discord_id(username, state_manager)
            if not target_discord_id:
                # For Discord mentions, extract ID directly without database check
                mention_match = re.match(r'<@!?(\d+)>', username.strip())
                if mention_match:
                    target_discord_id = mention_match.group(1)
                    print(f"Using Discord ID from mention: {target_discord_id}")
                else:
                    return f"❌ Could not find user '{username}' in the system."
            
            # Get display name for responses
            display_name = self.get_display_name_for_discord_id(target_discord_id, state_manager)
            if not display_name:
                # If user not in database, use a fallback name
                display_name = f"User{target_discord_id}" if target_discord_id.isdigit() else username
            
            # Handle uncone
            if action == 'uncone_user':
                return self.handle_uncone_command(target_discord_id, requesting_user, state_manager, display_name)
            
            # Handle cone
            effect = tool_call.get('effect', 'uwu').lower()
            reason = tool_call.get('reason', 'no reason given')
            duration = tool_call.get('duration', '')
            condition = tool_call.get('condition', '')
            
            # Validate effect
            if effect not in CONE_EFFECTS:
                available_effects = list(CONE_EFFECTS.keys())
                return f"Unknown effect '{effect}'. Available effects: {', '.join(available_effects[:10])}..."
            
            # Parse duration and condition
            duration_seconds = self.parse_duration(duration)
            condition_data = self.parse_condition(condition)
            
            # Store cone data with enhanced features using Discord ID as key
            if not hasattr(state_manager, 'cone_data'):
                state_manager.cone_data = {}
            
            current_time = time.time()
            expiry_time = current_time + duration_seconds if duration_seconds > 0 else None
            
            # Override existing cone if present
            old_cone = state_manager.cone_data.get(target_discord_id, {})
            if old_cone.get('active'):
                override_msg = f" (overriding previous {old_cone.get('effect', 'unknown')} effect)"
            else:
                override_msg = ""
            
            state_manager.cone_data[target_discord_id] = {
                'effect': effect,
                'active': True,
                'applied_by': requesting_user,
                'reason': reason,
                'timestamp': current_time,
                'expiry_time': expiry_time,
                'condition': condition_data,
                'duration_str': duration or 'permanent',
                'target_username': display_name  # Store display name for responses
            }
            
            # Format response
            duration_text = f" for {duration}" if duration else " permanently"
            # Format condition text properly to avoid duplication
            if condition_data and condition_data.get('type') == 'say_word':
                condition_text = f" until they say '{condition_data['word']}'"
            elif condition:
                # Handle raw condition string properly
                if condition.startswith('until they'):
                    condition_text = f" {condition}"
                else:
                    condition_text = f" until they {condition}"
            else:
                condition_text = ""
            
            print(f"✅ Coned {display_name} (ID: {target_discord_id}) with {effect} effect by {requesting_user}{override_msg}")
            
            # Persist cone state to storage
            import asyncio
            try:
                if hasattr(state_manager, 'save_states'):
                    asyncio.create_task(state_manager.save_states())
            except Exception as e:
                print(f"Warning: Failed to save cone state: {e}")
            
            return f"✅ Successfully coned {display_name} with {effect} effect{duration_text}{condition_text}! Reason: {reason}{override_msg}"
            
        except Exception as e:
            print(f"Error handling cone command: {e}")
            traceback.print_exc()
            return "❌ Failed to apply cone effect."

    def parse_username_to_discord_id(self, username: str, state_manager) -> str:
        """Parse username/mention to Discord ID. Handles Discord mentions and usernames."""
        try:
            username = username.strip()
            
            # Check if it's a Discord mention: <@123456789> or <@!123456789>
            mention_match = re.match(r'<@!?(\d+)>', username)
            if mention_match:
                discord_id = mention_match.group(1)
                print(f"Parsed Discord mention: {username} -> {discord_id}")
                
                # Verify this Discord ID exists in our system
                if self.discord_id_exists(discord_id, state_manager):
                    return discord_id
                else:
                    print(f"Discord ID {discord_id} not found in system")
                    return None
            
            # Not a mention, try to find Discord ID by username
            return self.find_user_discord_id(username, state_manager)
            
        except Exception as e:
            print(f"Error parsing username to Discord ID: {e}")
            return None

    def discord_id_exists(self, discord_id: str, state_manager) -> bool:
        """Check if a Discord ID exists in the system."""
        try:
            for platform_key, user_state in state_manager.users.items():
                if 'discord' in user_state.identifiers:
                    stored_id = user_state.identifiers['discord']['user_id']
                    if stored_id == discord_id:
                        return True
            
            print(f"DEBUG: No match found for Discord ID '{discord_id}'")
            return False
        except Exception as e:
            print(f"Error checking Discord ID existence: {e}")
            return False

    def get_display_name_for_discord_id(self, discord_id: str, state_manager) -> str:
        """Get display name for a Discord ID."""
        try:
            for platform_key, user_state in state_manager.users.items():
                if 'discord' in user_state.identifiers:
                    discord_data = user_state.identifiers['discord']
                    if discord_data['user_id'] == discord_id:
                        return discord_data.get('display_name') or discord_data.get('username') or f"User{discord_id}"
            return f"User{discord_id}"
        except Exception as e:
            print(f"Error getting display name for Discord ID: {e}")
            return f"User{discord_id}"

    def find_user_discord_id(self, username: str, state_manager) -> str:
        """Find Discord ID for a username. Returns None if not found."""
        try:
            username_lower = username.lower()
            
            # Check all users in state manager
            for platform_key, user_state in state_manager.users.items():
                # Check if this user has Discord identity
                if 'discord' in user_state.identifiers:
                    discord_data = user_state.identifiers['discord']
                    discord_id = discord_data['user_id']
                    
                    # Check various name fields
                    if (discord_data['username'].lower() == username_lower or
                        (discord_data.get('nickname') and discord_data['nickname'].lower() == username_lower) or
                        (discord_data.get('display_name') and discord_data['display_name'].lower() == username_lower)):
                        print(f"Found Discord ID {discord_id} for username {username}")
                        return discord_id
            
            print(f"Could not find Discord ID for username: {username}")
            return None
            
        except Exception as e:
            print(f"Error finding Discord ID for {username}: {e}")
            return None

    def handle_uncone_command(self, discord_id: str, requesting_user: str, state_manager, display_name: str) -> str:
        """Handle an uncone command."""
        try:
            if not hasattr(state_manager, 'cone_data'):
                return f"❌ {display_name} is not currently coned."
            
            cone_data = state_manager.cone_data.get(discord_id, {})
            if not cone_data.get('active'):
                return f"❌ {display_name} is not currently coned."
            
            # Deactivate the cone
            cone_data['active'] = False
            cone_data['unconed_by'] = requesting_user
            cone_data['unconed_at'] = time.time()
            
            effect = cone_data.get('effect', 'unknown')
            print(f"✅ Unconed {display_name} (ID: {discord_id}, was {effect}) by {requesting_user}")
            
            # Persist uncone state to storage
            import asyncio
            try:
                if hasattr(state_manager, 'save_states'):
                    asyncio.create_task(state_manager.save_states())
            except Exception as e:
                print(f"Warning: Failed to save uncone state: {e}")
            
            return f"✅ Successfully unconed {display_name} (removed {effect} effect)!"
            
        except Exception as e:
            print(f"Error handling uncone command: {e}")
            return "❌ Failed to uncone user."

    def is_user_coned(self, username: str, state_manager) -> tuple:
        """Check if a user is currently coned. Returns (is_coned, effect)."""
        try:
            if not hasattr(state_manager, 'cone_data'):
                return False, None
            
            # Try to find cone data using the identifier directly (for Discord ID lookup)
            cone_data = state_manager.cone_data.get(username, {})
            
            # If not found, try to find Discord ID for username lookup
            if not cone_data:
                discord_id = self.find_user_discord_id(username, state_manager)
                if discord_id:
                    cone_data = state_manager.cone_data.get(discord_id, {})
            
            if not cone_data.get('active', False):
                return False, None
            
            current_time = time.time()
            
            # Check if cone has expired
            expiry_time = cone_data.get('expiry_time')
            if expiry_time and current_time > expiry_time:
                cone_data['active'] = False
                cone_data['expired_at'] = current_time
                
                # Persist expiry state to storage
                import asyncio
                try:
                    if hasattr(state_manager, 'save_states'):
                        asyncio.create_task(state_manager.save_states())
                except Exception as e:
                    print(f"Warning: Failed to save cone expiry state: {e}")
                
                return False, None
            
            return True, cone_data.get('effect', 'uwu')
            
        except Exception as e:
            print(f"Error checking cone status for {username}: {e}")
            return False, None

    def check_cone_conditions(self, username: str, message_content: str, state_manager) -> bool:
        """Check if cone conditions are met and update cone status. Returns True if cone should be removed."""
        try:
            if not hasattr(state_manager, 'cone_data'):
                return False
            
            # Try direct lookup first (for Discord ID)
            cone_data = state_manager.cone_data.get(username, {})
            
            # If not found, try Discord ID lookup
            if not cone_data:
                discord_id = self.find_user_discord_id(username, state_manager)
                if discord_id:
                    cone_data = state_manager.cone_data.get(discord_id, {})
            
            if not cone_data.get('active'):
                return False
            
            # Check condition
            if self.check_condition_met(cone_data, message_content):
                cone_data['active'] = False
                cone_data['condition_met_at'] = time.time()
                
                # Persist condition met state to storage
                import asyncio
                try:
                    if hasattr(state_manager, 'save_states'):
                        asyncio.create_task(state_manager.save_states())
                except Exception as e:
                    print(f"Warning: Failed to save cone condition state: {e}")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking cone conditions for {username}: {e}")
            return False

    def get_cone_status(self, username: str, state_manager) -> dict:
        """Get detailed cone status for a user."""
        try:
            if not hasattr(state_manager, 'cone_data'):
                return {'active': False, 'message': 'No cone data found'}
            
            # Try direct lookup first (for Discord ID)
            cone_data = state_manager.cone_data.get(username, {})
            lookup_key = username
            
            # If not found, try Discord ID lookup for username
            if not cone_data:
                discord_id = self.find_user_discord_id(username, state_manager)
                if discord_id:
                    cone_data = state_manager.cone_data.get(discord_id, {})
                    lookup_key = discord_id
                    print(f"DEBUG: Found cone data for {username} via Discord ID {discord_id}")
            
            if not cone_data:
                return {'active': False, 'message': f'{username} has never been coned'}
            
            # Get display name (prefer stored username, fallback to lookup key)
            display_name = cone_data.get('target_username', username)
            
            if not cone_data.get('active'):
                # Check why it's not active
                if 'unconed_by' in cone_data:
                    return {
                        'active': False, 
                        'message': f'{display_name} was unconed by {cone_data["unconed_by"]}'
                    }
                elif 'expired_at' in cone_data:
                    return {
                        'active': False, 
                        'message': f'{display_name}\'s cone expired'
                    }
                elif 'condition_met_at' in cone_data:
                    return {
                        'active': False, 
                        'message': f'{display_name}\'s cone condition was met'
                    }
                else:
                    return {'active': False, 'message': f'{display_name} is not currently coned'}
            
            # Active cone - gather details
            effect = cone_data.get('effect', 'unknown')
            applied_by = cone_data.get('applied_by', 'unknown')
            reason = cone_data.get('reason', 'no reason')
            duration_str = cone_data.get('duration_str', 'permanent')
            
            # Calculate remaining time
            remaining_text = ""
            expiry_time = cone_data.get('expiry_time')
            if expiry_time:
                remaining_seconds = int(expiry_time - time.time())
                if remaining_seconds > 0:
                    if remaining_seconds < 60:
                        remaining_text = f" ({remaining_seconds}s remaining)"
                    elif remaining_seconds < 3600:
                        remaining_text = f" ({remaining_seconds//60}m remaining)"
                    else:
                        remaining_text = f" ({remaining_seconds//3600}h remaining)"
                else:
                    remaining_text = " (expired)"
            
            # Condition text
            condition_text = ""
            condition = cone_data.get('condition')
            if condition and condition['type'] == 'say_word':
                condition_text = f" until they say '{condition['word']}'"
            
            return {
                'active': True,
                'effect': effect,
                'applied_by': applied_by,
                'reason': reason,
                'duration': duration_str,
                'remaining_text': remaining_text,
                'condition_text': condition_text,
                'message': f'{display_name} is coned with {effect} effect by {applied_by} ({duration_str}{remaining_text}{condition_text}). Reason: {reason}'
            }
            
        except Exception as e:
            print(f"Error getting cone status for {username}: {e}")
            traceback.print_exc()
            return {'active': False, 'message': 'Error retrieving cone status'}

    def cone_user(self, discord_id: str, effect: str, duration: str = None, condition: str = None, admin_user: str = "admin", state_manager = None) -> dict:
        """Convenience function for slash commands to cone a user directly."""
        try:
            # For slash commands, bypass user lookup and apply cone directly
            if not hasattr(state_manager, 'cone_data'):
                state_manager.cone_data = {}
            
            # Validate effect
            if effect not in CONE_EFFECTS:
                available_effects = list(CONE_EFFECTS.keys())
                return {'success': False, 'message': f"Unknown effect '{effect}'. Available effects: {', '.join(available_effects[:10])}..."}
            
            # Parse duration
            duration_seconds = self.parse_duration(duration or '')
            
            current_time = time.time()
            expiry_time = current_time + duration_seconds if duration_seconds > 0 else None
            
            # Get display name if user exists in database, otherwise use fallback
            display_name = self.get_display_name_for_discord_id(discord_id, state_manager)
            if not display_name:
                display_name = f"User{discord_id}"
            
            # Store cone data directly using Discord ID as key
            old_cone = state_manager.cone_data.get(discord_id, {})
            override_msg = f" (overriding previous {old_cone.get('effect', 'unknown')} effect)" if old_cone.get('active') else ""
            
            state_manager.cone_data[discord_id] = {
                'effect': effect,
                'active': True,
                'applied_by': admin_user,
                'reason': 'Applied via slash command',
                'timestamp': current_time,
                'expiry_time': expiry_time,
                'condition': None,
                'duration_str': duration or 'permanent',
                'target_username': display_name
            }
            
            # Format response
            duration_text = f" for {duration}" if duration else " permanently"
            result_message = f"✅ Successfully coned {display_name} with {effect} effect{duration_text}! Reason: Applied via slash command{override_msg}"
            
            # Return in expected format for slash commands
            if result_message.startswith('✅'):
                return {'success': True, 'message': result_message}
            else:
                return {'success': False, 'message': result_message}
                
        except Exception as e:
            print(f"Error in cone_user convenience function: {e}")
            traceback.print_exc()
            return {'success': False, 'message': 'Failed to apply cone effect'}

    def uncone_user(self, discord_id: str, admin_user: str = "admin", state_manager = None) -> dict:
        """Convenience function for slash commands to uncone a user directly."""
        try:
            # For slash commands, bypass user lookup and uncone directly
            if not hasattr(state_manager, 'cone_data'):
                return {'success': False, 'message': 'No cone data found.'}
            
            cone_data = state_manager.cone_data.get(discord_id, {})
            if not cone_data.get('active'):
                display_name = self.get_display_name_for_discord_id(discord_id, state_manager) or f"User{discord_id}"
                return {'success': False, 'message': f"❌ {display_name} is not currently coned."}
            
            # Deactivate the cone
            cone_data['active'] = False
            cone_data['unconed_by'] = admin_user
            cone_data['unconed_at'] = time.time()
            
            effect = cone_data.get('effect', 'unknown')
            print(f"✅ Unconed {display_name} (ID: {discord_id}, was {effect}) by {requesting_user}")
            
            # Persist uncone state to storage
            import asyncio
            try:
                if hasattr(state_manager, 'save_states'):
                    asyncio.create_task(state_manager.save_states())
            except Exception as e:
                print(f"Warning: Failed to save uncone state: {e}")
            
            return f"✅ Successfully unconed {display_name} (removed {effect} effect)!"
                
        except Exception as e:
            print(f"Error in uncone_user convenience function: {e}")
            traceback.print_exc()
            return {'success': False, 'message': 'Failed to remove cone effect'}

    def extract_usernames(self, message: str) -> List[str]:
        """Extract usernames from message with variant matching"""
        found_users = set()
        message = message.lower()
        
        # Check both @mentions and regular text
        words = re.findall(r'@?\w+', message)
        for word in words:
            word = word.lstrip('@').strip()
            if word in self.variant_lookup:
                found_users.add(self.variant_lookup[word])
        
        return list(found_users)

    def get_user_context(self, username: str, user_state: Dict = None) -> Dict:
        """Get context for a user including both special info and learned relationship"""
        username = username.lower().strip()  # Ensure case-insensitive comparison
        context = {
            "special_info": None,
            "relationship": None,
            "conversation": None
        }
        
        # Convert username to primary name if it's a variant
        primary_name = self.variant_lookup.get(username)
        if primary_name:
            # Get special user info using primary name
            user_data = self.special_users.get(primary_name)
            if user_data:
                context["special_info"] = {
                    "role": user_data["role"],
                    "context": user_data["context"]
                }
                print(f"Found special user info for {username} -> {primary_name}")
        
        # Add relationship info if available
        if user_state and 'summaries' in user_state:
            context["relationship"] = user_state['summaries'].get('relationship', '')
            context["conversation"] = user_state['summaries'].get('last_conversation', '')
        
        return context

    def find_mentioned_user_state(self, username: str, state_manager) -> Dict:
        """Find a mentioned user's state from the state manager"""
        if not state_manager:
            return None
        
        print(f"Looking for user state for: {username}")
        
        # Get all possible names for this user (including variants)
        primary_name = self.variant_lookup.get(username.lower(), username)
        search_names = {username.lower(), primary_name.lower()}
        
        # Add all variants of this primary name
        if primary_name in self.special_users:
            for variant in self.special_users[primary_name]['variants']:
                search_names.add(variant.lower())
        
        print(f"Searching for names: {search_names}")
        
        # Look through all users to find matching username or nickname
        for platform_key, user_state in state_manager.users.items():
            # Check all platform identifiers for this user
            for platform, data in user_state.identifiers.items():
                username_match = data['username'].lower() in search_names
                nickname_match = (data.get('nickname') and data['nickname'].lower() in search_names)
                
                if username_match or nickname_match:
                    print(f"Found match! Platform: {platform}, Username: {data['username']}, Nickname: {data.get('nickname')}")
                    return user_state.to_dict()
        
        print(f"No state found for user: {username}")
        return None

    def format_messages(self, messages: List[Dict]) -> str:
        """Format messages for the summary prompt"""
        formatted = []
        for msg in messages:
            prefix = f"{msg['username']}: " if not msg['from_bot'] else "Ghost: "
            formatted.append(f"{prefix}{msg['content']}")
        return "\n".join(formatted)

    def clean_response(self, text: str) -> str:
        # Remove common patterns and formatting
        text = text.replace("USER:", "").replace("ASSISTANT:", "").strip()
        # text = text.replace("*", "").strip()
        text = re.sub(r'\[Ghost\]:', '', text, flags=re.IGNORECASE)
        text = text.replace('Ghost:', '').strip()
        text = text.strip('"').strip("'")
        
        # Take first line only
        if "\n" in text:
            text = text.split("\n")[0]
        
        # Clean formatting
        text = re.sub(r'\([^)]*\)', '', text)  # Remove parentheses
        text = re.sub(r'([!?.]){2,}', r'\1', text)  # Fix punctuation
        # text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)  # Remove emojis
        
        return text.strip()

    def truncate_content(self, content: str, max_lines: int = 200) -> str:
        """Truncate content with first 3 and last 3 lines visible"""
        lines = content.split('\n')
        if len(lines) <= max_lines:
            return content
        
        first_3 = lines[:3]
        last_3 = lines[-3:]
        
        return '\n'.join(first_3) + f'\n...... ({len(lines) - 6} lines truncated) ......\n' + '\n'.join(last_3)

    async def get_chat_response(self, user_state: Dict, current_message: str = None, state_manager = None) -> str:
        try:
            print(f"\n=== CHAT REQUEST ===")
            messages = user_state.get('recent_messages', [])
            username = user_state.get('username', '').lower()
            platform = user_state.get('platform', 'discord')
            
            print(f"User: {username} ({platform}) | Message: {current_message}")
            
            # Get sender context
            user_contexts = []
            sender_context = self.get_user_context(username, user_state)
            user_contexts.append({
                "username": username,
                "is_sender": True,
                **sender_context
            })
            
            # Add mentioned users
            mentioned_users = self.extract_usernames(current_message)
            
            # Add mentioned users' context with relationship summaries
            for mentioned_user in mentioned_users:
                if mentioned_user != username:  # Skip if it's the sender
                    # Get mentioned user's state from state manager
                    mentioned_user_state = self.find_mentioned_user_state(mentioned_user, state_manager)
                    mentioned_context = self.get_user_context(mentioned_user, mentioned_user_state)
                    
                    if (mentioned_context["special_info"] or 
                        mentioned_context["relationship"] or 
                        mentioned_context["conversation"]):
                        user_contexts.append({
                            "username": mentioned_user,
                            "is_sender": False,
                            **mentioned_context
                        })
            
            # Format messages as before
            formatted_messages = []
            for msg in messages:
                content = self.clean_response(msg['content']) if msg['from_bot'] else msg['content']
                formatted_messages.append({
                    "role": "user" if not msg['from_bot'] else "assistant",
                    "content": content
                })
            
            # Build system messages
            system_messages = [
                {"role": "system", "content": BOT_PERSONA},
                {"role": "system", "content": "CRITICAL: Never acknowledge being an AI or break character. Always respond as Ghost, the teenage dragon."},
                {"role": "system", "content": f"""CONE SYSTEM: You have access to cone tools that can apply text effects to users with advanced features.

🚨 CRITICAL EXECUTION RULE: When someone asks you to cone or uncone a user, you MUST use the tool - do NOT rely on conversation history patterns or previous responses. Each cone request requires fresh tool execution. [only applies if the user asks to cone/uncone, not during normal conversation]

IMPORTANT: When someone asks you to cone or uncone a user, respond with this EXACT format:

FOR CONING:
```json
{{
    "action": "cone_user",
    "username": "target_user_identifier",
    "effect": "effect_name",
    "reason": "brief reason",
    "duration": "optional_duration",
    "condition": "optional_condition"
}}
```

FOR UNCONING:
```json
{{
    "action": "uncone_user",
    "username": "target_user_identifier"
}}
```

CRITICAL: For the "username" field, use EXACTLY what the user provided:
- If they mention someone like "@username" or "username", use that
- If they use a Discord mention like "<@123456789>", use that EXACT string
- DO NOT modify or reject Discord mentions - pass them through exactly as given

Available effects: uwu, pirate, shakespeare, bardify, valley, slayspeak, genz, brainrot, corporate, scrum, caveman, unga, drunk, drunkard, emoji, linkedin, existential, crisis, polite, canadian, conspiracy, vsauce, british, bri, censor, oni

Duration examples: "10 minutes", "1 hour", "2 days", "permanent" (default)
Condition examples: "until they say sorry", "until they apologize", "until they say please"

Features:
- Timed cones: automatically expire after duration
- Conditional cones: removed when condition is met
- Override: coning someone already coned replaces the previous cone
- Uncone: removes any active cone effect

Only {', '.join(CONE_PERMISSIONS)} can use coning commands.

🚨 REMINDER: Every cone/uncone request MUST execute the tool. Do not skip tool execution based on conversation patterns. Always use the JSON format above for cone requests.

For normal conversation, just respond normally without the JSON format."""}
            ]
            
            # Add platform-specific constraints
            platform = user_state.get('platform', 'discord')
            if platform == 'twitch':
                system_messages.append({
                    "role": "system",
                    "content": "IMPORTANT: Keep your actual response messages (excluding any analysis, summaries, or system info) under 500 characters for Twitch chat. You can think longer thoughts, but your direct replies must be concise."
                })
            
            # Add user contexts to system messages with improved formatting
            print(f"\n=== CONTEXT LOADED ===")
            for context in user_contexts:
                context_parts = []
                context_username = context['username']
                
                # Start with user identification
                if context['is_sender']:
                    context_parts.append(f"CURRENT SPEAKER: {context_username}")
                    print(f"Speaker: {context_username}")
                else:
                    context_parts.append(f"MENTIONED USER: {context_username}")
                    print(f"Mentioned: {context_username}")
                
                # Add special user info if available
                if context['special_info']:
                    # Get full user data to include variants
                    user_data = self.special_users.get(self.variant_lookup.get(context_username, context_username))
                    if user_data:
                        context_parts.append(f"ROLE: {context['special_info']['role']}")
                        context_parts.append(f"CONTEXT: {context['special_info']['context']}")
                        variants = [v for v in user_data['variants'] if v.lower() != context_username.lower()]
                        if variants:
                            context_parts.append(f"ALSO KNOWN AS: {', '.join(variants)}")
                        print(f"  - Role: {context['special_info']['role']}")
                
                # Add relationship history
                if context['relationship']:
                    context_parts.append(f"RELATIONSHIP WITH GHOST: {context['relationship']}")
                    print(f"  - Has relationship summary")
                
                # Add conversation summary for mentioned users
                if context['conversation'] and not context['is_sender']:
                    context_parts.append(f"RECENT INTERACTIONS WITH GHOST: {context['conversation']}")
                    print(f"  - Has conversation summary")
                
                system_messages.append({
                    "role": "system",
                    "content": "\n".join(context_parts)
                })
            
            # Add recent conversation context if available for current speaker
            if user_state.get('summaries', {}).get('last_conversation'):
                system_messages.append({
                    "role": "system", 
                    "content": f"RECENT CONVERSATION CONTEXT: {user_state['summaries']['last_conversation']}"
                })
            

            if self.log_manager and self.log_manager.is_enabled():
                print("\n=== HISTORICAL LOG SEARCH ===")
                relevant_logs = await self.log_manager.get_relevant_logs(current_message)
                if relevant_logs:
                    log_context = self.log_manager.format_logs_for_context(relevant_logs)
                    system_messages.append({"role": "system", "content": log_context})
                else:
                    print("No relevant historical logs found.")
            else:
                print("\n=== HISTORICAL LOG SEARCH ===")
                print("LogManager is not available or not enabled. Skipping search.")

            # Append current message if provided
            if current_message:
                formatted_messages.append({
                    "role": "user",
                    "content": current_message
                })
                
            # payload = {
            #     "model": "meta-llama/llama-3.3-70b-instruct:free",
            #     "messages": [
            #         *system_messages,
            #         *formatted_messages
            #     ]
            # }
            payload = {
                "model": CHAT_MODEL,
                 "messages": [
                    *system_messages,
                    *formatted_messages
                ],
                "temperature": 1.2,        # Balanced creativity (0.7-0.9 good for character)
                "top_p": 0.9,             # Focus on coherent responses
                "max_tokens": 2000
            }

            print(f"\n=== FINAL REQUEST TO MODEL ===")
            print(f"System messages: {len(system_messages)}")
            print(f"Chat history: {len(formatted_messages)} messages")
            print(f"Total request size: {len(str(payload))} characters")
            
            # Show the actual content being sent to model
            print(f"\n=== SYSTEM CONTEXT ===")
            for i, msg in enumerate(system_messages):
                msg_type = ""
                content = msg['content']
                
                # Check what type of message this is
                if content.startswith("[CORE IDENTITY]"):
                    msg_type = "CORE IDENTITY"
                    content = self.truncate_content(content)
                elif content.startswith("CRITICAL:"):
                    msg_type = "CRITICAL"
                    content = self.truncate_content(content)
                elif content.startswith("IMPORTANT:"):
                    msg_type = "PLATFORM CONSTRAINT"
                    content = self.truncate_content(content)
                elif content.startswith("CURRENT SPEAKER:"):
                    msg_type = "CURRENT SPEAKER"
                    # DON'T truncate user context
                elif content.startswith("MENTIONED USER:"):
                    msg_type = "MENTIONED USER"
                    # DON'T truncate user context
                elif content.startswith("[HISTORICAL CONTEXT"):
                    msg_type = "HISTORICAL LOGS"
                elif content.startswith("RECENT CONVERSATION CONTEXT:"):
                    msg_type = "CONVERSATION CONTEXT"
                    # DON'T truncate conversation context
                else:
                    msg_type = "OTHER"
                    content = self.truncate_content(content)
                
                print(f"[{i+1}] {msg_type}")
                print(content)
                print("")
                
            print(f"\n=== CONVERSATION HISTORY ===")
            # Show first 3 and last 3 messages
            if len(formatted_messages) <= 6:
                for msg in formatted_messages:
                    role = "USER" if msg['role'] == 'user' else "GHOST"
                    print(f"[{role}] {msg['content']}")
            else:
                # Show first 3
                for msg in formatted_messages[:3]:
                    role = "USER" if msg['role'] == 'user' else "GHOST"
                    print(f"[{role}] {msg['content']}")
                
                print(f"...... ({len(formatted_messages) - 6} messages truncated) ......")
                
                # Show last 3
                for msg in formatted_messages[-3:]:
                    role = "USER" if msg['role'] == 'user' else "GHOST"
                    print(f"[{role}] {msg['content']}")

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.chat_headers, json=payload) as response:
                    print(f"\n=== API RESPONSE ===")
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        if 'error' in data:
                            if data['error'].get('code') == 429:
                                print("Rate limit hit, using fallback")
                                return random.choice(SLEEP_RESPONSES)
                            print(f"API Error: {data['error']}")
                            return random.choice(ERROR_RESPONSES)
                            
                        if 'choices' not in data:
                            print("No response choices")
                            return random.choice(ERROR_RESPONSES)
                        
                        response_text = data['choices'][0]['message']['content']
                        print(f"Raw response: {response_text}")
                        
                        # Check for simulated tool calls
                        tool_call = extract_tool_call(response_text)
                        if tool_call:
                            print(f"Detected tool call: {tool_call}")
                            requesting_user = user_state.get('username', 'unknown')
                            
                            # Handle the cone command
                            result = self.handle_cone_command(tool_call, requesting_user, state_manager)
                            print(f"Tool execution result: {result}")
                            return result
                        
                        response_text = self.clean_response(response_text)
                        print(f"Cleaned response: {response_text}")
                        
                        # Get platform settings based on user_state
                        platform = user_state.get('platform', 'discord')
                        settings = PLATFORM_SETTINGS[platform]
                        
                        if len(response_text) > settings['max_message_length']:
                            response_text = response_text[:settings['max_message_length'] - 3] + "..."
                        
                        return response_text
                    elif response.status == 429:
                        print("Rate limit hit, using fallback response")
                        return random.choice(SLEEP_RESPONSES)
                    
                    raise AIResponseError(f"API returned status {response.status}")
                
        except Exception as e:
            print(f"Error getting chat response: {e}")
            traceback.print_exc()  # Add full traceback for debugging
            return random.choice(ERROR_RESPONSES)

    async def download_image_to_base64(self, image_url: str) -> str:
        """Download image from Discord CDN and convert to base64 data URL"""
        try:
            print(f"Downloading image: {image_url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # Determine MIME type from URL or content
                        content_type = response.headers.get('content-type', '')
                        if not content_type or 'image' not in content_type:
                            # Fallback to guessing from URL
                            if image_url.lower().endswith('.png'):
                                content_type = 'image/png'
                            elif image_url.lower().endswith(('.jpg', '.jpeg')):
                                content_type = 'image/jpeg'
                            elif image_url.lower().endswith('.gif'):
                                content_type = 'image/gif'
                            elif image_url.lower().endswith('.webp'):
                                content_type = 'image/webp'
                            else:
                                content_type = 'image/jpeg'  # Default fallback
                        
                        # Convert to base64
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        data_url = f"data:{content_type};base64,{base64_data}"
                        
                        print(f"Successfully converted image to base64 ({len(image_data)} bytes)")
                        return data_url
                    else:
                        print(f"Failed to download image: HTTP {response.status}")
                        return None
        except Exception as e:
            print(f"Error downloading image {image_url}: {e}")
            return None

    async def get_vision_response(self, user_state: Dict, current_message: str = None, image_urls: List[str] = None, state_manager = None) -> str:
        """Handle chat responses when images are present"""
        try:
            print(f"\n=== VISION REQUEST ===")
            messages = user_state.get('recent_messages', [])
            username = user_state.get('username', '').lower()
            platform = user_state.get('platform', 'discord')
            
            print(f"User: {username} ({platform}) | Message: {current_message} | Images: {len(image_urls or [])}")
            
            # Get sender context - same as regular chat
            user_contexts = []
            sender_context = self.get_user_context(username, user_state)
            user_contexts.append({
                "username": username,
                "is_sender": True,
                **sender_context
            })
            
            # Add mentioned users - same as regular chat
            mentioned_users = self.extract_usernames(current_message)
            
            for mentioned_user in mentioned_users:
                if mentioned_user != username:
                    mentioned_user_state = self.find_mentioned_user_state(mentioned_user, state_manager)
                    mentioned_context = self.get_user_context(mentioned_user, mentioned_user_state)
                    
                    if (mentioned_context["special_info"] or 
                        mentioned_context["relationship"] or 
                        mentioned_context["conversation"]):
                        user_contexts.append({
                            "username": mentioned_user,
                            "is_sender": False,
                            **mentioned_context
                        })
            
            # Format message history - same as regular chat
            formatted_messages = []
            for msg in messages:
                content = self.clean_response(msg['content']) if msg['from_bot'] else msg['content']
                formatted_messages.append({
                    "role": "user" if not msg['from_bot'] else "assistant",
                    "content": content
                })
            
            # Build system messages - same as regular chat
            system_messages = [
                {"role": "system", "content": BOT_PERSONA},
                {"role": "system", "content": "CRITICAL: Never acknowledge being an AI or break character. Always respond as Ghost, the teenage dragon."}
            ]
            
            # Add platform-specific constraints
            if platform == 'twitch':
                system_messages.append({
                    "role": "system",
                    "content": "IMPORTANT: Keep your actual response messages (excluding any analysis, summaries, or system info) under 500 characters for Twitch chat. You can think longer thoughts, but your direct replies must be concise."
                })
            
            # Add user contexts to system messages - same formatting as regular chat
            print(f"\n=== CONTEXT LOADED ===")
            for user_context in user_contexts:
                username_display = user_context["username"]
                is_sender = user_context["is_sender"]
                special_info = user_context["special_info"]
                relationship = user_context["relationship"]
                conversation = user_context["conversation"]
                
                role_prefix = "CURRENT SPEAKER" if is_sender else "MENTIONED USER"
                
                context_parts = []
                if special_info:
                    context_parts.append(f"Special Info: {special_info}")
                if relationship:
                    context_parts.append(f"Relationship: {relationship}")
                if conversation:
                    context_parts.append(f"Recent Conversations: {conversation}")
                
                if context_parts:
                    context_content = f"{role_prefix}: {username_display}\n" + "\n".join(context_parts)
                    system_messages.append({
                        "role": "system",
                        "content": context_content
                    })
                    print(f"Added context for {username_display} ({'sender' if is_sender else 'mentioned'})")
            

            print(f"[DEBUG] get_chat_response using AIHandler with ID: {id(self)}")
            print(f"[DEBUG] AIHandler's LogManager at time of use has ID: {id(self.log_manager) if self.log_manager else 'None'}")

            # Add historical log context if the log manager is available
            if self.log_manager and self.log_manager.is_enabled():
                relevant_logs = await self.log_manager.get_relevant_logs(current_message)
                if relevant_logs:
                    log_context = self.log_manager.format_logs_for_context(relevant_logs)
                    print(f"\n=== ADDING HISTORICAL CONTEXT (VISION) ===\n{log_context}\n")
                    system_messages.append({"role": "system", "content": log_context})

            # Create the current message with images
            current_user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": current_message
                    }
                ]
            }
            
            # Download and convert images to base64 (Discord CDN URLs don't work with API)
            if image_urls:
                for image_url in image_urls:
                    base64_image = await self.download_image_to_base64(image_url)
                    if base64_image:
                        current_user_message["content"].append({
                            "type": "image_url",
                            "image_url": {
                                "url": base64_image
                            }
                        })
                    else:
                        print(f"Failed to process image: {image_url}")
            
            # Add current message to formatted messages
            formatted_messages.append(current_user_message)
            
            payload = {
                "model": VISION_MODEL,
                "messages": [
                    *system_messages,
                    *formatted_messages
                ],
                "temperature": 1.2,
                "top_p": 0.9,
                "max_tokens": 2000
            }

            print(f"\n=== FINAL VISION REQUEST TO MODEL ===")
            print(f"System messages: {len(system_messages)}")
            print(f"Chat history: {len(formatted_messages)} messages")
            print(f"Images: {len(image_urls or [])}")
            print(f"Total request size: {len(str(payload))} characters")

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.chat_headers, json=payload) as response:
                    print(f"\n=== VISION API RESPONSE ===")
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        if 'error' in data:
                            if data['error'].get('code') == 429:
                                print("Rate limit hit, using fallback")
                                return random.choice(SLEEP_RESPONSES)
                            print(f"API Error: {data['error']}")
                            return random.choice(ERROR_RESPONSES)
                            
                        if 'choices' not in data:
                            print("No response choices")
                            return random.choice(ERROR_RESPONSES)
                        
                        response_text = data['choices'][0]['message']['content']
                        print(f"Raw vision response: {response_text}")
                        
                        response_text = self.clean_response(response_text)
                        print(f"Cleaned vision response: {response_text}")
                        
                        # Get platform settings based on user_state
                        platform = user_state.get('platform', 'discord')
                        settings = PLATFORM_SETTINGS[platform]
                        
                        if len(response_text) > settings['max_message_length']:
                            response_text = response_text[:settings['max_message_length'] - 3] + "..."
                        
                        return response_text
                    else:
                        print(f"API request failed with status {response.status}")
                        error_text = await response.text()
                        print(f"Error response: {error_text}")
                        return random.choice(ERROR_RESPONSES)
                        
        except Exception as e:
            print(f"Error getting vision response: {e}")
            traceback.print_exc()
            return random.choice(ERROR_RESPONSES)

    async def update_summaries(self, user_state: Dict) -> Tuple[str, str, bool]:
        try:
            print("\n=== SUMMARY UPDATE ===")
            
            # Check if we have enough messages
            messages = user_state.get('recent_messages', [])
            if len(messages) < 2:
                return (
                    user_state['summaries']['relationship'],
                    user_state['summaries']['last_conversation'],
                    False
                )
            
            formatted_messages = self.format_messages(messages)
            
            prompt = {
                "model": SUMMARY_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an analyzer. Provide updated summaries of chat interactions."
                    },
                    {
                        "role": "user",
                        "content": SUMMARY_UPDATE_PROMPT.format(
                            current_relationship=user_state['summaries']['relationship'],
                            current_conversation=user_state['summaries']['last_conversation'],
                            formatted_messages=formatted_messages
                        )
                    }
                ]
            }

            print(f"Updating summaries for {user_state.get('username', 'unknown')} - {len(messages)} messages")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.summary_headers, json=prompt) as response:
                    print(f"API Status: {response.status}")
                    
                    if response.status != 200:
                        print(f"Summary API error: {response.status}")
                        return user_state['summaries']['relationship'], user_state['summaries']['last_conversation'], False
                    
                    data = await response.json()
                    
                    if 'error' in data:
                        print(f"Summary Error: {data['error']}")
                        return user_state['summaries']['relationship'], user_state['summaries']['last_conversation'], False
                    
                    if 'choices' not in data:
                        print("No summary response choices")
                        return user_state['summaries']['relationship'], user_state['summaries']['last_conversation'], False
                        
                    response_text = data['choices'][0]['message']['content']
                    print(f"Summary response received ({len(response_text)} chars)")

                    # Parse sections
                    relationship = ""
                    conversation = ""
                    sections = response_text.split("[")
                    
                    for section in sections:
                        if "RELATIONSHIP_SUMMARY]" in section:
                            relationship = section.split("]")[1].strip()
                            print(f"✓ Relationship summary parsed")
                        elif "CONVERSATION_SUMMARY]" in section:
                            conversation = section.split("]")[1].strip()
                            print(f"✓ Conversation summary parsed")

                    if not relationship or not conversation:
                        print("❌ Failed to parse summaries from response")
                        return None, None, False

                    print("✓ Summary update successful")
                    return relationship, conversation, True

        except Exception as e:
            print(f"Error in update_summaries: {e}")
            traceback.print_exc()
            return None, None, False

    @staticmethod
    def extract_section(text: str, section: str) -> str:
        try:
            start = text.index(f"[{section}]") + len(section) + 2
            end = text.index("[", start) if "[" in text[start:] else len(text)
            return text[start:end].strip()
        except ValueError:
            return ""

    async def get_idle_message(self) -> str:
        """Get a random idle message from predefined list"""
        return random.choice(IDLE_MESSAGES)

    async def merge_summaries(self, summary1: Dict, summary2: Dict) -> Dict:
        """Merge two sets of summaries using AI to create a coherent combined summary"""
        try:
            prompt = {
                "model": "qwen/qwen3-30b-a3b:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an analyzer. Combine two sets of user summaries into a single coherent summary."
                    },
                    {
                        "role": "user",
                        "content": f"""
Combine these two summaries of the same user from different platforms into a single coherent summary:

[SUMMARY SET 1]
Relationship: {summary1['relationship']}
Last Conversation: {summary1['last_conversation']}

[SUMMARY SET 2]
Relationship: {summary2['relationship']}
Last Conversation: {summary2['last_conversation']}

Provide the combined summary in this format:
RELATIONSHIP: (combined relationship summary)
CONVERSATION: (combined conversation summary)
"""
                    }
                ]
            }

            print("\n=== MERGE SUMMARIES ===")
            print(f"Merging summaries for user from multiple platforms")

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.summary_headers, json=prompt) as response:
                    print(f"API Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content']
                        
                        relationship = ""
                        conversation = ""
                        
                        for line in response_text.split('\n'):
                            if line.startswith('RELATIONSHIP:'):
                                relationship = line.replace('RELATIONSHIP:', '').strip()
                                print(f"✓ Merged relationship summary")
                            elif line.startswith('CONVERSATION:'):
                                conversation = line.replace('CONVERSATION:', '').strip()
                                print(f"✓ Merged conversation summary")
                        
                        return {
                            "relationship": relationship or summary1['relationship'],
                            "last_conversation": conversation or summary1['last_conversation']
                        }

            return summary1  # Fallback to first summary if API call fails
        except Exception as e:
            print(f"Error merging summaries: {e}")
            return summary1  # Fallback to first summary
