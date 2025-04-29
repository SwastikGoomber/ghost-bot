"""MongoDB connection handler that maintains JSON compatibility"""
import os
import asyncio
import logging
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient

# Set up logging
logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client = None
        self.db = None
        self.states = None
        
    async def connect(self):
        """Connect to MongoDB Atlas"""
        mongo_uri = os.getenv('MONGODB_URI')
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable not set")
        
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client.ghost_bot
        
        # Initialize collection
        self.states = self.db.user_states
        
    async def save_states(self, states: Dict[str, Any]) -> None:
        """Save entire states dictionary as one document"""
        if self.states is None:
            raise RuntimeError("Database not connected")
        
        # Save the entire state as a single document
        await self.states.find_one_and_replace(
            {'_id': 'current_states'},
            {'_id': 'current_states', **states},
            upsert=True
        )
        
    async def load_states(self) -> Dict[str, Any]:
        """Load states dictionary"""
        if self.states is None:
            raise RuntimeError("Database not connected")
        
        doc = await self.states.find_one({'_id': 'current_states'})
        if doc:
            doc_copy = dict(doc)  # Make a copy
            doc_copy.pop('_id')   # Remove MongoDB ID
            return doc_copy
        return {}

    async def ping(self) -> bool:
        """Check MongoDB connection health"""
        if not self.client:
            return False
        try:
            await self.db.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {e}")
            return False

    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(self.client.close), 
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning("MongoDB connection close timed out")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")
