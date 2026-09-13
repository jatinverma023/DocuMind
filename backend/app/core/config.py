"""
Central configuration for the app. Everything secret or environment-specific
lives here, loaded from a .env file — never hardcode secrets in code.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Database ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db_name: str = "documind_ai"

    # --- Auth ---
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day

    # --- Gemini API ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # --- Embeddings ---
    embedding_model_name: str = "BAAI/bge-base-en-v1.5"

    # --- File storage ---
    upload_dir: str = "storage/uploads"
    vector_index_dir: str = "storage/vector_index"

    # --- Chunking (tune later during upgrades) ---
    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50

    # --- Retrieval ---
    top_k_chunks: int = 5

    class Config:
        env_file = ".env"


settings = Settings()

# Fail fast if the JWT secret is missing or still the placeholder — booting
# with this would mean anyone can forge valid tokens. Better to crash loudly
# at startup than discover this later.
if settings.jwt_secret_key in ("", "CHANGE_ME_IN_PRODUCTION"):
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a secure random value in your .env file. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )