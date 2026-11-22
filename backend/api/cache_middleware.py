"""
Simple in-memory cache middleware for Flask API endpoints.
Adds ETag/If-None-Match support and response caching.
"""
import time
import hashlib
import json
from functools import wraps
from flask import request, jsonify, make_response

# In-memory cache: { key: { data, timestamp, etag } }
_response_cache = {}
_DEFAULT_TTL = 300  # 5 minutes

def cache_key_for_request():
    """Generate cache key from request path and query params."""
    path = request.path
    # Include sorted query params in key
    query = '&'.join(f"{k}={v}" for k, v in sorted(request.args.items()))
    raw = f"{path}?{query}" if query else path
    return hashlib.md5(raw.encode()).hexdigest()

def get_cached_response(key):
    """Get cached response if not expired."""
    entry = _response_cache.get(key)
    if not entry:
        return None
    if time.time() - entry['timestamp'] > entry.get('ttl', _DEFAULT_TTL):
        del _response_cache[key]
        return None
    return entry

def set_cached_response(key, data, ttl=None, etag=None):
    """Store response in cache."""
    if etag is None:
        # Generate ETag from content hash
        content = json.dumps(data, sort_keys=True, default=str)
        etag = f'"{hashlib.md5(content.encode()).hexdigest()[:16]}"'

    _response_cache[key] = {
        'data': data,
        'timestamp': time.time(),
        'ttl': ttl or _DEFAULT_TTL,
        'etag': etag,
    }
    return etag

def clear_cache(pattern=None):
    """Clear cache entries matching pattern (or all if None)."""
    global _response_cache
    if pattern is None:
        _response_cache.clear()
    else:
        keys_to_delete = [k for k in _response_cache if pattern in k]
        for k in keys_to_delete:
            del _response_cache[k]

def cached(ttl=None, key_prefix=None):
    """
    Decorator to cache JSON responses with ETag support.

    Usage:
        @bp.route("/finances")
        @cached(ttl=300)  # 5 min cache
        def get_finances():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Only cache GET requests
            if request.method != 'GET':
                return f(*args, **kwargs)

            # Build cache key
            base_key = cache_key_for_request()
            if key_prefix:
                base_key = f"{key_prefix}:{base_key}"

            # Check If-None-Match header (ETag)
            cached_entry = get_cached_response(base_key)
            if cached_entry:
                client_etag = request.headers.get('If-None-Match')
                if client_etag and client_etag == cached_entry['etag']:
                    # Return 304 Not Modified
                    resp = make_response('', 304)
                    resp.headers['ETag'] = cached_entry['etag']
                    resp.headers['Cache-Control'] = f'public, max-age={cached_entry["ttl"]}'
                    return resp

                # Return cached data with ETag
                resp = jsonify(cached_entry['data'])
                resp.headers['ETag'] = cached_entry['etag']
                resp.headers['Cache-Control'] = f'public, max-age={cached_entry["ttl"]}'
                resp.headers['X-Cache'] = 'HIT'
                return resp

            # Execute the actual endpoint
            result = f(*args, **kwargs)

            # Handle tuple returns (data, status) or just data
            if isinstance(result, tuple):
                data, status = result[0], result[1]
                headers = result[2] if len(result) > 2 else {}
            else:
                data = result
                status = 200
                headers = {}

            # Only cache successful responses
            if status == 200 and isinstance(data, (dict, list)):
                etag = set_cached_response(base_key, data, ttl)

                # Add headers to response
                if hasattr(data, 'headers'):
                    # Flask response object
                    resp = data
                else:
                    resp = jsonify(data)
                    resp.status_code = status

                resp.headers['ETag'] = etag
                resp.headers['Cache-Control'] = f'public, max-age={ttl or _DEFAULT_TTL}'
                resp.headers['X-Cache'] = 'MISS'

                for k, v in headers.items():
                    resp.headers[k] = v

                return resp

            return result
        return wrapped
    return decorator

def invalidate_on_write(*patterns):
    """
    Decorator for write endpoints (POST/PUT/DELETE) to invalidate related cache.

    Usage:
        @bp.route("/finances", methods=["POST"])
        @invalidate_on_write("finances", "governor")
        def create_finance():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            result = f(*args, **kwargs)
            # Only invalidate on successful writes
            if isinstance(result, tuple):
                status = result[1] if len(result) > 1 else 200
            elif hasattr(result, 'status_code'):
                status = result.status_code
            else:
                status = 200

            if 200 <= status < 300:
                for pattern in patterns:
                    clear_cache(pattern)
            return result
        return wrapped
    return decorator

# Stats endpoint for monitoring
def get_cache_stats():
    """Return cache statistics."""
    total = len(_response_cache)
    expired = sum(1 for e in _response_cache.values()
                  if time.time() - e['timestamp'] > e.get('ttl', _DEFAULT_TTL))
    return {
        'total_entries': total,
        'active_entries': total - expired,
        'expired_entries': expired,
    }