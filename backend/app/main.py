import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, documents, query
from app.db.mongodb import client, users_collection, chunks_collection, chat_history_collection

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.limiter import limiter

# Basic logging config — enough to see errors in the terminal during dev.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("documind")

app = FastAPI(title="DocuMind AI", version="0.1.0")

# Rate limiting — protects /query (each call costs a Gemini API call, real
# money) and /documents/upload (CPU/memory heavy) from being hammered.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(query.router)


@app.on_event("startup")
async def create_indexes():
    """
    Runs once when the server starts. Without these, queries on email,
    document_id, and user_id fall back to full collection scans as data
    grows — cheap to add now, painful to notice later.

    Wrapped in try/except so a temporarily unreachable DB at boot doesn't
    crash the whole app — /health can still report "degraded" instead.
    """
    try:
        await users_collection.create_index("email", unique=True)
        await chunks_collection.create_index("document_id")
        await chat_history_collection.create_index([("user_id", 1), ("asked_at", -1)])
        logger.info("MongoDB indexes ensured")
    except Exception as e:
        logger.error(f"Could not create indexes at startup (DB may be unreachable): {e}")


@app.get("/health")
async def health_check():
    """Actually checks MongoDB connectivity, not just 'the process is alive'."""
    try:
        await client.admin.command("ping")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "degraded", "database": "unreachable"}