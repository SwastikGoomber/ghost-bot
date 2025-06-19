# Ghost Bot Enhancement TODO

## 1. Global Chat Messages Context

**Problem:** Ghost is a public bot, not a private conversation bot. Users often refer to ongoing conversations, roleplay, or context from recent chat that Ghost doesn't see.

**Solution:** Include last 5 messages from the current platform's channel where user sent their message.

**Implementation Details:**

- **What to include:** Last 5 messages from same channel/chat
- **User context:** Only basic info per message (username, pronouns if set, special user role if any)
- **What NOT to include:** Full relationship summaries for each user (too token-heavy)
- **Platform handling:** Discord channels vs Twitch chat streams
- **Format:** Clear labeling as "RECENT CHAT CONTEXT" to prevent confusion with current user's context

**Why this approach:** Lightweight context that helps Ghost understand references to ongoing conversations without exploding token usage.

## 2. Mentioned Users' Relationship/Conversation Context

**Problem:** Currently only sending special_user_info for mentioned users, but missing their relationship dynamics with Ghost and recent conversation summaries.

**Solution:** Include relationship summaries and conversation context for any users mentioned in the current message.

**Implementation Details:**

- **What to add:** When user mentions someone, include that person's relationship summary and recent conversation summary with Ghost
- **Clear labeling:** Use "MENTIONED USER: {username}" vs "CURRENT SPEAKER: {username}" to prevent confusion
- **Context source:** Pull from existing UserState summaries for mentioned users
- **Fallback:** If mentioned user has no stored context, skip gracefully

**Why important:** Ghost can respond appropriately about relationships and recent interactions with mentioned people.

## 3. Pronouns Enforcement

**Problem:** Ghost doesn't respect pronouns or have any way to know users' pronouns unless explicitly told, which gets lost after 40 messages due to summarization.

**Solution:** Permanent pronoun storage with hybrid command interface.

**Implementation Details:**

- **Storage:** Add `pronouns` field to UserState that NEVER gets summarized away
- **Command interface:** Hybrid approach with Discord dropdown + custom option
  - Discord: Slash command with common choices (He/Him, She/Her, They/Them, etc.) plus "Custom" option
  - Twitch: Simple text command `!pronouns She/Her`
- **Common choices:** He/Him, She/Her, They/Them, He/They, She/They, Any pronouns, Ask me
- **Context inclusion:** Always include user's pronouns in system messages for that conversation
- **Cross-platform:** Works on both Discord and Twitch

**Why commands over role extraction:** Roles are complex to parse (🟠 He/Him), change frequently, don't exist on Twitch, and users should have direct control.

## 4. Captain's Logs Integration

**Problem:** Discord server has "captain's logs" thread with important overarching events and server lore that Ghost should know about for context.

**Solution:** Semi-automatic monitoring and search system for relevant log context.

**Implementation Details:**

- **Auto-detection:** Monitor specific Discord channel/thread for new captain's log posts
- **Manual approval:** When new logs detected, ping admin for review/approval before adding to context
- **Storage:** Store logs with date, content, and searchable keywords
- **Smart inclusion:**
  - If user mentions specific dates/events: Search and include relevant logs
  - Normal conversation: Include last 2 recent logs for general context
  - Token management: Reserve ~20% of context budget for logs
- **Search method:** Simple keyword matching + date parsing (no RAG needed initially)
- **Update frequency:** Automatic detection when new posts appear in captain's log channel

**Why semi-automatic:** Balances automation with human curation to ensure quality and relevance.

## 5. Image/Vision Support

**Problem:** Community shares memes, screenshots, artwork that Ghost can't see or respond to appropriately.

**Solution:** Automatic model switching to vision-capable model when images are detected.

**Implementation Details:**

- **Detection:** Check message attachments for image content types
- **Model switching:**
  - Images present: Use vision model (e.g., GPT-4V or Qwen2.5-VL)
  - Text only: Use regular text model (Llama 3.3 70B)
- **Image handling:** Pass image URLs to vision model along with text content and normal context
- **Context preservation:** Keep all existing context (user relationship, pronouns, etc.) for vision model
- **Platform support:** Discord attachments primarily, Twitch has limited image support
- **Character consistency:** Ensure Ghost's personality remains consistent across both models

**Why automatic switching:** Seamless user experience - Ghost can naturally respond to both text and images without user having to specify anything.

---

## Implementation Priority:

1. **Mentioned users' context** (Quick win, improves conversations immediately)
2. **Pronouns system** (High impact for user experience and inclusivity)
3. **Image/Vision support** (High engagement, fun community feature)
4. **Global chat context** (Moderate impact, more complex implementation)
5. **Captain's logs** (Nice-to-have, can be implemented later when more resources available)

## Technical Notes:

- All features should maintain Ghost's character consistency
- Token budget management crucial for context features
- Clear labeling in system messages prevents AI confusion
- Backward compatibility for existing UserState data
- Cross-platform considerations (Discord vs Twitch capabilities)
