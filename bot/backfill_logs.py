
import os
import asyncio
from datetime import datetime
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# --- IMPORTANT: Configuration ---
# Load environment variables from .env file in the current directory or a parent directory.
# Ensure your .env file with MONGO_URI and GEMINI_API_KEY is accessible.
load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_NAME = "ghost_bot"
LOG_COLLECTION_NAME = "captains_logs"

# --- Models ---
GEMINI_MODEL = "gemini-2.5-flash"
LOCAL_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Input File ---
# Place your raw, existing logs into this file.
LOG_FILE_PATH = "existing_logs.txt"

# --- Main Processing Logic ---

def chunk_text(text: str) -> list[str]:
    """
    Splits the cleaned log file into chunks.
    Assumes each line in the file is a separate, semantic chunk.
    """
    # Split by newline and filter out any empty lines that may exist.
    return [line.strip() for line in text.split('\n') if line.strip()]

async def get_metadata_from_gemini(chunk: str, model) -> dict[str, any]:
    """Uses Gemini to extract structured metadata from a text chunk."""
    prompt = f"""
    Analyze the following roleplay log entry. Extract the key information as a JSON object.

    **Log Entry:**
    "{chunk}"

    **Instructions:**
    1.  `summary`: Write a concise, one-sentence summary of the event.
    2.  `participants`: List the names of all characters or key figures involved.
    3.  `event_type`: Classify the event into one of: ["Character Interaction", "Plot Development", "Combat/Action", "Lore Drop", "Humor/Meme", "General"].
    4.  `key_objects_or_concepts`: List any important items, locations, or abstract ideas.

    **Output ONLY the raw JSON object.**
    """
    try:
        response = await model.generate_content_async(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()
        import json
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"-- Gemini Error: {e}")
        print(f"-- Failed Chunk: {chunk[:100]}...")
        return {"error": str(e)}

async def main():
    """Main function to run the backfill process."""
    print("--- Starting Log Backfill Process ---")

    # 1. Check for configurations
    if not MONGO_URI or not GEMINI_API_KEY:
        print("Error: MONGO_URI and GEMINI_API_KEY must be set in your .env file.")
        return

    if not os.path.exists(LOG_FILE_PATH):
        print(f"Error: Log file not found at '{LOG_FILE_PATH}'. Please create it and add your logs.")
        return

    # 2. Initialize connections and models
    try:
        print("Connecting to MongoDB...")
        db_client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
        db = db_client[DB_NAME]
        log_collection = db[LOG_COLLECTION_NAME]
        db_client.admin.command('ping')
        print("MongoDB connection successful.")

        print("Initializing Gemini model...")
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL)

        print(f"Loading local embedding model: {LOCAL_EMBEDDING_MODEL}...")
        local_embedder = SentenceTransformer(LOCAL_EMBEDDING_MODEL)
        print("Local embedding model loaded.")

    except Exception as e:
        print(f"Initialization failed: {e}")
        return

    # 3. Read and process the log file
    with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
        full_log_content = f.read()

    chunks = chunk_text(full_log_content)
    if not chunks:
        print("No valid chunks found in the log file.")
        return

    print(f"Found {len(chunks)} chunks to process.")

    # 4. Process each chunk
    documents_to_insert = []
    for i, chunk in enumerate(chunks):
        print(f"\nProcessing chunk {i+1}/{len(chunks)}...")
        print(f"Text: {chunk[:80]}...")

        # A. Get metadata from Gemini
        metadata = await get_metadata_from_gemini(chunk, gemini_model)
        if "error" in metadata:
            print(f"Skipping chunk due to Gemini processing error.")
            continue
        
        print(f"  - Summary: {metadata.get('summary')}")
        print(f"  - Participants: {metadata.get('participants')}")

        # B. Generate embedding locally
        embedding = local_embedder.encode(chunk).tolist()
        print(f"  - Embedding generated (vector size: {len(embedding)})")

        doc = {
            "message_id": f"backfill_{i}",
            "chunk_id": f"backfill_{i}-0",
            "text": chunk,
            "embedding": embedding,
            "metadata": metadata,
            "processed_at": datetime.utcnow(),
            "created_at": datetime.utcnow() # Placeholder timestamp for backfilled logs
        }
        documents_to_insert.append(doc)

        # C. Respect API rate limits
        print("Waiting 6 seconds before next API call...")
        await asyncio.sleep(6) # 10 requests per minute = 6s per request

    # 5. Insert into database
    if documents_to_insert:
        print("\n--- Database Insertion ---")
        try:
            # Optional: Clear the collection before inserting new backfilled data
            # print("Clearing existing captains_logs collection...")
            # log_collection.delete_many({})
            
            log_collection.insert_many(documents_to_insert)
            print(f"Successfully inserted {len(documents_to_insert)} documents into '{LOG_COLLECTION_NAME}'.")
        except Exception as e:
            print(f"Error inserting documents into MongoDB: {e}")
    else:
        print("No documents were processed to be inserted.")

    print("\n--- Backfill Process Complete ---")

if __name__ == "__main__":
    # To run this async script
    asyncio.run(main())

