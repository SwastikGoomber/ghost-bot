# Simple Deployment Guide

## Local Development

```bash
# Run bot locally
python main.py
```

## Render Deployment

1. Push code to GitHub
2. Create new Web Service on Render
3. Connect to your GitHub repository
4. Configure environment variables:
   ```
   DISCORD_TOKEN=your_token
   DISCORD_GUILD_ID=your_guild_id
   TWITCH_TOKEN=your_token
   TWITCH_CLIENT_ID=your_client_id
   TWITCH_CHANNEL=your_channel
   OPENROUTER_CHAT_KEY=your_key
   OPENROUTER_SUMMARY_KEY=your_key
   ```

## How It Works

- Local: Bot runs without health check
- Render: Bot automatically starts health check endpoint
- No additional setup needed

## Files

- `main.py` - Main bot + health check
- `render.yaml` - Render configuration
- `runtime.txt` - Python version (3.11.0)
- `requirements.txt` - Dependencies

## Monitoring

1. Watch Render dashboard for:

   - Memory usage (1GB limit)
   - Response times
   - Error logs

2. Bot logs show:
   - Startup status
   - Connection issues
   - API rate limits

## Recovery

1. If bot goes offline:

   - Check Render logs
   - Verify API credentials
   - Restart service if needed

2. If state corruption:
   - Stop service
   - Clear corrupted states
   - Restart service

## Support

- Render Dashboard: https://dashboard.render.com
- Discord API: https://discord.com/developers
- Twitch API: https://dev.twitch.tv
- OpenRouter: https://openrouter.ai/docs
