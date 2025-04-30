# Ghost Bot Documentation

## System Architecture

### Storage

1. MongoDB Integration

   - States and messages stored in MongoDB using motor (async driver)
   - Automatic fallback to JSON if MongoDB unavailable

   Connection String Format:

   ```
   mongodb+srv://<username>:<password>@<cluster>.mongodb.net/ghost_bot
   ```

   Data Structure:

   ```json
   {
     "discord_123456": {
       "user_id": "123456",
       "username": "example",
       "platform": "discord",
       "summaries": {
         "relationship": "...",
         "last_conversation": "..."
       }
     }
   }
   ```

### Troubleshooting

1. Common Issues

   - **Empty Bot Responses**: Check API keys and model availability
   - **MongoDB Connection**: Verify URI and network access
   - **Missing Messages**: Check state_manager.py logs for auto-saving
   - **Rate Limits**: Monitor /limits command output

2. Debug Logs

   ```
   /logs/auto_linking.log - Account linking issues
   /logs/bot.log         - General bot operations
   stdout               - API requests and responses
   ```

3. Health Check Status
   ```json
   {
     "status": "healthy|degraded",
     "mongodb": "healthy|degraded|disabled"
   }
   ```

### Message Processing

1. System Messages (API Context)

   - **Base Persona** (config.py: BOT_PERSONA)

     - Core personality traits
     - Basic behavioral guidelines

   - **Character Enforcement** (ai_handler.py: get_chat_response())

     - Ensures staying in character
     - Prevents AI acknowledgment

   - **Platform Constraints** (ai_handler.py: get_chat_response())

     - Twitch: 500 character limit
     - Discord: Platform-specific features

   - **User Context** (Multiple Sources)
     - special_users.json: Core relationships
     - state_manager.py: Learned relationships
     - ai_handler.py: Context merging

2. Message History
   - Recent messages stored in user state
   - Summarized periodically
   - Used for context in future interactions

### Models & AI

1. Chat Responses

   - Model: qwen/qwen3-30b-a3b:free
   - 41K context window
   - Good for creative roleplay

2. Summary Generation
   - Model: tngtech/deepseek-r1t-chimera:free
   - 164K context window
   - Better at analysis tasks

## Deployment

### Environment Setup

1. Required Variables

   ```
   # Discord
   DISCORD_TOKEN=your_bot_token
   DISCORD_GUILD_ID=your_server_id

   # Twitch
   TWITCH_TOKEN=oauth:token
   TWITCH_CLIENT_ID=client_id
   TWITCH_CLIENT_SECRET=client_secret
   TWITCH_CHANNEL_NAME=channel_to_join
   TWITCH_BOT_NAME=bot_account_name

   # MongoDB
   MONGODB_URI=mongodb+srv://...

   # Optional
   RENDER=false
   RENDER_EXTERNAL_URL=your_render_url
   ```

2. Bot Permissions
   - View Channels
   - Send Messages
   - Send Messages in Threads
   - Read Message History
   - Mention Everyone
   - Use Application Commands

### Channel Setup

1. Server-wide Settings
   - Remove "View Channel" from bot role
2. Per-Channel Access
   - Add channel override for bot role
   - Enable: View Channel, Send Messages, Read History
   - Customize per channel as needed

### Monitoring

1. Logs

   - System messages now show full context
   - API requests fully logged
   - Response processing visible

2. Health Checks
   - /health endpoint available
   - Checks MongoDB connection
   - Returns service status

## Maintenance

### Model Updates

1. Chat Model (ai_handler.py: get_chat_response())

   ```python
   payload = {
       "model": "qwen/qwen3-30b-a3b:free",
       "messages": [...],
   }
   ```

2. Summary Model (ai_handler.py: update_summaries())
   ```python
   prompt = {
       "model": "tngtech/deepseek-r1t-chimera:free",
       "messages": [...],
   }
   ```

### Customizing Bot Behavior

1. Core Personality (config.py)

   ```python
   BOT_PERSONA = """
   You are Ghost, a sassy british dragon...
   """
   ```

   - Defines base personality
   - Sets default behavior patterns
   - Used in every conversation

2. Special User Relationships (special_users.json)

   ```json
   {
     "username": {
       "role": "friend/rival/etc",
       "context": "detailed relationship context",
       "variants": ["nickname1", "nickname2"]
     }
   }
   ```

   - Defines special relationships
   - Provides context for interactions
   - Supports multiple username variants

3. Response Settings (config.py)
   ```python
   PLATFORM_SETTINGS = {
       "discord": {"max_message_length": 2000},
       "twitch": {"max_message_length": 500}
   }
   ```
   - Platform-specific constraints
   - Message length limits
   - Feature toggles

### Available Commands

1. Discord Slash Commands

   ```
   /link_twitch [username] - Link Discord and Twitch accounts
   /unlink_accounts      - Unlink Discord and Twitch accounts
   /update_summary      - Force update user relationship summary
   /limits             - Check API usage limits
   ```

2. Chat Triggers

   - Mention the bot (@Ghost)
   - Use keywords "ghost" or "ghosty"
   - Direct messages
   - Bot responds to any of these triggers

3. Twitch Commands
   ```
   !confirm_link - Complete Discord-Twitch account linking
   ```

### State Management

1. Backup Current State

   ```bash
   python migrate_to_mongo.py --backup
   ```

2. Clear Data

   ```bash
   python clear_data.py --all
   ```

3. Restore from Backup
   ```bash
   python migrate_to_mongo.py --restore
   ```
