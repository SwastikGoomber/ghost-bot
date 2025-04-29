import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import os
import traceback
import asyncio

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auto_linking.log'),
        logging.StreamHandler()
    ]
)

class UserState:
    def __init__(self, user_id: str, username: str, platform: str, nickname: str = None):
        # Primary identifiers dictionary to store all platform info
        self.identifiers = {
            platform: {
                'user_id': user_id,
                'username': username,
                'nickname': nickname,
                'display_name': nickname or username
            }
        }
        
        self.primary_name = username
        self.name_variants = self._generate_variants(username)
        self.summaries = {
            "relationship": "New user, relationship not established yet.",
            "last_conversation": "First interaction.",
            "last_updated": datetime.now().isoformat()
        }
        self.recent_messages = []
        self.message_count = 0
        self.last_interaction = datetime.now()

    def _generate_variants(self, username: str) -> list:
        variants = [username.lower()]
        if ' ' in username:
            variants.append(username.split()[0].lower())
        for sep in ['.', '_', '-']:
            if sep in username:
                variants.append(username.split(sep)[0].lower())
        return list(set(variants))

    def link_platform(self, platform: str, user_id: str, username: str, nickname: str = None):
        """Link another platform's identity to this user"""
        # Add the new platform identifier
        self.identifiers[platform] = {
            'user_id': user_id,
            'username': username,
            'nickname': nickname,
            'display_name': nickname or username
        }
        
        # Update name variants
        self.name_variants.extend(self._generate_variants(username))
        if nickname:
            self.name_variants.extend(self._generate_variants(nickname))
        self.name_variants = list(set(self.name_variants))  # Remove duplicates
        
        # Debug logging
        platforms = ', '.join(self.identifiers.keys())
        logging.info(f"Linked platforms for user {self.primary_name}: {platforms}")

    async def merge_with(self, other_state: 'UserState', ai_handler):
        """Merge data from another user state"""
        # Merge identifiers
        self.identifiers.update(other_state.identifiers)
        
        # Merge name variants
        self.name_variants.extend(other_state.name_variants)
        self.name_variants = list(set(self.name_variants))
        
        # Merge messages and update count
        self.recent_messages.extend(other_state.recent_messages)
        self.recent_messages.sort(key=lambda x: datetime.fromisoformat(x['timestamp']))
        self.message_count += other_state.message_count
        
        # Take the most recent interaction time
        other_interaction = other_state.last_interaction
        if isinstance(other_interaction, str):
            other_interaction = datetime.fromisoformat(other_interaction)
        if other_interaction > self.last_interaction:
            self.last_interaction = other_interaction
        
        # Merge summaries using AI
        merged_summaries = await ai_handler.merge_summaries(
            self.summaries,
            other_state.summaries
        )
        self.summaries = merged_summaries

    def add_message(self, content: str, from_bot: bool, username: str):
        """Add a message to the recent messages list"""
        message = {
            "content": content,
            "from_bot": from_bot,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }
        self.recent_messages.append(message)
        self.message_count += 1
        self.last_interaction = datetime.now()
        print(f"Added message to {username}. Messages: {len(self.recent_messages)}, Count: {self.message_count}")
        
        # The actual summary update will be triggered from bot.py after checking needs_summary_update()

    def needs_summary_update(self) -> bool:
        """Check if we need to update summaries based on message count and time"""
        # Count messages since last summary update
        last_update = datetime.fromisoformat(self.summaries.get('last_updated', '2000-01-01T00:00:00'))
        messages_since_update = 0
        
        for msg in self.recent_messages:
            msg_time = datetime.fromisoformat(msg['timestamp'])
            if msg_time > last_update:
                messages_since_update += 1
        
        # Update if we have 6 or more messages since last summary
        if messages_since_update >= 6:
            print(f"Summary update needed: {messages_since_update} messages since last update")
            return True
        
        # Update if it's been more than 30 minutes since last summary
        time_diff = datetime.now() - last_update
        if time_diff.total_seconds() > 1800:  # 30 minutes
            print("Summary update needed: Over 30 minutes since last update")
            return True
            
        print(f"No summary update needed: {messages_since_update} messages since last update")
        return False

    def to_dict(self) -> dict:
        """Convert state to dictionary for serialization"""
        # Get the first platform's data
        first_platform = list(self.identifiers.keys())[0]
        first_platform_data = self.identifiers[first_platform]
        
        return {
            "user_id": first_platform_data['user_id'],
            "username": self.primary_name,
            "platform": first_platform,
            "identifiers": self.identifiers,
            "summaries": self.summaries,
            "recent_messages": self.recent_messages,
            "message_count": self.message_count,
            "last_interaction": self.last_interaction.isoformat()
        }

