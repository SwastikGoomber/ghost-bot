"""Utility script to purge user summaries and message history from MongoDB"""
import asyncio
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from db import MongoDB

# Load environment variables
load_dotenv('.env')

async def purge_user_data(backup=True, purge_summaries=False, purge_messages=False, purge_all=False):
    """Purge user summaries and/or message history from MongoDB"""
    print("\n=== Starting Data Purge ===")
    
    if not (purge_summaries or purge_messages or purge_all):
        print("No purge action specified. Use --summaries, --messages, or --all")
        return False
    
    db = None
    try:
        # Initialize MongoDB
        print("🔄 Connecting to MongoDB...")
        db = MongoDB()
        await db.connect()
        is_connected = await db.ping()
        assert is_connected, "MongoDB connection failed"
        print("✓ Connected to MongoDB")

        # Load current states
        print("\n📖 Loading current states...")
        states_data = await db.load_states()
        if not states_data:
            print("❌ No user states found in database")
            return False
        
        print(f"✓ Loaded {len(states_data)} user states from database")
        
        # Create backup if requested
        if backup:
            backup_dir = Path("state_backups")
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"states_backup_{timestamp}.json"
            
            with open(backup_path, 'w') as f:
                json.dump(states_data, f, indent=2, default=str)
            print(f"✓ Created backup at {backup_path}")
        
        # Process each user state
        modified_count = 0
        for key, user_data in states_data.items():
            if key == 'pending_links':
                continue  # Skip pending links
                
            modified = False
            
            # Purge summaries if requested
            if purge_summaries or purge_all:
                if 'summaries' in user_data:
                    user_data['summaries'] = {
                        "relationship": "No additional information yet.",
                        "last_conversation": "No conversation summary yet",
                        "last_updated": datetime.now().isoformat()
                    }
                    modified = True
            
            # Purge message history if requested
            if purge_messages or purge_all:
                if 'recent_messages' in user_data:
                    user_data['recent_messages'] = []
                    user_data['message_count'] = 0
                    modified = True
            
            if modified:
                modified_count += 1
        
        # Save modified states back to database
        if modified_count > 0:
            print(f"\n💾 Saving {modified_count} modified user states...")
            await db.save_states(states_data)
            print("✓ Successfully purged data and saved to MongoDB")
        else:
            print("\nℹ️ No user states were modified")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during purge operation: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db:
            await db.close()
            print("✓ Closed MongoDB connection")

def get_database_name():
    """Extract database name from MongoDB URI for display"""
    uri = os.getenv('MONGODB_URI', '')
    if not uri:
        return "Unknown"
    
    try:
        # Extract database name from URI
        parts = uri.split('/')
        if len(parts) > 3:
            db_name = parts[3].split('?')[0]
            return db_name
        return "Default"
    except:
        return "Unknown"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Purge user data from MongoDB")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating a backup before purging")
    parser.add_argument("--summaries", action="store_true", help="Purge user summaries")
    parser.add_argument("--messages", action="store_true", help="Purge message history")
    parser.add_argument("--all", action="store_true", help="Purge both summaries and message history")
    
    args = parser.parse_args()
    
    if not os.getenv('MONGODB_URI'):
        print("❌ MONGODB_URI environment variable not set")
        exit(1)
    
    print(f"Using database: {get_database_name()}")
    
    try:
        success = asyncio.run(purge_user_data(
            backup=not args.no_backup,
            purge_summaries=args.summaries,
            purge_messages=args.messages,
            purge_all=args.all
        ))
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nPurge operation interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\nPurge operation failed with error: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        exit(1)

# # Purge only summaries (keeps message history)
# python purge_user_data.py --summaries

# # Purge only message history (keeps summaries)
# python purge_user_data.py --messages

# # Purge both summaries and message history
# python purge_user_data.py --all

# # Skip creating a backup (not recommended)
# python purge_user_data.py --all --no-backup