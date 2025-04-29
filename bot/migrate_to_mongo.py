"""Script to migrate existing JSON data to MongoDB"""
import asyncio
import json
import os
from datetime import datetime
from db import MongoDB
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Setup paths
USER_STATES_FILE = Path('user_states.json')

async def migrate_data():
    """Migrate user states to MongoDB"""
    print("\n=== Starting Migration ===")
    
    db = None
    try:
        # Initialize MongoDB
        print("🔄 Connecting to MongoDB...")
        db = MongoDB()
        await db.connect()
        is_connected = await db.ping()
        assert is_connected, "MongoDB connection failed"
        print("✓ Connected to MongoDB")

        # Load user states
        print("\n📖 Loading user states...")
        if not USER_STATES_FILE.exists():
            print("❌ No user_states.json found")
            return False

        with open(USER_STATES_FILE, 'r') as f:
            states_data = json.load(f)
        print(f"✓ Loaded {len(states_data)} states from file")

        # Save to MongoDB
        print("\n💾 Saving to MongoDB...")
        try:
            await db.save_states(states_data)
            print("✓ States saved to MongoDB")
        except Exception as e:
            print(f"❌ Failed to save states: {e}")
            raise
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        mongo_states = await db.load_states()
        
        if len(mongo_states) != len(states_data):
            print("❌ State count mismatch")
            print(f"MongoDB: {len(mongo_states)}, Original: {len(states_data)}")
            return False

        # Compare contents
        orig_keys = set(states_data.keys())
        mongo_keys = set(mongo_states.keys())
        if orig_keys != mongo_keys:
            print("❌ State keys mismatch")
            print(f"MongoDB keys: {sorted(mongo_keys)}")
            print(f"Original keys: {sorted(orig_keys)}")
            return False

        # Create backup of original file
        backup_path = USER_STATES_FILE.with_suffix('.json.bak')
        if backup_path.exists():
            backup_path.unlink()
        USER_STATES_FILE.rename(backup_path)
        print("✓ Original file backed up")
            
        print("\n✓ Migration successful!")
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if db is not None:
            try:
                await db.close()
                print("✓ Database connection closed")
            except Exception as e:
                print(f"❌ Error closing database: {e}")

def get_database_name() -> str:
    """Extract database name from MongoDB URI"""
    uri = os.getenv('MONGODB_URI', '')
    try:
        parts = uri.split('/')
        if len(parts) >= 4:
            return parts[3].split('?')[0]
    except Exception:
        pass
    return 'unknown'

if __name__ == "__main__":
    if not os.getenv('MONGODB_URI'):
        print("❌ MONGODB_URI environment variable not set")
        exit(1)
    
    print(f"Using database: {get_database_name()}")
    
    try:
        success = asyncio.run(migrate_data())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nMigration interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\nMigration failed with error: {type(e).__name__}")
        print(f"Error details: {str(e)}")
        exit(1)
