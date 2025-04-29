import asyncio
import os
import aiohttp
from bot import CustomBot
from twitch_handler import TwitchBot
from state_manager import StateManager
from ai_handler import AIHandler
from config import DISCORD_TOKEN
from logging_config import setup_logging

# Set up logging
logger = setup_logging()

# Simple HTTP server for health checks
from aiohttp import web

async def health_check():
    """Basic health check endpoint"""
    return web.Response(text='OK')

async def start_health_server():
    """Start a simple health check server"""
    try:
        if os.environ.get('RENDER'):
            app = web.Application()
            app.router.add_get('/health', health_check)
            runner = web.AppRunner(app)
            await runner.setup()
            port = int(os.environ.get('PORT', 10000))
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            logger.info(f"Health check server running on port {port}")
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}")

async def main():
    logger.info("Initializing shared components...")
    # Initialize AI handler first
    ai_handler = AIHandler()
    
    # Initialize state manager with AI handler
    state_manager = StateManager(ai_handler)
    
    logger.info("Initializing bots...")
    # Initialize bots
    discord_bot = CustomBot(state_manager, ai_handler)
    twitch_bot = TwitchBot(state_manager, ai_handler)
    
    logger.info("Starting both bots...")
    
    logger.info("Bot starting in {} mode".format(
        "Render" if os.environ.get('RENDER') else "Local"
    ))
    
    try:
        # Determine tasks based on environment
        tasks = [
            discord_bot.start(DISCORD_TOKEN),
            twitch_bot.start()
        ]
        
        # Start health check server if on Render
        if os.environ.get('RENDER'):
            await start_health_server()
            
        # Run all tasks
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
    finally:
        # Handle graceful shutdown
        logger.info("Cleaning up...")
        tasks = [
            discord_bot.close(),
            twitch_bot.close()
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
