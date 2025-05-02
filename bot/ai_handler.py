
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
(Summarize the most relevant and recent interactions. Blend important points from previous summary with new key developments. Focus on themes and significant moments. Max 3 sentences.)

[CHANGES_DETECTED]
(YES or NO - indicate if there were meaningful changes in relationship dynamic or conversation tone)
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

    async def get_chat_response(self, user_state: Dict) -> str:
        try:
            print("\n=== Message ===")
            messages = user_state.get('recent_messages', [])
            current_message = messages[-1]['content'] if messages else ""
            username = user_state.get('username', '').lower()
            platform = user_state.get('platform', 'discord')
            
            print(f"Platform: {platform}")
            print(f"User: {username}")
            print(f"Content: {current_message}")
            
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
            
            # Add platform-specific constraints
            platform = user_state.get('platform', 'discord')
            if platform == 'twitch':
                system_messages.append({
                    "role": "system",
                    "content": "IMPORTANT: Keep your actual response messages (excluding any analysis, summaries, or system info) under 500 characters for Twitch chat. You can think longer thoughts, but your direct replies must be concise."
                })
            
            # Add user contexts to system messages with improved formatting
            for context in user_contexts:
                context_parts = []
                username = context['username']
                
                # Start with user identification
                if context['is_sender']:
                    context_parts.append(f"IMPORTANT USER CONTEXT - Current Speaker: {username}")
                else:
                    context_parts.append(f"IMPORTANT USER CONTEXT - Mentioned User: {username}")
                
                # Add special user info if available
                if context['special_info']:
                    # Get full user data to include variants
                    user_data = self.special_users.get(self.variant_lookup.get(username, username))
                    if user_data:
                        context_parts.append(f"ROLE: {context['special_info']['role']}")
                        context_parts.append(f"CONTEXT: {context['special_info']['context']}")
                        variants = [v for v in user_data['variants'] if v.lower() != username.lower()]
                        if variants:
                            context_parts.append(f"ALSO KNOWN AS: {', '.join(variants)}")
                
                # Add relationship history
                if context['relationship']:
                    context_parts.append(f"RECENT DYNAMIC: {context['relationship']}")
                
                system_messages.append({
                    "role": "system",
                    "content": "\n".join(context_parts)
                })
            
            # Add recent conversation context if available
            if user_state.get('summaries', {}).get('last_conversation'):
                system_messages.append({
                    "role": "system", 
                    "content": f"RECENT CONVERSATION CONTEXT: {user_state['summaries']['last_conversation']}"
                })
            
            payload = {
                "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1:free",
                "messages": [
                    *system_messages,
                    *formatted_messages
                ]
            }

            # Log full request details
            print("\n=== Chat Request ===")
            print(f"Platform: {platform}")
            print(f"Username: {username}")
            print(f"Message count: {len(formatted_messages)}")
            
            print("\n=== System Messages ===")
            for i, msg in enumerate(system_messages):
                print(f"\nSystem Message {i + 1}:")
                print(msg['content'])
            
            print("\n=== Chat History ===")
            for msg in formatted_messages:
                print(f"\n[{msg['role']}]")
                print(msg['content'])
            
            print("\n=== Full Request ===")
            print(json.dumps(payload, indent=2))
            
            print(f"\nTotal Request Size: {len(str(payload))} characters")

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.chat_headers, json=payload) as response:
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
                            
                        print("\n=== API Response ===")
                        print(json.dumps(data, indent=2))
                        
                        response_text = data['choices'][0]['message']['content']
                        print(f"\nRaw Response: {repr(response_text)}")
                        
                        response_text = self.clean_response(response_text)
                        print(f"\nCleaned Response: {repr(response_text)}")
                        
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
            print("\n=== Summary Update ===")
            
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

            # Log details of summary request
            print("\n=== Summary Request ===")
            print(json.dumps({
                "model": prompt["model"],
                "message_count": len(prompt["messages"]),
                "request_size": len(str(prompt)),
                "current_relationship_length": len(user_state['summaries']['relationship']),
                "current_conversation_length": len(user_state['summaries']['last_conversation']),
                "new_messages": len(formatted_messages.split('\n'))
            }, indent=2))
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.summary_headers, json=prompt) as response:
                    print(f"\nAPI Response Status: {response.status}")
                    
                    if response.status != 200:
                        print(f"Summary API error: {response.status}")
                        return user_state['summaries']['relationship'], user_state['summaries']['last_conversation'], False
                    
                    data = await response.json()
                    print("\n=== Summary API Response ===")
                    print(json.dumps(data, indent=2))
                    
                    if 'error' in data:
                        print(f"\nSummary Error: {data['error']}")
                        return user_state['summaries']['relationship'], user_state['summaries']['last_conversation'], False
                    
                    if 'choices' not in data:
                        print("\nNo summary response choices")
                        return user_state['summaries']['relationship'], user_state['summaries']['last_conversation'], False
                        
                    response_text = data['choices'][0]['message']['content']
                    
                    print("\n=== Summary Response ===")
                    print(f"Raw response: {repr(response_text[:200])}...")

                    # Parse sections
                    relationship = ""
                    conversation = ""
                    changes = False
                    sections = response_text.split("[")
                    
                    print("\nParsing sections:")
                    for section in sections:
                        if "RELATIONSHIP_SUMMARY]" in section:
                            relationship = section.split("]")[1].strip()
                            print(f"Relationship: {relationship[:100]}...")
                        elif "CONVERSATION_SUMMARY]" in section:
                            conversation = section.split("]")[1].strip()
                            print(f"Conversation: {conversation[:100]}...")
                        elif "CHANGES_DETECTED]" in section:
                            changes_text = section.split("]")[1].strip().upper()
                            changes = "YES" in changes_text
                            print(f"Changes detected: {changes}")

                    print("\n=== Summary Results ===")
                    print(f"Changed: {'Yes' if changes else 'No'}")

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

            print("\n=== Merge Request ===")
            print(json.dumps({
                "model": prompt["model"],
                "summary1_length": len(summary1['relationship']) + len(summary1['last_conversation']),
                "summary2_length": len(summary2['relationship']) + len(summary2['last_conversation'])
            }, indent=2))

            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=self.summary_headers, json=prompt) as response:
                    print(f"\nAPI Response Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print("\n=== Merge API Response ===")
                        print(json.dumps(data, indent=2))
                        
                        response_text = data['choices'][0]['message']['content']
                        print(f"\nRaw merge response: {repr(response_text)}")
                        
                        relationship = ""
                        conversation = ""
                        
                        print("\nParsing merge response:")
                        for line in response_text.split('\n'):
                            if line.startswith('RELATIONSHIP:'):
                                relationship = line.replace('RELATIONSHIP:', '').strip()
                                print(f"Relationship: {relationship[:100]}...")
                            elif line.startswith('CONVERSATION:'):
                                conversation = line.replace('CONVERSATION:', '').strip()
                                print(f"Conversation: {conversation[:100]}...")
                        
                        return {
                            "relationship": relationship or summary1['relationship'],
                            "last_conversation": conversation or summary1['last_conversation']
                        }

            return summary1  # Fallback to first summary if API call fails
        except Exception as e:
            print(f"Error merging summaries: {e}")
            return summary1  # Fallback to first summary
