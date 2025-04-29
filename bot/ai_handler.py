
from typing import Dict, List, Tuple
import aiohttp
import sys
import os
import re
import traceback
import json
from config import (
    OPENROUTER_CHAT_KEY,
    OPENROUTER_SUMMARY_KEY,
    BOT_PERSONA,
    PLATFORM_SETTINGS,
    BOT_NAME,
    IDLE_MESSAGES,
    SLEEP_RESPONSES
)

# Add debug prints
print("Current working directory:", os.getcwd())
print("Python path:", sys.path)

try:
    from config import (
        OPENROUTER_CHAT_KEY,
        OPENROUTER_SUMMARY_KEY,
        BOT_PERSONA,
        PLATFORM_SETTINGS
    )
    print("Successfully imported config variables")
except Exception as e:
    print(f"Error importing from config: {e}")
    raise

import random

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
(Summarize the most relevant and recent interactions. Blend important points from previous summary with new key developments. Focus on themes and significant moments. Max 3 sentences.)

[CHANGES_DETECTED]
(YES or NO - indicate if there were meaningful changes in relationship dynamic or conversation tone)
"""

class AIResponseError(Exception):
    pass

class AIHandler:
    def __init__(self):
        print("Initializing AIHandler")
        print(f"PLATFORM_SETTINGS available: {PLATFORM_SETTINGS is not None}")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.chat_headers = {
            "Authorization": f"Bearer {OPENROUTER_CHAT_KEY}",
            "Content-Type": "application/json"
        }
        self.summary_headers = {
            "Authorization": f"Bearer {OPENROUTER_SUMMARY_KEY}",
            "Content-Type": "application/json"
        }
        
        # Load special users data
        self.special_users = self.load_special_users()  # Load from JSON file

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

    def extract_usernames(self, message: str) -> List[str]:
        """Extract usernames from message with variant matching"""
        found_users = set()
        message = message.lower()
        
        # Check for @mentions
        mentions = re.findall(r'@(\w+)', message)
        for mention in mentions:
            mention = mention.lower()
            # Check if mention matches any variant
            if mention in self.variant_lookup:
                found_users.add(self.variant_lookup[mention])
        
        # Check for username matches in text
        words = message.split()
        for word in words:
            # Remove common punctuation
            clean_word = re.sub(r'[,.!?]$', '', word.lower())
            if clean_word in self.variant_lookup:
                found_users.add(self.variant_lookup[clean_word])
        
        print(f"Username extraction debug:")
        print(f"Message: {message}")
        print(f"Found primary users: {found_users}")
        print(f"Variant lookup: {self.variant_lookup}")
        
        return list(found_users)

    def get_user_context(self, username: str, user_state: Dict = None) -> Dict:
        """Get context for a user including both special info and learned relationship"""
        username = username.lower().strip()  # Ensure case-insensitive comparison
        context = {
            "special_info": None,
            "relationship": None
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
        
        return context

    def format_messages(self, messages: List[Dict]) -> str:
        """Format messages for the summary prompt"""
        formatted = []
        for msg in messages:
            prefix = f"{msg['username']}: " if not msg['from_bot'] else "Ghost: "
            formatted.append(f"{prefix}{msg['content']}")
        return "\n".join(formatted)

    def clean_response(self, text: str) -> str:
        # Remove common AI patterns
        text = text.replace("USER:", "").replace("ASSISTANT:", "").strip()
        text = text.replace("*", "").strip()
        
        # Remove "Ghost:" prefix and quotes, including the bracketed version
        text = re.sub(r'\[Ghost\]:', '', text, flags=re.IGNORECASE)
        text = text.replace('Ghost:', '').strip()
        text = text.strip('"').strip("'")
        
        # Remove self-generated questions
        if "\n" in text:
            text = text.split("\n")[0]
        
        # Remove any explanation of actions or emotions
        text = re.sub(r'\([^)]*\)', '', text)
        
        # Remove excessive punctuation and emojis
        text = re.sub(r'([!?.]){2,}', r'\1', text)
        text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
        
        return text.strip()

    async def get_chat_response(self, user_state: Dict) -> str:
        try:
            print("\n=== SPECIAL USERS DEBUG ===")
            print(f"Loaded special users: {self.special_users}")
            
            messages = user_state.get('recent_messages', [])
            current_message = messages[-1]['content'] if messages else ""
            username = user_state.get('username', '').lower()
            
            print(f"Current username: {username}")
            print(f"Is username in special_users? {username in self.special_users}")
            
            # Debug logging for context gathering
            print("\n=== User Context Debug ===")
            print(f"Processing message from user: {username}")
            print(f"User state available: {bool(user_state)}")
            print(f"Message content: {current_message}")
            
            # First, always get the sender's context directly from username
            user_contexts = []
            sender_context = self.get_user_context(username, user_state)
            print(f"Sender context: {json.dumps(sender_context, indent=2)}")
            
            user_contexts.append({
                "username": username,
                "is_sender": True,
                **sender_context
            })
            
            # Then look for additional mentioned users in the message
            mentioned_users = self.extract_usernames(current_message)
            print(f"Extracted mentioned usernames: {mentioned_users}")
            
            # Log available special users for comparison
            print(f"Available special users: {list(self.special_users.keys())}")
            
            # Add mentioned users' context
            for mentioned_user in mentioned_users:
                if mentioned_user != username:  # Skip if it's the sender
                    mentioned_context = self.get_user_context(mentioned_user)
                    if mentioned_context["special_info"] or mentioned_context["relationship"]:
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
                {"role": "system", "content": "CRITICAL: Never acknowledge being an AI or break character. Always respond as Ghost, the teenage dragon."}
            ]
            
            # Add user contexts to system messages with improved formatting
            for context in user_contexts:
                context_parts = []
                context_parts.append(f"IMPORTANT USER CONTEXT - {context['username']}")
                if context['is_sender']:
                    context_parts.append("(Current Speaker)")
                
                if context['special_info']:
                    context_parts.append(f"CORE RELATIONSHIP: {context['special_info']['role']}")
                    context_parts.append(f"CONTEXT: {context['special_info']['context']}")
                
                if context['relationship']:
                    context_parts.append(f"RECENT DYNAMIC: {context['relationship']}")
                
                system_messages.append({
                    "role": "system",
                    "content": " | ".join(context_parts)
                })
            
            # Add recent conversation context if available
            if user_state.get('summaries', {}).get('last_conversation'):
                system_messages.append({
                    "role": "system", 
                    "content": f"RECENT CONVERSATION CONTEXT: {user_state['summaries']['last_conversation']}"
                })
            
            payload = {
                "model": "sophosympatheia/rogue-rose-103b-v0.2:free",
                "messages": [
                    *system_messages,
                    *formatted_messages
                ]
            }

            # Debug prints
            print("\nSystem Messages:")
            for msg in system_messages:
                print(f"- {msg['content']}")
            
            print("\nConversation Messages:")
            for msg in formatted_messages:
                print(f"- [{msg['role']}]: {msg['content']}")
            
            print("\nFull Payload:")
            print(json.dumps(payload, indent=2))
            print("\n=== END PROMPT ===\n")

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.chat_headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("\nAPI Response:", data)  # Debug print for API response
                        
                        if 'error' in data and data['error'].get('code') == 429:
                            print("Rate limit hit, using fallback response")
                            return random.choice(SLEEP_RESPONSES)
                        
                        if 'choices' not in data or not data['choices']:
                            print(f"Invalid API response: {data}")
                            return "Ugh, whatever. I'm not in the mood right now."
                        
                        response_text = data['choices'][0]['message']['content']
                        response_text = self.clean_response(response_text)
                        
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
            return "Ugh, can't be bothered right now."

    async def update_summaries(self, user_state: Dict) -> Tuple[str, str, bool]:
        try:
            print("\n=== DEBUG: update_summaries ===")
            print(f"User state keys: {user_state.keys()}")
            print(f"Recent messages count: {len(user_state.get('recent_messages', []))}")
            print(f"Recent messages: {json.dumps(user_state.get('recent_messages', []), indent=2)}")
            
            if not user_state.get('recent_messages'):
                print("Not enough messages for summary update - recent_messages is empty or None")
                return (
                    user_state['summaries']['relationship'],
                    user_state['summaries']['last_conversation'],
                    False
                )

            # Ensure we have at least 2 messages before proceeding
            if len(user_state['recent_messages']) < 2:
                print(f"Not enough messages for summary update - only have {len(user_state['recent_messages'])} messages")
                return (
                    user_state['summaries']['relationship'],
                    user_state['summaries']['last_conversation'],
                    False
                )

            formatted_messages = self.format_messages(user_state['recent_messages'])
            print(f"Formatted messages: {formatted_messages}")
            
            prompt = {
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an analyzer. Provide brief summaries of chat interactions."
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

            print("Sending summary update request with prompt:", prompt)  # Debug print

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.summary_headers, json=prompt) as response:
                    if response.status != 200:
                        print(f"Summary API error: {response.status}")
                        return user_state['summaries']['relationship'], user_state['summaries']['last_conversation'], False
                    
                    data = await response.json()
                    response_text = data['choices'][0]['message']['content']
                    
                    print("Raw API response: ", response_text)  # Debug print
                    
                    # Parse the response
                    relationship = ""
                    conversation = ""
                    changes = False

                    # Split response into sections
                    sections = response_text.split("[")
                    for section in sections:
                        if "RELATIONSHIP_SUMMARY]" in section:
                            relationship = section.split("]")[1].strip()
                        elif "CONVERSATION_SUMMARY]" in section:
                            conversation = section.split("]")[1].strip()
                        elif "CHANGES_DETECTED]" in section:
                            changes_text = section.split("]")[1].strip().upper()
                            changes = "YES" in changes_text

                    print(f"Parsed summaries:")
                    print(f"Relationship: {relationship}")
                    print(f"Conversation: {conversation}")
                    print(f"Changes detected: {changes}")

                    # Only return None values if parsing failed
                    if not relationship or not conversation:
                        print("Failed to parse summaries from response")
                        return None, None, False

                    return relationship, conversation, changes

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
                "model": "mistralai/mistral-7b-instruct:free",
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

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.summary_headers, json=prompt) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data['choices'][0]['message']['content']
                        
                        # Parse the response
                        relationship = ""
                        conversation = ""
                        
                        for line in response_text.split('\n'):
                            if line.startswith('RELATIONSHIP:'):
                                relationship = line.replace('RELATIONSHIP:', '').strip()
                            elif line.startswith('CONVERSATION:'):
                                conversation = line.replace('CONVERSATION:', '').strip()
                        
                        return {
                            "relationship": relationship or summary1['relationship'],
                            "last_conversation": conversation or summary1['last_conversation']
                        }

            return summary1  # Fallback to first summary if API call fails
        except Exception as e:
            print(f"Error merging summaries: {e}")
            return summary1  # Fallback to first summary
