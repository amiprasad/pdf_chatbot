"""
core/config.py
──────────────
Loads all environment variables and exposes them as a typed Settings object.
Uses pydantic-settings pattern for clean config management.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

class Settings:
    # API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

    # File Storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "data/uploads")
    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "data/quadrant_storage")

    # Models
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama3-8b-8192")
    GOOGLE_GENAI_MODEL: str = os.getenv("GOOGLE_GENAI_MODEL", "models/embedding-001")

    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 1000))
    OVERLAP_SIZE: int = int(os.getenv("OVERLAP_SIZE", 200))

    def validate(self):
        if not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in .env")
            # Google API key is optional (only needed if using Gemini embeddings)
        Path(self.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.QDRANT_PATH).mkdir(parents=True, exist_ok=True)
        Path("./data").mkdir(parents=True, exist_ok=True)

settings = Settings()