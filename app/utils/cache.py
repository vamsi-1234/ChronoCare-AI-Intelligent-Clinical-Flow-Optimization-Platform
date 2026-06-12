"""Optional Redis caching layer for ChronoCare AI.

The application degrades gracefully when Redis is unavailable — all cache
operations are silent no-ops so the rest of the stack is unaffected.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client: Any = None  # lazy singleton
_redis_available: Optional[bool] = None  # None = not yet tested


def _get_redis() -> Any:
    """Return a connected Redis client, or None if unavailable."""
    global _redis_client, _redis_available

    if _redis_available is False:
        return None  # Already confirmed unavailable; skip retry
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        import redis  # type: ignore

        client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("Redis cache connected at %s", redis_url)
        return _redis_client
    except Exception as exc:  # noqa: BLE001
        _redis_available = False
        logger.warning("Redis unavailable – running without cache: %s", exc)
        return None


def make_cache_key(prefix: str, data: Any) -> str:
    """Create a deterministic cache key from a prefix and arbitrary data."""
    payload = json.dumps(data, sort_keys=True, default=str)
    digest = hashlib.md5(payload.encode()).hexdigest()  # noqa: S324
    return f"chronocare:{prefix}:{digest}"


def cache_get(key: str) -> Optional[Any]:
    """Retrieve a cached value, returning *None* on any failure."""
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw:
            return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cache GET error for %s: %s", key, exc)
    return None


def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Store a value in cache with the given TTL (seconds).  Silently fails."""
    client = _get_redis()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cache SET error for %s: %s", key, exc)


def cache_delete(key: str) -> None:
    """Delete a cached key.  Silently fails."""
    client = _get_redis()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cache DEL error for %s: %s", key, exc)
