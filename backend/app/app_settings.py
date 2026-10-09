"""ManifestCV settings layered over the upstream mystic-auth settings."""

import importlib
import os
from pathlib import Path

from dotenv import load_dotenv

_pkg_parent = __package__.rsplit(".", 1)[0] if __package__ and "." in __package__ else ""
_mystic_auth_root = f"{_pkg_parent}.mystic_auth" if _pkg_parent else "mystic_auth"
_mystic_auth_settings = importlib.import_module(f"{_mystic_auth_root}.core.settings").settings

_repo_root = Path(__file__).resolve().parents[2]
for _env_file in (_repo_root / "env" / "mystic_auth" / ".env", _repo_root / "env" / "app" / ".env"):
    load_dotenv(_env_file, override=False)


class _ManifestCVSettings:
    """Expose upstream settings plus ManifestCV-only environment fields."""

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

    def __getattr__(self, name: str):
        return getattr(_mystic_auth_settings, name)


settings = _ManifestCVSettings()
