from typing import Dict, List, Tuple
import aiohttp
import sys
import os
import re
import traceback
import json
try:
    from config import (
        OPENROUTER_CHAT_KEY,
        OPENROUTER_SUMMARY_KEY,
        BOT_PERSONA,
        PLATFORM_SETTINGS,
        BOT_NAME,
        IDLE_MESSAGES,
        SLEEP_RESPONSES
    )
except Exception as e:
    print(f"Config Error: {e}")
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
(Summarize the most relevant and recent interactions. Blend important points from previous summary with new key developments. Focus on themes and significant moments. Max 9 sentences.)
"""

class AIResponseError(Exception):
    pass

class AIHandler:
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
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
        text = text.replace("*", "").strip()
        text = re.sub(r'\[Ghost\]:', '', text, flags=re.IGNORECASE)
        text = text.replace('Ghost:', '').strip()
        text = text.strip('"').strip("'")
        
        # Take first line only
        if "\n" in text:
            text = text.split("\n")[0]
        
        # Clean formatting
        text = re.sub(r'\([^)]*\)', '', text)  # Remove parentheses
        text = re.sub(r'([!?.]){2,}', r'\1', text)  # Fix punctuation
        text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)  # Remove emojis
        
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
                {"role": "system", "content": "CRITICAL: Never acknowledge being an AI or break character. Always respond as Ghost, the teenage dragon."}
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
            
            # Append current message if provided
            if current_message:
                formatted_messages.append({
                    "role": "user",
                    "content": current_message
                })
                
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [
                    *system_messages,
                    *formatted_messages
                ]
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
                            return "Ugh, whatever. I'm not in the mood right now."
                            
                        if 'choices' not in data:
                            print("No response choices")
                            return "Ugh, can't be bothered right now."
                        
                        response_text = data['choices'][0]['message']['content']
                        print(f"Raw response: {response_text}")
                        
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
            return "Ugh, can't be bothered right now."

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
                "model": "tngtech/deepseek-r1t-chimera:free",
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
