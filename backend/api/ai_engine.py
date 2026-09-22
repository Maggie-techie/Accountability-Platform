from flask import Blueprint, request, jsonify
from api.database.connection import get_db
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

@ai_bp.route("/mp/<constituency_slug>/peer_rank", methods=["GET"])
def mp_peer_rank(constituency_slug):
    """AI Peer Rank Analyzer Module for MP/Constituency"""
    try:
        # Check cache first
        cache_parameters = {"constituency_slug": constituency_slug, "module": "peer_rank"}
        cached_response = get_cached_ai_response(
            prompt=f"Analyze peer ranking for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "peer_rank",
                "cached": True,
                "data": cached_response
            })
        
        db = get_db()

        # Extract data
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = f"""
        Analyze the peer ranking for the constituency with slug '{constituency_slug}' based on performance metrics.
        Compare this constituency to other constituencies in the county.

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}
        All Constituencies Data: {json.dumps(list(db.constituencies.find()), default=str)}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "ranking_explanation": "string (explanation of ranking methodology)",
            "insights": "string (key insights from peer comparison)"
          }},
          "chart_data": {{
            "peer_scores": [{{"constituent": "string", "score": number}}],
            "ranking_distribution": {{"excellent": number, "good": number, "average": number, "poor": number, "very_poor": number}}
          }}
        }}
        """

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Analyze peer ranking for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "peer_rank",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP peer rank: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/citizen_actions", methods=["GET"])
def mp_citizen_actions(constituency_slug):
    """AI Citizen Actions Recommender Module for MP/Constituency"""
    try:
        # Check cache first
        cache_parameters = {"constituency_slug": constituency_slug, "module": "citizen_actions"}
        cached_response = get_cached_ai_response(
            prompt=f"Generate citizen action recommendations for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "citizen_actions",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = f"""
        Generate recommended actions for citizens for the constituency with slug '{constituency_slug}'.
        Based on audit findings, financial data, and performance metrics, suggest specific actions citizens can take.

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "recommended_actions": "string (detailed recommended actions)",
            "priority_level": "string (High/Medium/Low priority)"
          }},
          "chart_data": {{
            "action_effectiveness": [{{"action": "string", "effectiveness": number, "cost": number}}],
            "implementation_timeline": [{{"phase": "string", "duration": number}}]
          }}
        }}
        """

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Generate citizen action recommendations for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "citizen_actions",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP citizen actions: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/data_sources", methods=["GET"])
def mp_data_sources(constituency_slug):
    """AI Data Sources Analyzer Module for MP/Constituency"""
    try:
        # Check cache first
        cache_parameters = {"constituency_slug": constituency_slug, "module": "data_sources"}
        cached_response = get_cached_ai_response(
            prompt=f"Analyze data sources for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "data_sources",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = f"""
        Evaluate the data sources and quality for the constituency with slug '{constituency_slug}'.
        Assess reliability, completeness, and timeliness of the data used for analysis.

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "data_quality_assessment": "string (overall data quality rating)",
            "source_reliability": "string (assessment of source reliability)"
          }},
          "chart_data": {{
            "source_scores": [{{"source": "string", "reliability": number, "completeness": number}}],
            "data_gaps": [{{"gap_type": "string", "severity": number}}]
          }}
        }}
        """

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Analyze data sources for constituency {constituency_slug}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "data_sources",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP data sources: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/cached_at", methods=["GET"])
def mp_cached_at(constituency_slug):
    """AI Cached At Tracker Module for MP/Constituency"""
    try:
        # Check if we have any cached data for this constituency
        db = get_db()
        cache_collection = db.ai_cache

        # Find the most recent cache entry for this constituency
        latest_cache = cache_collection.find_one(
            {"parameters.constituency_slug": constituency_slug},
            sort=[("created_at", -1)]
        )

        if latest_cache:
            return jsonify({
                "success": True,
                "module": "cached_at",
                "cached": True,
                "data": {
                    "last_cached": latest_cache["created_at"].isoformat() if isinstance(latest_cache["created_at"], datetime) else str(latest_cache["created_at"]),
                    "cache_ttl_hours": latest_cache.get("ttl_hours", AI_CACHE_TTL_HOURS),
                    "expires_at": latest_cache["expires_at"].isoformat() if isinstance(latest_cache["expires_at"], datetime) else str(latest_cache["expires_at"]),
                    "total_cache_entries": cache_collection.count_documents({"parameters.constituency_slug": constituency_slug})
                }
            })
        else:
            return jsonify({
                "success": True,
                "module": "cached_at",
                "cached": False,
                "data": {
                    "last_cached": None,
                    "cache_ttl_hours": AI_CACHE_TTL_HOURS,
                    "expires_at": None,
                    "total_cache_entries": 0
                }
            })

    except Exception as e:
        logging.error(f"Error in MP cached at: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# Governor AI Modules
@ai_bp.route("/governor/fiscal_health", methods=["GET"])
def governor_fiscal_health():
    """AI Fiscal Health Scorer Module for Governor"""
    try:
        # Check cache first
        cache_parameters = {"module": "fiscal_health"}
        cached_response = get_cached_ai_response(
            prompt="Analyze fiscal health of county government",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "fiscal_health",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data()  # No constituency slug for governor-wide analysis
        if "error" in data:
            return jsonify({"error": data["error"]}), 404
        
        # Fix the prompt formatting
        prompt = """
        Analyze the fiscal health of the county government based on financial data, audit findings, and department performance.
        Assess overall financial stability, sustainability, and performance.

        Governor Data: {governor_data}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "health_level": "string (e.g., Strong, Moderate, Weak)",
            "budget_summary": "string (summary of budget performance)",
            "osr_analysis": "string (Own Source Revenue analysis)"
          }},
          "chart_data": {{
            "health_score": number (0-100 for gauge visualization),
            "revenue_trend": [{{"fy": "string", "equitable": number, "conditional": number, "osr": number, "health": number}}],
            "osr_trend": [{{"fy": "string", "target": number, "actual": number}}]
          }}
        }}
        """.format(governor_data=json.dumps(data.get('governor', {}), default=str))

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt="Analyze fiscal health of county government",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "fiscal_health",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor fiscal health: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/dept_absorption", methods=["GET"])
def governor_dept_absorption():
    """AI Dept Absorption Analyst Module for Governor"""
    try:
        # Check cache first
        cache_parameters = {"module": "dept_absorption"}
        cached_response = get_cached_ai_response(
            prompt="Analyze department budget absorption rates",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "dept_absorption",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data()  # No constituency slug for governor-wide analysis
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = """
        Analyze department budget absorption rates and identify risks.
        Assess how well departments are utilizing their allocated budgets.

        Governor Data: {governor_data}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "risk_flag": "string (overall risk indicator)",
            "projections": "string (year-end projection explanations)"
          }},
          "chart_data": {{
            "dept_absorption": [{{"name": "string", "pct": number, "risk_level": string}}]
          }}
        }}
        """.format(governor_data=json.dumps(data.get('governor', {}), default=str))

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt="Analyze department budget absorption rates",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "dept_absorption",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor dept absorption: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/osr_analysis", methods=["GET"])
def governor_osr_analysis():
    """AI OSR Analyser Module for Governor"""
    try:
        # Check cache first
        cache_parameters = {"module": "osr_analysis"}
        cached_response = get_cached_ai_response(
            prompt="Analyze Own Source Revenue (OSR) performance",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "osr_analysis",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data()  # No constituency slug for governor-wide analysis
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = """
        Analyze Own Source Revenue (OSR) performance and trends.
        Evaluate the county's ability to generate revenue from local sources.

        Governor Data: {governor_data}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "osr_performance": "string (assessment of OSR performance)",
            "trend_analysis": "string (analysis of OSR trends over time)"
          }},
          "chart_data": {{
            "osr_breakdown": [{{"source": "string", "amount": number, "percentage": number}}],
            "osr_growth": [{{"fy": "string", "growth_rate": number}}]
          }}
        }}
        """.format(governor_data=json.dumps(data.get('governor', {}), default=str))

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt="Analyze Own Source Revenue (OSR) performance",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "osr_analysis",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor osr analysis: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/department_flags", methods=["GET"])
def governor_department_flags():
    """AI Department Flags Module for Governor"""
    try:
        # Check cache first
        cache_parameters = {"module": "department_flags"}
        cached_response = get_cached_ai_response(
            prompt="Identify department-specific risk flags",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "department_flags",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data()  # No constituency slug for governor-wide analysis
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = """
        Identify department-specific risk flags based on budget performance and audit findings.
        Highlight departments that require attention or intervention.

        Governor Data: {governor_data}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "flags_summary": "string (summary of identified flags)",
            "recommendations": "string (recommended actions for flagged departments)"
          }},
          "chart_data": {{
            "dept_risk_scores": [{{"name": "string", "risk_score": number, "risk_level": string}}],
            "trend_indicators": [{{"name": "string", "trend": "string", "significance": number}}]
          }}
        }}
        """.format(governor_data=json.dumps(data.get('governor', {}), default=str))

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt="Identify department-specific risk flags",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "department_flags",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor department flags: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/top_risks", methods=["GET"])
def governor_top_risks():
    """AI Top Risks & Citizen Actions Module for Governor"""
    try:
        # Check cache first
        cache_parameters = {"module": "top_risks"}
        cached_response = get_cached_ai_response(
            prompt="Identify top risks and recommend citizen actions for county government",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "top_risks",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data()  # No constituency slug for governor-wide analysis
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = """
        Identify the top risks facing the county government and recommend citizen actions.
        Assess financial, operational, and governance risks that could impact service delivery.

        Governor Data: {governor_data}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "top_risks": "string (description of top risks)",
            "citizen_guidance": "string (guidance for citizen engagement)"
          }},
          "chart_data": {{
            "risk_matrix": [{{"risk": "string", "impact": number, "likelihood": number}}],
            "action_impact": [{{"action": "string", "impact": number, "feasibility": number}}]
          }}
        }}
        """.format(governor_data=json.dumps(data.get('governor', {}), default=str))

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt="Identify top risks and recommend citizen actions for county government",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "top_risks",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor top risks: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# County-Level Modules
@ai_bp.route("/county/narrative", methods=["GET"])
def county_narrative():
    """AI County Narrative Generator Module"""
    try:
        # Check cache first
        cache_parameters = {"module": "county_narrative"}
        cached_response = get_cached_ai_response(
            prompt="Generate county narrative covering both MP and Governor perspectives",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "county_narrative",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data()  # No constituency slug for county-wide analysis
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = """
        Generate a comprehensive county narrative covering both MP (NG-CDF) and Governor (county executive) perspectives.
        Include analysis of cross-leader relationships, shared risks, and collaborative opportunities.

        Governor Data: {governor_data}
        Constituency Data Summary: {constituency_data_summary}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "mp_paragraph": "string (NG-CDF/MP perspective narrative)",
            "governor_paragraph": "string (county executive perspective narrative)",
            "county_health_score": number (0-100 for doughnut gauge visualization)
          }},
          "chart_data": {{
            "cross_leader_anomalies": [{{"type": "string", "description": "string", "severity": number}}],
            "constituency_risk_scores": [{{"name": "string", "score": number}}]
          }}
        }}
        """.format(
            governor_data=json.dumps(data.get('governor', {}), default=str),
            constituency_data_summary=json.dumps("Aggregated constituency data", default=str) if not data.get('constituency') else json.dumps(data.get('constituency', {}), default=str)
        )

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt="Generate county narrative covering both MP and Governor perspectives",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "county_narrative",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in county narrative: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# Finding Classifier Module
@ai_bp.route("/findings/classifier", methods=["POST"])
def findings_classifier():
    """AI Finding Classifier Module"""
    try:
        # Get request data
        request_data = request.get_json(silent=True) or {}
        finding_id = request_data.get("finding_id")
        finding_text = request_data.get("finding_text")

        # Check cache first (if we have specific finding data)
        cache_parameters = {
            "module": "finding_classifier",
            "finding_id": finding_id,
            "finding_text": finding_text
        }

        # Only check cache if we have specific finding identifiers
        if finding_id or finding_text:
            cached_response = get_cached_ai_response(
                prompt=f"Classify and analyze audit finding: {finding_text or finding_id}",
                model="claude",
                parameters=cache_parameters
            )

            if cached_response:
                return jsonify({
                    "success": True,
                    "module": "finding_classifier",
                    "cached": True,
                    "data": cached_response
                })

        # Extract data (governor-wide findings analysis)
        data = validate_and_extract_data()  # No constituency slug for analysis of all findings
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = """
        Classify and analyze audit findings from both MP (NG-CDF) and Governor (county executive) sources.
        Categorize by severity, provide plain English summaries, and recommend actions.

        Focus on the following finding: {finding_context}

        Governor Data: {governor_data}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "severity": "string (High/Medium/Low overall severity)",
            "plain_english_summary": "string (accessible summary of findings)",
            "recommended_action": "string (recommended course of action)"
          }},
          "chart_data": {{
            "severity_counts": {{"high": number, "medium": number, "low": number}},
            "findings_by_constituency": [{{"name": "string", "count": number}}]
          }}
        }}
        """.format(
            finding_context=finding_text or finding_id or "all audit findings",
            governor_data=json.dumps(data.get('governor', {}), default=str)
        )

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response (if we have specific identifiers)
        if finding_id or finding_text:
            cache_ai_response(
                prompt=f"Classify and analyze audit finding: {finding_text or finding_id}",
                model="claude",
                parameters=cache_parameters,
                response=ai_response
            )

        return jsonify({
            "success": True,
            "module": "finding_classifier",
            "cached": bool(finding_id or finding_text),
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in findings classifier: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# Cross-Leader Comparator Module
@ai_bp.route("/compare", methods=["POST"])
def compare_leaders():
    """AI Cross-Leader Comparator Module"""
    try:
        # Get request data
        request_data = request.get_json(silent=True) or {}
        leader1_type = request_data.get("leader1_type", "governor")  # governor or constituency
        leader1_id = request_data.get("leader1_id")  # governor name or constituency slug
        leader2_type = request_data.get("leader2_type", "constituency")  # governor or constituency
        leader2_id = request_data.get("leader2_id")  # governor name or constituency slug

        # Check cache first
        cache_parameters = {
            "module": "compare",
            "leader1_type": leader1_type,
            "leader1_id": leader1_id,
            "leader2_type": leader2_type,
            "leader2_id": leader2_id
        }

        cached_response = get_cached_ai_response(
            prompt=f"Compare {leader1_type} {leader1_id} with {leader2_type} {leader2_id}",
            model="claude",
            parameters=cache_parameters
        )

        if cached_response:
            return jsonify({
                "success": True,
                "module": "compare",
                "cached": True,
                "data": cached_response
            })

        # Extract data
        data = validate_and_extract_data(leader1_id if leader1_type == "constituency" else None)
        # Also get data for second leader if it's a constituency
        data2 = {}
        if leader2_type == "constituency" and leader2_id:
            data2 = validate_and_extract_data(leader2_id)
            if "error" in data2:
                return jsonify({"error": data2["error"]}), 404

        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Prepare prompt for Claude
        prompt = """
        Compare MP (NG-CDF legislative) and Governor (county executive) performance across multiple dimensions.
        Analyze allocation effectiveness, audit outcomes, correct appropriations, budget absorption, and fiscal health.

        Leader 1 ({leader1_type}): {leader1_data}
        Leader 2 ({leader2_type}): {leader2_data}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "comparative_analysis": "string (detailed comparison analysis)",
            "stronger_track": "string (which track performs better overall)",
            "reasoning": "string (explanation of reasoning behind assessment)"
          }},
          "chart_data": {{
            "radar_data": {{
              "mp_track": {{"allocation": number, "audit_findings": number, "correct_appropriations": number, "absorption_rate": number, "fiscal_health": number}},
              "governor_track": {{"allocation": number, "audit_findings": number, "correct_appropriations": number, "absorption_rate": number, "fiscal_health": number}}
            }}
          }}
        }}
        """.format(
            leader1_type=leader1_type,
            leader1_data=json.dumps(data.get('constituency' if leader1_type == 'constituency' else 'governor', {}), default=str) if (leader1_type == 'constituency' and data.get('constituency')) or (leader1_type == 'governor' and data.get('governor')) else "{}",
            leader2_type=leader2_type,
            leader2_data=json.dumps(data2.get('constituency' if leader2_type == 'constituency' else 'governor', {}), default=str) if (leader2_type == 'constituency' and data2.get('constituency')) or (leader2_type == 'governor' and data2.get('governor')) else "{}"
        )

        # Call Claude API (mock for now)
        ai_response = call_claude_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=f"Compare {leader1_type} {leader1_id} with {leader2_type} {leader2_id}",
            model="claude",
            parameters=cache_parameters,
            response=ai_response
        )

        return jsonify({
            "success": True,
            "module": "compare",
            "cached": False,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in compare leaders: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

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