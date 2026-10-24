"""Proxy forwarding for backend.services.nvidia_gemma."""
from backend.app.services.nvidia_gemma import (
    NvidiaGemmaService,
    nvidia_service,
    SYSTEM_PROMPT_BASE,
    LANGUAGE_INSTRUCTIONS,
)

__all__ = ["NvidiaGemmaService", "nvidia_service", "SYSTEM_PROMPT_BASE", "LANGUAGE_INSTRUCTIONS"]
