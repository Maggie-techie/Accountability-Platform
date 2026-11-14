"""
Authentication and Rate Limiting Middleware for AI Engine.
"""
import os
from functools import wraps
from flask import jsonify, request, current_app
from flask_jwt_extended import jwt_required, verify_jwt_in_request, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# ============================================================
# Rate Limiter Configuration
# ============================================================

def get_limiter_key():
    """Generate rate limit key based on user identity or IP."""
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except Exception:
        pass
    return f"ip:{get_remote_address()}"


def create_limiter(app=None):
    """
    Create and configure Flask-Limiter instance.

    Rate limits:
    - Default: 60 requests/minute per user/IP
    - AI endpoints: 30 requests/minute per user/IP (more restrictive)
    - Assistant/chat: 20 requests/minute per user/IP (most restrictive)
    """
    limiter = Limiter(
        key_func=get_limiter_key,
        app=app,
        default_limits=["60 per minute"],
        storage_uri=os.getenv("RATE_LIMIT_STORAGE_URL", "memory://"),
        strategy="fixed-window",
        headers_enabled=True,
        # Retry-After header for rate limited responses
        header_name_mapping={
            "X-RateLimit-Limit": "X-RateLimit-Limit",
            "X-RateLimit-Remaining": "X-RateLimit-Remaining",
            "X-RateLimit-Reset": "X-RateLimit-Reset",
            "Retry-After": "Retry-After"
        }
    )
    return limiter


# ============================================================
# Decorators for AI Endpoints
# ============================================================

def ai_rate_limit(limit: str = "30 per minute"):
    """
    Decorator to apply specific rate limit to AI endpoints.
    Usage: @ai_rate_limit("30 per minute")
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Rate limiting is handled by Flask-Limiter at the blueprint level
            # This decorator is a marker for documentation
            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_auth(f):
    """
    Decorator to require JWT authentication.
    Can be used instead of @jwt_required for consistency.
    """
    @wraps(f)
    @jwt_required()
    def wrapped(*args, **kwargs):
        return f(*args, **kwargs)
    return wrapped


def optional_auth(f):
    """
    Decorator for endpoints that work with or without auth.
    Verifies JWT if present but doesn't require it.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        verify_jwt_in_request(optional=True)
        return f(*args, **kwargs)
    return wrapped


# ============================================================
# Rate Limit Exemptions
# ============================================================

# Endpoints that should be exempt from rate limiting (health checks, etc.)
RATE_LIMIT_EXEMPT_ENDPOINTS = {
    "ai.ai_health",
    "ai.ai_version",
}


def is_rate_limit_exempt(endpoint: str) -> bool:
    """Check if an endpoint should be exempt from rate limiting."""
    return endpoint in RATE_LIMIT_EXEMPT_ENDPOINTS


# ============================================================
# Error Handlers
# ============================================================

def register_rate_limit_handlers(app):
    """Register custom error handlers for rate limiting."""

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": getattr(e, "retry_after", 60)
        }), 429


# ============================================================
# Initialization Function
# ============================================================

def init_ai_auth_and_rate_limiting(app, ai_blueprint):
    """
    Initialize authentication and rate limiting for AI engine.

    Args:
        app: Flask application instance
        ai_blueprint: The main AI blueprint to apply limits to
    """
    # Create limiter
    limiter = create_limiter(app)

    # Apply rate limits to AI blueprint
    # Different limits for different endpoint groups

    # Health/version - exempt
    limiter.exempt(ai_blueprint, methods=["GET"])

    # MP endpoints - 30/min
    from api.ai_engine.modules.mp import mp_bp
    limiter.limit("30 per minute")(mp_bp)

    # Governor endpoints - 30/min
    from api.ai_engine.modules.governor import governor_bp
    limiter.limit("30 per minute")(governor_bp)

    # County endpoints - 30/min
    from api.ai_engine.modules.county import county_bp
    limiter.limit("30 per minute")(county_bp)

    # Assistant endpoints - 20/min (more restrictive for chat)
    from api.ai_engine.rag.assistant import assistant_bp
    limiter.limit("20 per minute")(assistant_bp)

    # Register error handlers
    register_rate_limit_handlers(app)

    return limiter