class StateManager:
    # Class constant for state file
    USER_STATES_FILE = 'user_states.json'

    def __init__(self, ai_handler=None):
        self.users = {}
        self.pending_links = {}
        self.ai_handler = ai_handler
        self._initialized = False  # Track initialization state
        self.db = None
        
        # Determine storage mode
        if os.environ.get('MONGODB_URI'):
            from db import MongoDB
            self.db = MongoDB()
            
        # Do not auto-load states here - wait for explicit load_states call

    async def initialize(self):
        """Initialize database connection if needed"""
        if self.db is not None:
            try:
                print("Connecting to MongoDB...")
                await self.db.connect()
                is_connected = await self.db.ping()
                if is_connected:
                    print("✓ Connected to MongoDB")
                else:
                    print("❌ MongoDB ping failed")
            except Exception as e:
                print(f"❌ MongoDB connection failed: {e}")
                self.db = None

    def __del__(self):
        """Cleanup database connection"""
        if self.db:
            self.db.close()

    async def save_states(self):
        """Save all states"""
        try:
            data = {}
            processed_users = set()  # Track users we've saved
            
            # First pass: Save Discord states
            for user_id, user_state in self.users.items():
                if 'discord' in user_state.identifiers:
                    discord_id = user_state.identifiers['discord']['user_id']
                    discord_key = f"discord_{discord_id}"
                    data[discord_key] = user_state.to_dict()
                    processed_users.add(id(user_state))
            
            # Second pass: Save Twitch-only states
            for user_id, user_state in self.users.items():
                if id(user_state) not in processed_users:
                    # This is a Twitch-only state
                    data[user_id] = user_state.to_dict()

            # Add pending links if any exist
            if self.pending_links:
                data['pending_links'] = self.pending_links
                
            # Convert datetime objects to ISO format strings
            data = json.loads(json.dumps(data, default=str))
            
            # Save to storage
            if self.db is not None:
                await self.db.save_states(data)
            else:
                with open(self.USER_STATES_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to save states: {e}")
            traceback.print_exc()

    async def load_states(self):
        """Load states from storage"""
        print("\n=== Loading states ===")
        self.users = {}
        self.pending_links = {}

        # Initialize MongoDB connection if needed
        if self.db is not None:
            await self.initialize()
        try:
            # Load from MongoDB if available, otherwise from file
            if self.db:
                print("Loading from MongoDB")
                data = await self.db.load_states()
            else:
                if not os.path.exists(self.USER_STATES_FILE):
                    print(f"No state file found at {self.USER_STATES_FILE}")
                    return
                    
                print(f"Loading from {self.USER_STATES_FILE}")
                with open(self.USER_STATES_FILE, 'r') as f:
                    data = json.load(f)
            
            # Load pending links if any
            self.pending_links = data.get('pending_links', {})
            
            # First pass: Load and create Discord states
            discord_states = {}  # Map Discord IDs to states
            for key, user_data in data.items():
                if key == 'pending_links':
                    continue
                    
                if key.startswith('discord_'):
                    # Create Discord state
                    user_state = UserState(
                        user_id=user_data['user_id'],
                        username=user_data['username'],
                        platform='discord'
                    )
                    # Restore fields
                    user_state.identifiers = user_data['identifiers']
                    user_state.summaries = user_data['summaries']
                    user_state.recent_messages = user_data['recent_messages']
                    user_state.message_count = user_data['message_count']
                    user_state.last_interaction = datetime.fromisoformat(user_data['last_interaction'])
                    
                    # Store state and track references
                    self.users[key] = user_state
                    discord_states[user_data['user_id']] = user_state
            
            unique_states = set()  # Track unique UserState objects
            
            # Second pass: Link Twitch states or create new ones
            for key, user_data in data.items():
                if key == 'pending_links' or key.startswith('discord_'):
                    continue
                    
                # Check if this Twitch user should be linked to a Discord account
                if 'discord' in user_data['identifiers']:
                    discord_id = user_data['identifiers']['discord']['user_id']
                    if discord_id in discord_states:
                        # Link to existing Discord state
                        self.users[key] = discord_states[discord_id]
                        unique_states.add(id(discord_states[discord_id]))
                        continue
                
                # If we get here, this is a Twitch-only user
                user_state = UserState(
                    user_id=user_data['user_id'],
                    username=user_data['username'],
                    platform='twitch'
                )
                # Restore fields
                user_state.identifiers = user_data['identifiers']
                user_state.summaries = user_data['summaries']
                user_state.recent_messages = user_data['recent_messages']
                user_state.message_count = user_data['message_count']
                user_state.last_interaction = datetime.fromisoformat(user_data['last_interaction'])
                
                # Store state and track it
                self.users[key] = user_state
                unique_states.add(id(user_state))
            
            # Count unique objects by ID
            unique_states = {id(state) for state in self.users.values()}
            print(f"Loaded {len(unique_states)} unique users and {len(self.pending_links)} pending links")
        except Exception as e:
            print(f"Error loading states: {str(e)}")
            traceback.print_exc()
            logging.error(f"Failed to load states: {e}")
            self.users = {}
            self.pending_links = {}

    async def unlink_accounts(self, platform_key: str) -> bool:
        """Unlink a user's Discord and Twitch accounts"""
        try:
            user_state = self.users.get(platform_key)
            if not user_state:
                return False

            # Get both platform IDs
            discord_data = user_state.identifiers.get('discord')
            twitch_data = user_state.identifiers.get('twitch')

            if not (discord_data and twitch_data):
                return False  # Not a linked account

            # Create separate states for each platform
            discord_key = f"discord_{discord_data['user_id']}"
            twitch_key = f"twitch_{twitch_data['user_id']}"

            # Create new state for Twitch
            twitch_state = UserState(
                user_id=twitch_data['user_id'],
                username=twitch_data['username'],
                platform='twitch'
            )
            # Copy current messages and summaries
            twitch_state.recent_messages = user_state.recent_messages.copy()
            twitch_state.summaries = user_state.summaries.copy()
            twitch_state.message_count = user_state.message_count

            # Update Discord state
            user_state.identifiers = {'discord': discord_data}  # Keep only Discord

            # Update users dictionary
            self.users[discord_key] = user_state
            self.users[twitch_key] = twitch_state

            await self.save_states()
            return True
        except Exception as e:
            logging.error(f"Failed to unlink accounts: {e}")
            return False

    async def create_link_request(self, discord_id: str, twitch_username: str) -> bool:
        """Create a pending link request"""
        try:
            self.pending_links[twitch_username.lower()] = discord_id
            await self.save_states()  # Save immediately after creating request
            logging.info(f"Created link request: Discord {discord_id} -> Twitch {twitch_username}")
            return True
        except Exception as e:
            logging.error(f"Failed to create link request: {e}")
            return False

    async def confirm_link_request(self, twitch_id: str, twitch_username: str) -> tuple[bool, str]:
        """Confirm and process a link request"""
        twitch_username = twitch_username.lower()
        
        if twitch_username not in self.pending_links:
            return False, "No pending link request found"

        discord_id = self.pending_links[twitch_username]
        discord_key = f"discord_{discord_id}"
        twitch_key = f"twitch_{twitch_id}"

        if discord_key not in self.users:
            return False, "Discord user not found"

        try:
            # Always use Discord state as primary
            primary_state = self.users[discord_key]
            
            # If Twitch state exists, merge it into Discord state
            if twitch_key in self.users:
                twitch_state = self.users[twitch_key]
                # Merge using AI handler for summaries
                await primary_state.merge_with(twitch_state, self.ai_handler)
                del self.users[twitch_key]
            
            # Add Twitch identity to primary state
            primary_state.link_platform('twitch', twitch_id, twitch_username)
            
            # Both keys should reference the same state object
            self.users[discord_key] = primary_state
            self.users[twitch_key] = primary_state  # Same object, not a copy
            
            # Clean up pending link
            del self.pending_links[twitch_username]
            await self.save_states()
            
            return True, "Accounts successfully linked! Conversation history and summaries have been merged."
            
        except Exception as e:
            logging.error(f"Error confirming link: {e}")
            return False, f"Error linking accounts: {str(e)}"

    async def add_message(self, platform_key: str, content: str, from_bot: bool, username: str):
        """Add a message to user state"""
        message = {
            "content": content,
            "from_bot": from_bot,
            "username": username,
            "timestamp": datetime.now().isoformat()
        }

        # Update user state
        if platform_key in self.users:
            user_state = self.users[platform_key]
            user_state.recent_messages.append(message)
            user_state.message_count += 1
            user_state.last_interaction = datetime.now()
            print(f"Added message to {platform_key}. Messages: {len(user_state.recent_messages)}, Count: {user_state.message_count}")
            
            # Save state
            await self.save_states()

    async def update_user_state(self, platform_key: str) -> Tuple[bool, str]:
        """Update user state summaries"""
        try:
            print(f"\n=== DEBUG: Updating state for {platform_key} ===")
            user_state = self.users.get(platform_key)
            if not user_state:
                return False, "User not found."

            state_dict = user_state.to_dict()
            relationship, conversation, changes = await self.ai_handler.update_summaries(state_dict)

            # Check if we got valid summaries
            if relationship and conversation:
                print(f"Updating summaries for {platform_key}")
                print(f"Old relationship: {user_state.summaries['relationship']}")
                print(f"New relationship: {relationship}")
                print(f"Old conversation: {user_state.summaries['last_conversation']}")
                print(f"New conversation: {conversation}")

                if changes:
                    now = datetime.now()
                    
                    # Update summaries with current timestamp
                    user_state.summaries["relationship"] = relationship
                    user_state.summaries["last_conversation"] = conversation
                    user_state.summaries["last_updated"] = now.isoformat()
                    
                    # Keep only the 3 most recent messages and reset message count
                    user_state.recent_messages = user_state.recent_messages[-3:]
                    user_state.message_count = 0  # Reset count since last summary
                    
                    # Save immediately after updating
                    await self.save_states()
                    print(f"Successfully saved updated state for {platform_key}")
                    return True, "Summary updated successfully!"
                
                return False, "No significant changes detected."

            return False, "Failed to generate valid summaries."

        except Exception as e:
            print(f"Error updating user state: {e}")
            traceback.print_exc()
            return False, f"Error updating summaries: {str(e)}"

    def find_matching_user(self, username: str, nickname: str = None) -> UserState:
        """Find user by username or nickname across platforms"""
        search_terms = {username.lower()}
        if nickname:
            search_terms.add(nickname.lower())

        # Debug logging
        logging.info(f"Searching for user with terms: {search_terms}")
        logging.info(f"Current users: {[{k: v.identifiers} for k, v in self.users.items()]}")

        for user_id, user_state in self.users.items():
            for platform, data in user_state.identifiers.items():
                platform_username = data['username'].lower()
                # Safely handle nickname which might be None
                platform_nickname = data.get('nickname')
                if platform_nickname:
                    platform_nickname = platform_nickname.lower()
                
                logging.info(f"Checking {platform_username} ({platform_nickname}) against {search_terms}")
                
                if platform_username in search_terms or (platform_nickname and platform_nickname in search_terms):
                    logging.info(f"Found match! User ID: {user_id}")
                    return user_state
        
        logging.info("No matching user found")
        return None

    async def get_user_state(self, user_id: str, username: str, platform: str, nickname: str = None) -> tuple[UserState, str]:
        """Get or create user state, with potential auto-linking"""
        platform_key = f"{platform}_{user_id}"
        
        # Check if user exists with this platform ID
        if platform_key in self.users:
            user_state = self.users[platform_key]
            # If this is a linked account, ensure both discord and twitch keys point to the same state
            if 'twitch' in user_state.identifiers and 'discord' in user_state.identifiers:
                discord_id = user_state.identifiers['discord']['user_id']
                twitch_id = user_state.identifiers['twitch']['user_id']
                discord_key = f"discord_{discord_id}"
                twitch_key = f"twitch_{twitch_id}"
                # Make sure both keys point to the same state object
                self.users[discord_key] = user_state
                self.users[twitch_key] = user_state
            return user_state, None

        # Try to find existing user by username or nickname
        existing_user = self.find_matching_user(username, nickname)
        if existing_user:
            # Auto-linking happens here!
            existing_platform = list(existing_user.identifiers.keys())[0]
            existing_data = existing_user.identifiers[existing_platform]
            
            logging.info(f"Auto-linking new account with existing:\n"
                        f"  Original: {existing_platform}/{existing_data['username']} ({existing_data['user_id']})\n"
                        f"  New: {platform}/{username} ({user_id})")
            
            # Link the new platform to the existing user
            existing_user.link_platform(platform, user_id, username, nickname)
            
            # Update the users dictionary with the new platform key (same object reference)
            self.users[platform_key] = existing_user
            
            # Create notification message
            if platform == "discord":
                return existing_user, f"Discord account automatically linked with Twitch account {existing_data['username']}"
            else:
                return existing_user, f"Twitch account automatically linked with Discord account {existing_data['username']}"

        # Create new user state
        new_user = UserState(user_id, username, platform, nickname)
        self.users[platform_key] = new_user
        return new_user, None
