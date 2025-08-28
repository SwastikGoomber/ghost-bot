
import os
import asyncio
from datetime import datetime
from typing import Dict, List, Any
import discord
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
import numpy as np
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Use a connection string from environment variables
MONGO_URI = os.getenv("MONGODB_URI")
DB_NAME = "ghost_bot" # Or pull from env if you prefer
LOG_COLLECTION_NAME = "captains_logs"
LOG_CHANNEL_ID = 1371121095683346534

# --- Models ---
# Model for semantic analysis of log chunks (using Gemini)
GEMINI_MODEL = "gemini-2.0-flash"
# Model for local embedding generation (runs on CPU)
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class LogManager:
    """
    Manages fetching, processing, storing, and retrieving long-term logs.
    """
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db_client = None
        self.db = None
        self.log_collection = None
        self.local_embedder = None
        self._initialized = False

    async def initialize(self):
        """
        Initializes the database connection and the local embedding model.
        """
        if self._initialized:
            return

        print("--- LogManager Initialization ---")
        
        # 1. Initialize Database Connection
        try:
            if not MONGO_URI:
                print("MONGODB_URI not set. LogManager will be disabled.")
                return

            self.db_client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
            self.db = self.db_client[DB_NAME]
            self.log_collection = self.db[LOG_COLLECTION_NAME]
            # Ping to confirm connection
            self.db_client.admin.command('ping')
            print("Successfully connected to MongoDB for LogManager.")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            self.db_client = None # Disable DB features on failure
            return

        # 2. Initialize Local Embedding Model
        try:
            print(f"Loading local embedding model: {LOCAL_EMBEDDING_MODEL}...")
            self.local_embedder = SentenceTransformer(LOCAL_EMBEDDING_MODEL)
            print("Local embedding model loaded successfully.")
        except Exception as e:
            print(f"CRITICAL: Failed to load SentenceTransformer model: {e}")
            # This is a fatal error for the module, so we disable it.
            self.db_client = None 
            return

        self._initialized = True
        print("--- LogManager Initialized Successfully ---")

    def is_enabled(self) -> bool:
        """Check if the LogManager is fully initialized and operational."""
        from config import CAPTAINS_LOG_ENABLED
        
        initialized = self._initialized
        db_client = self.db_client is not None
        local_embedder = self.local_embedder is not None
        config_enabled = CAPTAINS_LOG_ENABLED
        
        print(f"[DEBUG] LogManager.is_enabled() check: _initialized={initialized}, db_client={db_client}, local_embedder={local_embedder}, config_enabled={config_enabled}")
        return initialized and db_client and local_embedder and config_enabled

    async def get_relevant_logs(self, query: str, limit: int = 5) -> List[str]:
        """
        Finds and returns the most semantically similar log chunks for a given query.
        """
        if not self.is_enabled():
            return []

        try:
            # 1. Generate vector for the user's query using the local model
            print(f"Generating query vector for: \"{query}\"")
            query_vector = self.local_embedder.encode(query).tolist()

            # 2. Perform a vector search query on MongoDB
            # {
            #   "fields": [
            #     {
            #       "type": "vector",
            #       "path": "embedding",
            #       "numDimensions": 384,
            #       "similarity": "cosine"
            #     }
            #   ]
            # }
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index", # The name of your vector search index
                        "path": "embedding",
                        "queryVector": query_vector,
                        "numCandidates": 100, # Number of candidates to consider
                        "limit": limit # Number of results to return
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "text": 1,
                        "score": { "$meta": "vectorSearchScore" }
                    }
                }
            ]

            results = list(self.log_collection.aggregate(pipeline))
            
            print(f"Found {len(results)} relevant log chunks via vector search.")
            # Filter results with a minimum relevance score if needed
            # relevant_docs = [res['text'] for res in results if res['score'] > 0.7]
            relevant_docs = [res['text'] for res in results]

            return relevant_docs

        except Exception as e:
            print(f"Error during semantic log search: {e}")
            # This can happen if the vector search index doesn't exist.
            # As a fallback, we could do a manual cosine similarity search,
            # but it's much less efficient. For now, we'll just log the error.
            return []

    def format_logs_for_context(self, relevant_logs: List[str]) -> str:
        """Formats the retrieved logs into a string for the AI context."""
        if not relevant_logs:
            return ""

        context_str = "[HISTORICAL CONTEXT - Relevant Captain's Log Entries]\n"
        for log_text in relevant_logs:
            context_str += f"- {log_text}\n"
        
        print(f"--- RAG CONTEXT ---\n{context_str}\n---------------------")
        return context_str.strip()

    async def fetch_and_process_new_logs(self):
        """
        Fetches new messages from the log channel and processes them.
        """
        if not self.is_enabled():
            print("LogManager is not enabled, skipping log processing.")
            return

        print("Checking for new Captain's Logs...")
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if not log_channel:
            print(f"Error: Cannot find log channel with ID {LOG_CHANNEL_ID}")
            return
        
        # Get the timestamp of the most recently processed log
        last_log_timestamp = await self.get_last_log_timestamp()

        # Fetch messages after this timestamp
        new_messages = []
        async for message in log_channel.history(after=last_log_timestamp, limit=100): # limit to 100 new logs per check
            new_messages.append(message)

        if not new_messages:
            print("No new logs found.")
            return

        print(f"Found {len(new_messages)} new log(s) to process.")
        # Process oldest to newest
        for message in reversed(new_messages): 
            await self.process_single_log_message(message)
            # Gentle delay to respect Gemini API limits
            await asyncio.sleep(5) 

    async def process_single_log_message(self, message: discord.Message):
        """
        Processes one Discord message, chunks it, analyzes, embeds, and stores it.
        """
        print(f"Processing log from {message.author.name} at {message.created_at.isoformat()}")
        
        # 1. Chunk the message content
        chunks = self.chunk_text(message.content)
        if not chunks:
            return

        # 2. Analyze and embed each chunk
        documents_to_insert = []
        for i, chunk_text in enumerate(chunks):
            # A. Get semantic metadata from Gemini
            metadata = await self.get_metadata_from_gemini(chunk_text)
            
            # B. Generate vector embedding locally
            embedding = self.local_embedder.encode(chunk_text).tolist()

            doc = {
                "message_id": message.id,
                "chunk_id": f"{message.id}-{i}",
                "text": chunk_text,
                "embedding": embedding,
                "metadata": metadata,
                "processed_at": datetime.utcnow(),
                "created_at": message.created_at
            }
            documents_to_insert.append(doc)

        # 3. Insert into MongoDB
        if documents_to_insert:
            self.log_collection.insert_many(documents_to_insert)
            print(f"Successfully processed and stored {len(documents_to_insert)} chunks for message {message.id}.")

    def chunk_text(self, text: str, min_chunk_size: int = 50) -> List[str]:
        """
        Splits a log message into smaller chunks by paragraphs or bullet points.
        """
        # Split by double newlines first (paragraphs)
        chunks = text.split('\n\n')
        
        # Further split by single newlines (bullet points)
        final_chunks = []
        for chunk in chunks:
            sub_chunks = chunk.split('\n')
            final_chunks.extend([c.strip() for c in sub_chunks if len(c.strip()) >= min_chunk_size])

        return final_chunks

    async def get_metadata_from_gemini(self, chunk: str) -> Dict[str, Any]:
        """
        Uses Gemini to extract structured metadata from a text chunk.
        """
        if not GEMINI_API_KEY:
            return {"error": "Gemini API key not configured."}
            
        try:
            model = genai.GenerativeModel(GEMINI_MODEL)
            prompt = f"""
            Analyze the following roleplay log entry. Extract the key information as a JSON object.

            **Log Entry:**
            "{chunk}"

            **Instructions:**
            1.  `summary`: Write a concise, one-sentence summary of the event.
            2.  `participants`: List the names of all characters or key figures involved.
            3.  `event_type`: Classify the event into one of the following categories: ["Character Interaction", "Plot Development", "Combat/Action", "Lore Drop", "Humor/Meme", "General"].
            4.  `key_objects_or_concepts`: List any important items, locations, or abstract ideas mentioned.

            **Output ONLY the raw JSON object.**
            """
            
            response = await model.generate_content_async(prompt)
            # The response text might be enclosed in ```json ... ```, so we need to parse it out.
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
            
            import json
            return json.loads(cleaned_response)

        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return {"error": str(e)}

    async def get_last_log_timestamp(self) -> datetime:
        """
        Gets the timestamp of the most recent log entry from the database.
        """
        latest_log = self.log_collection.find_one(sort=[("created_at", -1)])
        if latest_log:
            return latest_log["created_at"]
        # If no logs exist, return a very old timestamp to fetch all history (up to the limit)
        return datetime(2000, 1, 1)


