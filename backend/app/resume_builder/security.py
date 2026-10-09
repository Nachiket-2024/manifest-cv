from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from urllib.parse import urlparse

_URL_PATTERN = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}
_MAX_DEPTH = 8
_MAX_ITEMS = 200


def validate_content(value: object, *, _depth: int = 0) -> None:
    """Reject executable markup and unsafe links in user-controlled content."""
    if _depth > _MAX_DEPTH:
        raise ValueError("content is too deeply nested")
    if isinstance(value, str):
        lowered = value.lower()
        if "<script" in lowered or "data:text/html" in lowered or "onerror=" in lowered or "onload=" in lowered:
            raise ValueError("unsupported executable content")
        if _URL_PATTERN.match(value):
            parsed = urlparse(value)
            if parsed.scheme.lower() not in _ALLOWED_URL_SCHEMES or (parsed.scheme.lower() != "mailto" and not parsed.netloc):
                raise ValueError("unsupported URL")
        return
    if isinstance(value, Mapping):
        if len(value) > _MAX_ITEMS:
            raise ValueError("content has too many fields")
        for item in value.values():
            validate_content(item, _depth=_depth + 1)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        if len(value) > _MAX_ITEMS:
            raise ValueError("content has too many items")
        for item in value:
            validate_content(item, _depth=_depth + 1)
