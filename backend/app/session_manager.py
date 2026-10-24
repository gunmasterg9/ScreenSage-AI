"""In-memory session manager for ScreenSage AI.
Retains current screenshot for follow-up questions during the active session.
Never persists images to disk permanently and purges expired sessions safely.
"""

import time
import uuid
from typing import Dict, Any, Optional, List
from threading import Lock
from backend.app.config import settings
from backend.app.schemas import ScreenExplanation


class SessionData:
    def __init__(self, session_id: str, image_b64: str, metadata: dict):
        self.session_id = session_id
        self.image_b64 = image_b64
        self.metadata = metadata
        self.created_at = time.time()
        self.last_accessed_at = time.time()
        self.conversation_history: List[Dict[str, str]] = []
        self.last_explanation: Optional[ScreenExplanation] = None

    def touch(self):
        self.last_accessed_at = time.time()

    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
        self.touch()


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._batches: Dict[str, List[str]] = {}
        self._lock = Lock()

    def create_session(self, image_b64: str, metadata: dict) -> str:
        """Create a new ephemeral session and return session_id."""
        self.cleanup_expired()
        session_id = str(uuid.uuid4())
        session = SessionData(session_id=session_id, image_b64=image_b64, metadata=metadata)
        with self._lock:
            self._sessions[session_id] = session
        return session_id

    def register_batch(self, batch_id: str, session_ids: List[str]):
        """Map a batch_id to its contained session_ids for coordinated cleanup."""
        with self._lock:
            self._batches[batch_id] = session_ids

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve an active session by ID."""
        self.cleanup_expired()
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
            return session

    def delete_session(self, session_id: str) -> bool:
        """Explicitly purge session data from memory (privacy feature)."""
        with self._lock:
            if session_id in self._sessions:
                # Overwrite image bytes before deleting
                self._sessions[session_id].image_b64 = ""
                del self._sessions[session_id]
                return True
            return False

    def delete_batch(self, batch_id: str) -> int:
        """Explicitly purge all session data in a batch from memory."""
        cleared_count = 0
        with self._lock:
            session_ids = self._batches.pop(batch_id, [])
            for sid in session_ids:
                if sid in self._sessions:
                    self._sessions[sid].image_b64 = ""
                    del self._sessions[sid]
                    cleared_count += 1
        return cleared_count

    def cleanup_expired(self):
        """Purge sessions older than SESSION_TTL_SECONDS."""
        now = time.time()
        ttl = settings.SESSION_TTL_SECONDS
        with self._lock:
            expired_keys = [
                sid for sid, s in self._sessions.items()
                if (now - s.last_accessed_at) > ttl
            ]
            for sid in expired_keys:
                self._sessions[sid].image_b64 = ""
                del self._sessions[sid]


# Global session manager instance
session_manager = SessionManager()
