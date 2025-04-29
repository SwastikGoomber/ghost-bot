import asyncio
import os
import signal
import aiohttp
from bot import CustomBot
from twitch_handler import TwitchBot
from state_manager import StateManager
from ai_handler import AIHandler
from config import DISCORD_TOKEN
from logging_config import setup_logging
from typing import Optional, Tuple

# Set up logging
logger = setup_logging()

# Simple HTTP server for health checks
from aiohttp import web

# Global shutdown flag
shutdown_event = asyncio.Event()

def handle_shutdown(sig, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {sig}")
    shutdown_event.set()

# Register signal handlers
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

async def health_check(request):
    """Basic health check endpoint"""
    # Check MongoDB connection if available
    state_manager = request.app['state_manager']
    if state_manager and state_manager.db:
        try:
            await state_manager.db.ping()
            status = "healthy"
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            status = "degraded"
    else:
        status = "healthy"
    
    return web.json_response({
        "status": status,
        "mongodb": status if state_manager and state_manager.db else "disabled"
    })

async def keep_alive():
    """Ping health endpoint every 10 minutes to prevent spin down"""
    while not shutdown_event.is_set():
        try:
            async with aiohttp.ClientSession() as session:
                render_url = os.environ.get('RENDER_EXTERNAL_URL')
                if render_url:
                    async with session.get(f'{render_url}/health') as resp:
                        logger.info(f"Keep-alive ping sent. Status: {resp.status}")
                else:
                    logger.warning("No RENDER_EXTERNAL_URL found for keep-alive")
        except Exception as e:
            logger.error(f"Keep-alive error: {e}")
        try:
            # Wait for either shutdown or next interval
            await asyncio.wait_for(shutdown_event.wait(), timeout=600)
        except asyncio.TimeoutError:
            continue

async def start_health_server(state_manager: Optional[StateManager] = None):
    """Start a simple health check server"""
    try:
        if os.environ.get('RENDER'):
            app = web.Application()
            app['state_manager'] = state_manager  # Store for health checks
            app.router.add_get('/health', health_check)
            runner = web.AppRunner(app)
            await runner.setup()
            port = int(os.environ.get('PORT', 10000))
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            logger.info(f"Health check server running on port {port}")
            
            # Start keep-alive task
            asyncio.create_task(keep_alive())
    except Exception as e:
        logger.error(f"Failed to start health check server: {e}")

async def initialize_components() -> Tuple[AIHandler, StateManager, CustomBot, TwitchBot]:
    """Initialize all shared components"""
    try:
        logger.info("Initializing AI handler...")
        ai_handler = AIHandler()
        
        logger.info("Initializing state manager...")
        state_manager = StateManager(ai_handler)
        
        # Load states if using MongoDB
        if os.environ.get('MONGODB_URI'):
            logger.info("Loading states from MongoDB...")
            retry_delay = 1
            for attempt in range(3):  # Try 3 times
                try:
                    await state_manager.load_states()
                    logger.info("States loaded successfully")
                    break
                except Exception as e:
                    if attempt == 2:  # Last attempt failed
                        logger.error(f"Failed to load states after 3 attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        
        logger.info("Initializing bots...")
        discord_bot = CustomBot(state_manager, ai_handler)
        twitch_bot = TwitchBot(state_manager, ai_handler)
        
        return ai_handler, state_manager, discord_bot, twitch_bot
        
    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        raise

async def shutdown(discord_bot=None, twitch_bot=None, state_manager=None):
    """Handle graceful shutdown of components"""
    logger.info("Initiating graceful shutdown...")
    
    try:
        tasks = []
        
        # Close bots if they exist
        if discord_bot:
            tasks.append(asyncio.create_task(discord_bot.close()))
        if twitch_bot:
            tasks.append(asyncio.create_task(twitch_bot.close()))
            
        # Wait for bot shutdowns with timeout
        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=5)
            if pending:
                logger.warning(f"{len(pending)} tasks did not complete shutdown gracefully")
            
        # Close state manager's DB connection
        if state_manager and state_manager.db:
            try:
                await asyncio.wait_for(state_manager.db.close(), timeout=2)
            except asyncio.TimeoutError:
                logger.warning("Database connection close timed out")
            
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    finally:
        logger.info("Shutdown complete")

async def main():
    logger.info("Bot starting in {} mode".format(
        "Render" if os.environ.get('RENDER') else "Local"
    ))
    
    components = None
    try:
        # Initialize all components
        components = await initialize_components()
        ai_handler, state_manager, discord_bot, twitch_bot = components
        
        # Start health check server if on Render
        if os.environ.get('RENDER'):
            await start_health_server(state_manager)
        
        # Start both bots
        logger.info("Starting bots...")
        tasks = []
        tasks.append(asyncio.create_task(discord_bot.start(DISCORD_TOKEN)))
        tasks.append(asyncio.create_task(twitch_bot.start()))
        
        # Wait for shutdown signal or bot failure
        done, pending = await asyncio.wait(
            tasks + [asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Check if a bot task failed
        for task in done:
            if task in tasks and task.exception():
                logger.error("Bot task failed", exc_info=task.exception())
                raise task.exception()
            
    except Exception as e:
        logger.error(f"Fatal error occurred: {e}", exc_info=True)
        raise
    finally:
        if components:
            await shutdown(*components)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown by user request")
    except Exception as e:
        logger.error("Bot crashed", exc_info=True)
        exit(1)
