"""Prediction service – thin wrapper around the ML model layer.

All heavy lifting is done in ``app.ml.models``.  This module adds:
  - Redis caching
  - Input pre-processing / enrichment
  - Logging
"""
from __future__ import annotations

import logging
from typing import Any

from app.ml.models import predict_duration as _predict_duration
from app.ml.models import predict_noshow as _predict_noshow
from app.utils.cache import cache_get, cache_set, make_cache_key

logger = logging.getLogger(__name__)

_DURATION_TTL = 300  # 5 minutes
_NOSHOW_TTL = 300


def predict_duration(data: dict[str, Any]) -> dict[str, Any]:
    """Return duration prediction, using cache when available."""
    key = make_cache_key("duration", data)
    cached = cache_get(key)
    if cached:
        logger.debug("Cache HIT duration %s", key)
        return cached

    result = _predict_duration(data)
    cache_set(key, result, ttl=_DURATION_TTL)
    return result


def predict_no_show(data: dict[str, Any]) -> dict[str, Any]:
    """Return no-show prediction, using cache when available."""
    key = make_cache_key("noshow", data)
    cached = cache_get(key)
    if cached:
        logger.debug("Cache HIT noshow %s", key)
        return cached

    result = _predict_noshow(data)
    cache_set(key, result, ttl=_NOSHOW_TTL)
    return result
