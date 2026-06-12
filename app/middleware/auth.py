"""Optional API key authentication for ChronoCare AI.

Disabled by default (ENABLE_AUTH=false) for easy local development.
Enable by setting ENABLE_AUTH=true and API_KEYS=key1,key2 in .env.

Default dev key: dev-chronocare-2026
"""
from __future__ import annotations

import os
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

_API_KEY_HEADER_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=_API_KEY_HEADER_NAME, auto_error=False)


def _get_valid_keys() -> set[str]:
    raw = os.getenv("API_KEYS", "dev-chronocare-2026")
    return {k.strip() for k in raw.split(",") if k.strip()}


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """FastAPI dependency – validates X-API-Key header when ENABLE_AUTH=true.

    When ENABLE_AUTH is false (default), all requests pass through.
    """
    enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    if not enable_auth:
        return "dev"
    if api_key and api_key in _get_valid_keys():
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "UNAUTHORIZED",
            "message": "Invalid or missing API key.",
            "hint": "Pass a valid key in the X-API-Key header.",
        },
    )
