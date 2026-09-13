"""
Single shared Motor client for the whole app. Motor is the async MongoDB
driver — needed because FastAPI is async, and a blocking DB call would
stall the whole event loop under load.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import certifi

client = AsyncIOMotorClient(
    settings.mongo_uri,
    tlsCAFile=certifi.where()
)

db = client[settings.mongo_db_name]

# Collections — reference these from routes/services, don't reconnect elsewhere
users_collection = db["users"]
documents_collection = db["documents"]
chunks_collection = db["chunks"]          # chunk metadata (text + doc ref); vectors live in FAISS
chat_history_collection = db["chat_history"]