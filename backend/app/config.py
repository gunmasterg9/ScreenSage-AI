"""Configuration settings for ScreenSage AI backend."""

import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "ScreenSage AI"
    APP_VERSION: str = "1.0.0"
    PRODUCT_TAGLINE: str = "Understand any screen. Take the next step."
    ENVIRONMENT: str = "development"

    # Server binding (localhost only for privacy by default)
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # NVIDIA Gemma 4 API Configuration
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL: str = os.getenv("NVIDIA_MODEL", "google/gemma-4-31b-it")
    NVIDIA_BASE_URL: str = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    INFERENCE_TIMEOUT_SECONDS: float = float(os.getenv("INFERENCE_TIMEOUT_SECONDS", "60.0"))

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
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
