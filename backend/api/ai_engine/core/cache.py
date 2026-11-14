"""
AI Response Cache with TTL and stampede protection.
MongoDB-backed with in-memory locks for thundering herd prevention.
"""
import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import current_app
from api.database.connection import get_db

logger = logging.getLogger(__name__)

# Configuration
AI_CACHE_TTL_HOURS = int(os.getenv("AI_CACHE_TTL_HOURS", "24"))
DISABLE_AI_CACHE = os.getenv("DISABLE_AI_CACHE", "false").lower() == "true"

# In-memory locks for cache keys (prevents thundering herd)
# For multi-worker deployments, consider Redis or MongoDB-based locks
_cache_locks = {}
_locks_lock = threading.Lock()


def get_cache_lock(cache_key: str) -> threading.Lock:
    """Get or create a lock for a specific cache key."""
    with _locks_lock:
        if cache_key not in _cache_locks:
            _cache_locks[cache_key] = threading.Lock()
        return _cache_locks[cache_key]


# Lazy index creation
_index_created = False


def _ensure_cache_index():
    """Ensure the cache TTL index exists. Called lazily on first cache access."""
    global _index_created
    if _index_created:
        return
    try:
        collection = get_db().ai_cache
        collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            background=True
        )
        _index_created = True
    except Exception as e:
        logger.warning(f"Could not create cache index: {e}")


def get_ai_cache_collection():
    """Get the AI cache collection."""
    _ensure_cache_index()
    return get_db().ai_cache


def generate_cache_key(prompt: str, model: str, parameters: dict) -> str:
    """Generate a unique cache key for AI requests."""
    cache_data = {
        "prompt": prompt,
        "model": model,
        "parameters": parameters
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()


def cache_ai_response(
    prompt: str,
    model: str,
    parameters: dict,
    response: dict,
    ttl_hours: int = AI_CACHE_TTL_HOURS
) -> bool:
    """Cache an AI response with TTL. Skips caching if response has _error flag."""
    if response.get("_error"):
        return False

    if DISABLE_AI_CACHE:
        return False

    try:
        collection = get_ai_cache_collection()
        cache_key = generate_cache_key(prompt, model, parameters)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        cache_document = {
            "cache_key": cache_key,
            "prompt": prompt,
            "model": model,
            "parameters": parameters,
            "response": response,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "ttl_hours": ttl_hours
        }

        collection.replace_one(
            {"cache_key": cache_key},
            cache_document,
            upsert=True
        )

        logger.info(f"Cached AI response with key: {cache_key[:16]}...")
        return True

    except Exception as e:
        logger.error(f"Failed to cache AI response: {e}")
        return False


def get_cached_ai_response(
    prompt: str,
    model: str,
    parameters: dict
) -> Optional[dict]:
    """Retrieve a cached AI response if it exists and hasn't expired."""
    if DISABLE_AI_CACHE:
        return None

    try:
        collection = get_ai_cache_collection()
        cache_key = generate_cache_key(prompt, model, parameters)

        # Filter out expired entries (TTL index may not have cleaned up yet)
        now = datetime.now(timezone.utc)
        cached_doc = collection.find_one({
            "cache_key": cache_key,
            "expires_at": {"$gt": now}
        })

        if cached_doc:
            logger.info(f"Cache hit for AI response with key: {cache_key[:16]}...")
            return cached_doc["response"]
        else:
            logger.info(f"Cache miss for AI response with key: {cache_key[:16]}...")
            return None

    except Exception as e:
        logger.error(f"Failed to retrieve cached AI response: {e}")
        return None


def get_or_compute_ai_response(
    prompt: str,
    model: str,
    parameters: dict,
    compute_fn,
    ttl_hours: int = AI_CACHE_TTL_HOURS
) -> dict:
    """
    Get cached response or compute and cache it with stampede protection.

    This prevents the thundering herd problem where multiple concurrent requests
    for the same cache key all miss the cache and hit the API simultaneously.

    Set DISABLE_AI_CACHE=true in environment to bypass cache entirely.
    """
    # Bypass cache entirely if disabled
    if DISABLE_AI_CACHE:
        logger.info("AI cache disabled, computing response directly")
        return compute_fn(prompt, model)

    cache_key = generate_cache_key(prompt, model, parameters)
    lock = get_cache_lock(cache_key)

    # Fast path: try cache without lock
    cached = get_cached_ai_response(prompt, model, parameters)
    if cached is not None:
        return cached

    # Cache miss: acquire lock
    acquired = lock.acquire(timeout=30)
    try:
        if acquired:
            # Double-check cache after acquiring lock
            cached = get_cached_ai_response(prompt, model, parameters)
            if cached is not None:
                return cached

        # Compute the response
        logger.info(f"Computing AI response for cache key: {cache_key[:16]}...")
        response = compute_fn(prompt, model)

        # Cache only successful responses
        if not response.get("_error"):
            cache_ai_response(prompt, model, parameters, response, ttl_hours)

        return response
    finally:
        if acquired:
            lock.release()


def get_cache_stats(constituency_slug: str = None) -> dict:
    """Get cache statistics for a constituency or globally."""
    try:
        collection = get_ai_cache_collection()

        if constituency_slug:
            filter_params = {"parameters.constituency_slug": constituency_slug}
        else:
            filter_params = {}

        total = collection.count_documents(filter_params)

        # Get latest cache entry
        latest = collection.find_one(filter_params, sort=[("created_at", -1)])

        return {
            "total_entries": total,
            "latest_cached": latest["created_at"].isoformat() if latest and latest.get("created_at") else None,
            "expires_at": latest["expires_at"].isoformat() if latest and latest.get("expires_at") else None,
            "ttl_hours": latest.get("ttl_hours", AI_CACHE_TTL_HOURS) if latest else AI_CACHE_TTL_HOURS
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {
            "total_entries": 0,
            "latest_cached": None,
            "expires_at": None,
            "ttl_hours": AI_CACHE_TTL_HOURS
        }