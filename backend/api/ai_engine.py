from flask import Blueprint, request, jsonify
from api.utils.utils import get_db
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os

ai_bp = Blueprint("ai", __name__)

# AI Cache configuration
AI_CACHE_TTL_HOURS = int(os.getenv("AI_CACHE_TTL_HOURS", "24"))

def get_ai_cache_collection():
    """Get or create the AI cache collection, reusing the connection."""
    db = get_db()
    collection = db.ai_cache

    # Create TTL index for automatic cleanup if it doesn't exist
    try:
        collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            background=True
        )
    except Exception as e:
        # Index might already exist, which is fine
        pass

    return collection

def generate_cache_key(prompt: str, model: str, parameters: dict) -> str:
    """Generate a unique cache key for AI requests."""
    # Create a deterministic hash of the prompt, model, and parameters
    cache_data = {
        "prompt": prompt,
        "model": model,
        "parameters": parameters
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()

def cache_ai_response(prompt: str, model: str, parameters: dict, response: dict, ttl_hours: int = AI_CACHE_TTL_HOURS) -> bool:
    """Cache an AI response with TTL."""
    try:
        collection = get_ai_cache_collection()

        cache_key = generate_cache_key(prompt, model, parameters)
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

        cache_document = {
            "cache_key": cache_key,
            "prompt": prompt,
            "model": model,
            "parameters": parameters,
            "response": response,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "ttl_hours": ttl_hours
        }

        # Upsert: insert if doesn't exist, update if does
        collection.replace_one(
            {"cache_key": cache_key},
            cache_document,
            upsert=True
        )

        logging.info(f"Cached AI response with key: {cache_key[:16]}...")
        return True

    except Exception as e:
        logging.error(f"Failed to cache AI response: {e}")
        return False

def get_cached_ai_response(prompt: str, model: str, parameters: dict) -> dict | None:
    """Retrieve a cached AI response if it exists and hasn't expired."""
    try:
        collection = get_ai_cache_collection()

        cache_key = generate_cache_key(prompt, model, parameters)

        # Find the cache document (will automatically exclude expired ones due to TTL index)
        cached_doc = collection.find_one({"cache_key": cache_key})

        if cached_doc:
            logging.info(f"Cache hit for AI response with key: {cache_key[:16]}...")
            return cached_doc["response"]
        else:
            logging.info(f"Cache miss for AI response with key: {cache_key[:16]}...")
            return None

    except Exception as e:
        logging.error(f"Failed to retrieve cached AI response: {e}")
        return None

def call_claude_api(prompt: str, model: str = None) -> dict:
    """
    Call Claude API to get analysis.
    For now, this is a placeholder that returns mock data.
    In production, this would integrate with the actual Claude API.
    """
    # TODO: Implement actual Claude API call
    # For now, return structured mock data that matches expected format

    # This is a mock implementation - replace with actual Claude API call
    mock_response = {
        "narrative_fields": {
            "summary": "Mock analysis summary",
            "details": "This is a placeholder response"
        },
        "chart_data": {
            "sample_array": [1, 2, 3, 4, 5],
            "sample_labels": ["A", "B", "C", "D", "E"]
        }
    }

    return mock_response

def validate_and_extract_data(constituency_slug: str = None) -> dict:
    """
    Extract and validate data for AI analysis based on constituency slug.
    Returns structured data that can be passed to Claude for analysis.
    """
    try:
        db = get_db()

        # Get constituency data
        constituency_data = {}
        if constituency_slug:
            constituency = db.constituencies.find_one({"slug": constituency_slug})
            if not constituency:
                return {"error": f"Constituency not found: {constituency_slug}"}

            # Convert ObjectId to string
            constituency["_id"] = str(constituency["_id"])
            constituency_data["constituency"] = constituency

            # Get related allocations
            allocations = list(db.allocations.find({"constituency_slug": constituency_slug}))
            for alloc in allocations:
                alloc["_id"] = str(alloc["_id"])
            constituency_data["allocations"] = allocations

            # Get related audit findings
            audit_findings = list(db.audit_findings.find({"constituency_slug": constituency_slug}))
            for finding in audit_findings:
                finding["_id"] = str(finding["_id"])
            constituency_data["audit_findings"] = audit_findings

            # Get MP data
            mp = db.mps.find_one({"constituency_slug": constituency_slug})
            if mp:
                mp["_id"] = str(mp["_id"])
                constituency_data["mp"] = mp

        # Get governor data (always available)
        governor_data = {}

        governor_profile = db.county_leaders.find_one({})
        if governor_profile:
            governor_profile["_id"] = str(governor_profile["_id"])
            governor_data["profile"] = governor_profile

        finances = list(db.county_finances.find({}))
        for finance in finances:
            finance["_id"] = str(finance["_id"])
        governor_data["finances"] = finances

        audit_findings = list(db.county_audit.find({}))
        for finding in audit_findings:
            finding["_id"] = str(finding["_id"])
        governor_data["audit_findings"] = audit_findings

        departments = list(db.department_absorption.find({}))
        for dept in departments:
            dept["_id"] = str(dept["_id"])
        governor_data["departments"] = departments

        return {
            "constituency": constituency_data if constituency_slug else None,
            "governor": governor_data
        }

    except Exception as e:
        logging.error(f"Failed to extract data for AI analysis: {e}")
        return {"error": f"Data extraction failed: {str(e)}"}

# MP AI Modules
@ai_bp.route("/mp/<constituency_slug>/risk_score", methods=["GET"])
def mp_risk_score(constituency_slug):
    """AI Risk Scorer Module for MP/Constituency"""
    try:
        # Check cache first
        cache_parameters = {"constituency_slug": constituency_slug, "module": "risk_score"}
        cached_response = get_cached_ai_response(
            prompt=f"Analyze risk for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "risk_score",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = f"""
        Analyze the financial risk for the constituency with slug '{constituency_slug}'.
        Based on the following data, provide a risk assessment:

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "risk_level": "string (e.g., Low, Medium, High)",
            "summary": "string (brief summary of risk factors)"
          }},
          "chart_data": {{
            "risk_score": number (0-100 for gauge visualization),
            "citizen_actionspeer_scores": [{{"constituent": "string", "score": number}}],
            "allocation_trend": [{{"fy": "string", "amount": number, "anomaly_flag": boolean}}]
          }}
        }}
        """

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Analyze risk for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "risk_score",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP risk score: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/risk_level", methods=["GET"])
def mp_risk_level(constituency_slug):
    """AI Risk Level Analyzer Module for MP/Constituency"""
    try:
        # Check cache first
        cache_parameters = {"constituency_slug": constituency_slug, "module": "risk_level"}
        cached_response = get_cached_ai_response(
            prompt=f"Analyze risk level for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "risk_level",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = f"""
        Analyze the risk level and anomalies for the constituency with slug '{constituency_slug}'.
        Based on the following data, provide insights:

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "summary": "string (explanation of risk level)",
            "anomalies": "string (description of any anomalies found)",
            "citizen_actions": "string (recommended actions for citizens)"
          }},
          "chart_data": {{
            "peer_scores": [{{"constituent": "string", "score": number}}]
          }}
        }}
        """

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Analyze risk level for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "risk_level",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP risk level: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/summary", methods=["GET"])
def mp_summary(constituency_slug):
    """AI Summary Generator Module for MP/Constituency"""
    try:
        # Check cache first
        cache_parameters = {"constituency_slug": constituency_slug, "module": "summary"}
        cached_response = get_cached_ai_response(
            prompt=f"Generate summary for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "summary",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = f"""
        Generate a comprehensive summary for the constituency with slug '{constituency_slug}'.
        Based on the following data, provide insights:

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "summary": "string (comprehensive summary of constituency performance)"
          }},
          "chart_data": {{
            "key_metrics": [{{"label": "string", "value": number}}]
          }}
        }}
        """

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Generate summary for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "summary",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP summary: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/anomalies", methods=["GET"])
def mp_anomalies(constituency_slug):
    """AI Anomalies Detector Module for MP/Constituency"""
    try:
        # Check cache first
        cache_parameters = {"constituency_slug": constituency_slug, "module": "anomalies"}
        cached_response = get_cached_ai_response(
            prompt=f"Detect anomalies for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "anomalies",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = f"""
        Detect anomalies in the financial and audit data for the constituency with slug '{constituency_slug}'.
        Based on the following data, identify any anomalies:

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "summary": "string (description of anomalies found)",
            "details": "string (additional details about the anomalies)"
          }},
          "chart_data": {{
            "anomaly_points": [{{"fy": "string", "metric": "string", "value": number, "expected": number}}],
            "normal_range": [{{"fy": "string", "min": number, "max": number}}]
          }}
        }}
        """

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Detect anomalies for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "anomalies",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP anomalies: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# Additional MP modules would continue here...
# For brevity in this initial implementation, I'm showing the pattern
# The remaining modules would follow the same structure

# Health check endpoint for AI engine
@ai_bp.route("/health", methods=["GET"])
def ai_health():
    """Health check for AI engine"""
    try:
        # Test database connection
        db = get_db()
        # Try to access the ai_cache collection
        collection = db.ai_cache
        # This will throw an exception if there's a problem
        collection.find_one({})

        return jsonify({
            "status": "healthy",
            "service": "AI Engine",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "service": "AI Engine",
            "error": str(e)
        }), 503