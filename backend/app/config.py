"""Configuration settings for ScreenSage AI backend."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv

# Search for .env in project root and backend dir
root_env = Path(__file__).resolve().parent.parent.parent / ".env"
backend_env = Path(__file__).resolve().parent.parent / ".env"

if root_env.exists():
    load_dotenv(root_env)
elif backend_env.exists():
    load_dotenv(backend_env)
else:
    load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "ScreenSage AI"
    APP_VERSION: str = "1.0.0"
    PRODUCT_TAGLINE: str = "Understand any screen. Take the next step."
    ENVIRONMENT: str = "development"

    # Server binding (localhost only for privacy by default)
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Google Gemini API Configuration (Gemma 4 model integration)
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_GEMINI_MODEL: str = os.getenv("GOOGLE_GEMINI_MODEL", "gemma-4-31b-it")
    INFERENCE_TIMEOUT_SECONDS: float = float(os.getenv("INFERENCE_TIMEOUT_SECONDS", "120.0"))

    # Security & Image upload limits
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024)))  # 10 MB
    MAX_IMAGE_DIMENSION: int = int(os.getenv("MAX_IMAGE_DIMENSION", "4096"))
    MAX_IMAGE_PIXELS: int = int(os.getenv("MAX_IMAGE_PIXELS", "10000000"))  # Pillow decompression bomb limit
    ALLOWED_IMAGE_MIMES: List[str] = [
        "image/png",
        "image/jpeg",
        "image/webp",
    ]
    ALLOWED_IMAGE_FORMATS: List[str] = ["PNG", "JPEG", "WEBP"]

    # Batch processing limits & concurrency
    MAX_BATCH_IMAGES: int = int(os.getenv("MAX_BATCH_IMAGES", "10"))
    MAX_BATCH_TOTAL_SIZE_BYTES: int = int(os.getenv("MAX_BATCH_TOTAL_SIZE_BYTES", str(30 * 1024 * 1024)))  # 30 MB
    BATCH_CONCURRENCY: int = int(os.getenv("BATCH_CONCURRENCY", "2"))

    # Session storage (in-memory)
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", "3600"))  # 1 hour in-memory TTL

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = {
        "extra": "ignore",
    }


settings = Settings()
