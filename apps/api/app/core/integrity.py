import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Deterministic JSON used for digests (FR-SEC-09)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: Any) -> str:
    return sha256_hex(canonical_json(value))
