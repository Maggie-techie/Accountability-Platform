"""
AI Engine Package - Main entry point.
Registers all blueprints and provides unified API.
"""
from flask import Blueprint, jsonify

# Import all sub-blueprints
from .modules.mp import mp_bp
from .modules.governor import governor_bp
from .modules.county import county_bp
from .rag.assistant import assistant_bp

# Import auth and rate limiting
from .core.auth import init_ai_auth_and_rate_limiting, require_auth, optional_auth

# Create main AI blueprint
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

# Register sub-blueprints
ai_bp.register_blueprint(mp_bp)
ai_bp.register_blueprint(governor_bp)
ai_bp.register_blueprint(county_bp)
ai_bp.register_blueprint(assistant_bp)


# Health check endpoint
@ai_bp.route("/health", methods=["GET"])
def ai_health():
    """Health check for AI engine"""
    try:
        from api.database.connection import get_db
        db = get_db()
        collection = db.ai_cache
        collection.find_one({})

        from datetime import datetime, timezone
        return jsonify({
            "status": "healthy",
            "service": "AI Engine",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"AI health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "AI Engine"
        }), 503


# Version info endpoint
@ai_bp.route("/version", methods=["GET"])
def ai_version():
    """AI Engine version and configuration info"""
    import os
    return jsonify({
        "service": "AI Engine",
        "version": "2.0.0",
        "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        "cache_enabled": os.getenv("DISABLE_AI_CACHE", "false").lower() != "true",
        "cache_ttl_hours": int(os.getenv("AI_CACHE_TTL_HOURS", "24")),
        "endpoints": {
            "mp": [
                "/mp/<constituency_slug>/risk_score",
                "/mp/<constituency_slug>/risk_level",
                "/mp/<constituency_slug>/summary",
                "/mp/<constituency_slug>/anomalies",
                "/mp/<constituency_slug>/peer_rank",
                "/mp/<constituency_slug>/citizen_actions",
                "/mp/<constituency_slug>/data_sources",
                "/mp/<constituency_slug>/cached_at"
            ],
            "governor": [
                "/governor/fiscal_health",
                "/governor/dept_absorption",
                "/governor/osr_analysis",
                "/governor/department_flags",
                "/governor/top_risks"
            ],
            "county": [
                "/county/narrative",
                "/findings/classifier",
                "/compare"
            ],
            "assistant": [
                "/assistant",
                "/assistant/intent"
            ]
        }
    })


# Export main blueprint
__all__ = ["ai_bp"]