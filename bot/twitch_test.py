import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from twitch_handler import TwitchBot
from state_manager import StateManager
from ai_handler import AIHandler

def main():
    try:
        print("Initializing components...")
        # Initialize AI handler first
        ai_handler = AIHandler()
        
        # Initialize state manager with AI handler
        state_manager = StateManager(ai_handler)

        print("Creating Twitch bot...")
        # Create and run Twitch bot
        bot = TwitchBot(state_manager, ai_handler)
        
        print("Running bot...")
        bot.run()
    except Exception as e:
        print(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()
