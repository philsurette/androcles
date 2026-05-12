"""Normalized content hashing for production script identities."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


@dataclass
class ContentHasher:
    """Build deterministic hashes for production lines and segments."""

    def hash_line(self, kind: str, text: str, roles: list[str] | tuple[str, ...] = ()) -> str:
        role_text = ",".join(role.strip() for role in roles)
        return self._hash(f"{kind}|{role_text}|{self._normalize(text)}")

    def hash_segment(self, kind: str, text: str, role: str | None = None) -> str:
        role_text = role.strip() if role else ""
        return self._hash(f"{kind}|{role_text}|{self._normalize(text)}")

    def _hash(self, normalized: str) -> str:
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"sha256:{digest}"

    def _normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
