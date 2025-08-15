# Ghost Bot - Cross-Platform AI Character Bot

Ghost is an AI-powered character bot that maintains consistent persona and memory across Discord and Twitch platforms.

## Table of Contents

- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Core Systems](#core-systems)
  - [State Management](#state-management)
  - [AI Handler](#ai-handler)
  - [User Recognition](#user-recognition)
- [Platform Integration](#platform-integration)
  - [Discord Bot](#discord-bot)
  - [Twitch Bot](#twitch-bot)
  - [Cross-Platform Features](#cross-platform-features)
- [Features & Usage](#features--usage)
- [Technical Implementation](#technical-implementation)

## Setup & Installation

1. Install required packages:

```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:

```env
DISCORD_TOKEN=your_discord_token
DISCORD_GUILD_ID=your_guild_id
TWITCH_TOKEN=your_twitch_token
TWITCH_CLIENT_ID=your_client_id
TWITCH_CHANNEL=your_channel
OPENROUTER_CHAT_KEY=your_openrouter_key
OPENROUTER_SUMMARY_KEY=your_openrouter_key
```

3. Configure special users in `special_users.json`:

```json
{
  "username": {
    "variants": ["main_username", "alt_username"],
    "role": "user_role",
    "context": "user specific context"
  }
}
```

## Core Systems

### State Management

The StateManager (`state_manager.py`) is the core component that maintains user states and cross-platform memory.

#### Key Features:

- **User State Tracking**: Maintains conversation history, relationships, and user info
- **Cross-Platform Linking**: Links Discord and Twitch accounts for unified user experience
- **State Persistence**: Saves and loads states from disk
- **Auto-Linking**: Automatically links accounts based on username matching

#### User State Structure:

```python
{
    "user_id": str,
    "username": str,
    "platform": str,
    "identifiers": {
        "platform_name": {
            "user_id": str,
            "username": str,
            "nickname": str,
            "display_name": str
        }
    },
    "summaries": {
        "relationship": str,
        "last_conversation": str,
        "last_updated": datetime
    },
    "recent_messages": List[Message],
    "message_count": int
}
```

### AI Handler

The AIHandler (`ai_handler.py`) manages all AI interactions and maintains Ghost's persona.

#### Features:

- **Persona Maintenance**: Ensures consistent character behavior
- **Context Management**: Incorporates user relationships and history
- **Special User Recognition**: Handles special user interactions differently
- **Summary Generation**: Creates and updates relationship summaries
- **Response Processing**: Cleans and formats AI responses

#### Persona Implementation:

```python
BOT_PERSONA = """
You are Ghost, a teenage dragon with a rebellious and sarcastic personality.
Core traits:
- Grumpy but secretly caring
- Sarcastic and witty
- Protective of certain users (especially "mother")
- Maintains tough exterior while having soft spots
- Never breaks character or acknowledges being AI
"""

# Response cleaning to maintain character
def clean_response(self, text: str) -> str:
    # Remove AI patterns
    text = text.replace("As an AI", "")
    text = text.replace("I am a bot", "")

    # Remove excessive formatting
    text = re.sub(r'\*{2,}', '*', text)
    text = re.sub(r'_{2,}', '_', text)

    # Keep character-appropriate emotes
    allowed_emotes = {'😤', '😒', '🙄', '💤'}
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)

    return text.strip()
```

#### Relationship Management:

```python
# Example relationship summary prompt
SUMMARY_UPDATE_PROMPT = """
[CURRENT STATE]
Relationship: {current_relationship}
Last Chat: {last_conversation}

[NEW MESSAGES]
{messages}

Update while maintaining:
1. Consistent personality
2. Memory of past interactions
3. Special relationships (mother, friends, rivals)
4. Character-appropriate emotions
"""

# Merge relationship data across platforms
async def merge_summaries(self, discord_summary, twitch_summary):
    # Combine learnings while maintaining character consistency
    # Prefer stronger/older relationship if conflicts exist
    merged = await self.ai_handler.merge_contexts(
        discord_summary,
        twitch_summary
    )
    return merged
```

#### Message Processing Flow:

1. Extract user context and special user info
2. Format conversation history
3. Generate response maintaining character
4. Clean and validate response
5. Update relationship summaries

### User Recognition

#### Special Users System:

- Variant-based username matching
- Role-specific interactions
- Custom context per user
- Cross-platform identity tracking

## Platform Integration

### Discord Bot

The Discord bot (`bot.py`) handles Discord-specific interactions.

#### Commands:

- `/link_twitch`: Link Discord account with Twitch
- `/unlink_accounts`: Unlink Discord and Twitch accounts
- `/limits`: Check API usage limits
- `/update_summary`: Force update user summaries

#### Features:

- Message response to mentions and keywords
- Auto-linking with Twitch accounts
- Command handling
- Rate limiting

### Twitch Bot

The Twitch bot (`twitch_handler.py`) manages Twitch chat interactions.

#### Features:

- Chat message response
- Account linking confirmation
- Cross-platform state sharing
- Channel-specific settings

### Cross-Platform Features

#### Account Linking:

1. Discord user initiates link with `/link_twitch`
2. System creates pending link request
3. User confirms in Twitch chat
4. States are merged and maintained across platforms

#### Shared State:

- Conversation history
- Relationship dynamics
- User recognition
- Special user status

## Features & Usage

### Basic Interaction:

- Mention "ghost" in message
- Direct mention (@Ghost)
- DM the bot
- Use commands

### Account Management:

```bash
# Link accounts
/link_twitch username  # On Discord
!confirm_link         # On Twitch

# Unlink accounts
/unlink_accounts     # On Discord
```

### State Updates:

- Automatic updates based on interaction frequency
- Manual updates via command
- Cross-platform state synchronization

## Technical Implementation

### State Saving/Loading:

```python
# Save format (user_states.json)
{
    "discord_123456789": {  # Discord user
        "user_id": "123456789",
        "username": "username",
        "platform": "discord",
        "identifiers": {
            "discord": {
                "user_id": "123456789",
                "username": "username",
                "nickname": "nick",
                "display_name": "display"
            }
        },
        "summaries": {
            "relationship": "Current relationship dynamic...",
            "last_conversation": "Recent interaction summary...",
            "last_updated": "2025-04-29T13:30:00"
        }
    },
    "twitch_987654321": {  # Linked Twitch account
        # Similar structure
    },
    "pending_links": {
        "twitch_username": "discord_user_id"
    }
}
```

### Special Users Configuration:

```json
{
  "swastik": {
    "variants": ["swastikgoomber", "swasgoomber", "swastik"],
    "role": "vip",
    "context": "loves potatoes and willing participant in choccy milk heist"
  },
  "lilly": {
    "variants": ["lillyyen", "lillyyenvt", "lilly"],
    "role": "mother",
    "context": "This is your mother/captain. You respect her and have a special bond."
  }
}
```

### Message Flow:

1. **Message Received**:

   ```python
   # Discord
   @bot.event
   async def on_message(message):
       if message.author == bot.user:
           return

       if should_respond:  # @mention or "ghost" in message
           user_state = await state_manager.get_user_state(
               str(message.author.id),
               message.author.name,
               "discord"
           )
   ```

2. **Context Processing**:

   ```python
   # Extract mentioned users and their contexts
   mentioned_users = ai_handler.extract_usernames(message.content)
   user_contexts = []
   for user in mentioned_users:
       context = ai_handler.get_user_context(user)
       user_contexts.append(context)
   ```

3. **AI Response**:

   ```python
   response = await ai_handler.get_chat_response({
       "username": username,
       "recent_messages": messages,
       "summaries": summaries,
       "platform": platform
   })
   ```

4. **State Update**:
   ```python
   if user_state.needs_summary_update():
       success, msg = await state_manager.update_user_state(platform_key)
   ```

### AI Model Usage & Prompting

#### Model Configuration:

```python
CHAT_MODEL = "sophosympatheia/rogue-rose-103b-v0.2:free"  # Main chat interactions
SUMMARY_MODEL = "mistralai/mistral-7b-instruct:free"      # Relationship summaries

# System messages for different purposes
CHAT_SYSTEM_PROMPT = [
    {"role": "system", "content": BOT_PERSONA},
    {"role": "system", "content": "CRITICAL: Never acknowledge being AI. Always respond as Ghost."}
]

SUMMARY_SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are an analyzer creating concise relationship summaries."
}
```

### Rate Limiting & Recovery:

```python
# Rate limit tracking
self.daily_requests = 0  # Resets daily
self.minute_requests = deque(maxlen=20)  # Rolling window

# Check limits with recovery responses
if self.daily_requests >= 200:
    return random.choice([
        "*yawns* Too tired... wake me up tomorrow...",
        "Zzzz... *curls up and ignores everyone*",
        "*grumbles something about needing sleep*"
    ])

if len(self.minute_requests) >= 20:
    return random.choice([
        "Give me a minute to catch my breath, geez!",
        "*takes a quick power nap*",
        "Too many questions! I need a break."
    ])

# Auto-recovery
while self.minute_requests and (current_time - self.minute_requests[0]).seconds > 60:
    self.minute_requests.popleft()
```

#### Prompt Construction:

```python
def build_chat_prompt(self, user_state: Dict) -> List[Dict]:
    """Build prompt maintaining character and context"""
    messages = [
        *CHAT_SYSTEM_PROMPT,
        # User context
        {"role": "system", "content": f"SPEAKER: {user_state['username']}"},
    ]

    # Add special relationships
    if special_info := user_state.get('special_info'):
        messages.append({
            "role": "system",
            "content": f"RELATIONSHIP: {special_info['role']}\n{special_info['context']}"
        })

    # Add recent interaction history
    if relationship := user_state.get('summaries', {}).get('relationship'):
        messages.append({
            "role": "system",
            "content": f"RECENT DYNAMIC: {relationship}"
        })

    return messages
```

### Common Interaction Examples:

1. **Basic Chat**:

   ```
   User: ghost, how are you today?
   Ghost: *grumbles* Could be better if people didn't ask how I am every five minutes.
   ```

2. **Special User Interaction**:

   ```
   Lilly: ghost, behave yourself
   Ghost: *huffs but shows clear respect* Yes, mom... but I still don't like it.
   ```

3. **Cross-Platform Linking**:

   ```
   Discord: /link_twitch swasgoomber
   Bot: Link request created! Type !confirm_link in Twitch chat.

   Twitch: !confirm_link
   Bot: Accounts successfully linked! History and relationships merged.
   ```

### Error Handling:

- Graceful degradation
- Fallback responses
- State preservation
- Error logging

---

## Directory Structure

```
bot/
├── main.py           # Entry point
├── bot.py           # Discord bot implementation
├── twitch_handler.py # Twitch bot implementation
├── ai_handler.py    # AI processing
├── state_manager.py # State management
├── config.py        # Configuration
├── .env            # Environment variables
├── special_users.json # User data
└── logs/           # Log directory
    └── auto_linking.log
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## Deployment Guide

### Prerequisites

- Python 3.11.x
- Git repository
- Render.com account
- Discord bot token
- Twitch API credentials
- OpenRouter API key

### Local Testing (Windows)

1. Clone repository and install dependencies:

```powershell
git clone <repository-url>
cd bot
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:

```env
DISCORD_TOKEN=your_discord_token
DISCORD_GUILD_ID=your_guild_id
TWITCH_TOKEN=your_twitch_token
TWITCH_CLIENT_ID=your_client_id
TWITCH_CHANNEL=your_channel
OPENROUTER_CHAT_KEY=your_openrouter_key
OPENROUTER_SUMMARY_KEY=your_openrouter_key
```

3. Run test script:

```powershell
.\test_deployment.ps1
```

### Render Deployment Steps

1. **Initial Setup**

   - Create new Web Service
   - Connect GitHub repository
   - Select Python environment

2. **Configuration**

   ```yaml
   Name: ghost-bot
   Environment: Python 3.11
   Build Command: pip install -r requirements.txt
   Start Command: python main.py
   Instance Type: Free
   ```

3. **Environment Variables**

   - Add all variables from `.env`
   - Add `RENDER=true`
   - Add any additional platform-specific settings
