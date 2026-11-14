from flask import Blueprint, request, jsonify
from api.database.connection import get_db
from datetime import datetime, timedelta
import hashlib
import json
import logging
import os
import requests
import time
import threading
from dotenv import load_dotenv

load_dotenv()

ai_bp = Blueprint("ai", __name__)

# AI Cache configuration
AI_CACHE_TTL_HOURS = int(os.getenv("AI_CACHE_TTL_HOURS", "24"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

# In-memory locks for cache keys (prevents thundering herd)
# For multi-worker deployments, consider using Redis or MongoDB-based locks
_cache_locks = {}
_locks_lock = threading.Lock()

def get_cache_lock(cache_key: str) -> threading.Lock:
    """Get or create a lock for a specific cache key."""
    with _locks_lock:
        if cache_key not in _cache_locks:
            _cache_locks[cache_key] = threading.Lock()
        return _cache_locks[cache_key]

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


def get_or_compute_ai_response(prompt: str, model: str, parameters: dict, compute_fn, ttl_hours: int = AI_CACHE_TTL_HOURS) -> dict:
    """
    Get cached response or compute and cache it with stampede protection.

    This prevents the thundering herd problem where multiple concurrent requests
    for the same cache key all miss the cache and hit the API simultaneously.

    Args:
        prompt: The prompt for the AI
        model: The model to use
        parameters: Cache parameters (used for cache key)
        compute_fn: Function to call to compute the response (e.g., call_claude_api)
        ttl_hours: Cache TTL in hours

    Returns:
        The AI response (from cache or freshly computed)
    """
    cache_key = generate_cache_key(prompt, model, parameters)
    lock = get_cache_lock(cache_key)

    # Try to get from cache first (fast path)
    cached = get_cached_ai_response(prompt, model, parameters)
    if cached is not None:
        return cached

    # Cache miss - acquire lock to prevent stampede
    acquired = lock.acquire(timeout=30)  # Wait up to 30s for lock
    if not acquired:
        logging.warning(f"Could not acquire lock for cache key {cache_key[:16]}, proceeding without lock")
        # Fallback: try cache again, then compute if still missing
        cached = get_cached_ai_response(prompt, model, parameters)
        if cached is not None:
            return cached
    else:
        try:
            # Double-check cache after acquiring lock (another request may have populated it)
            cached = get_cached_ai_response(prompt, model, parameters)
            if cached is not None:
                return cached
        finally:
            # We don't release here - we'll release after computing
            pass

    try:
        # Compute the response
        logging.info(f"Computing AI response for cache key: {cache_key[:16]}...")
        response = compute_fn(prompt, model)

        # Cache the response
        cache_ai_response(prompt, model, parameters, response, ttl_hours)

        return response
    finally:
        # Always release the lock
        if acquired:
            lock.release()

def call_claude_api(prompt: str, model: str = None) -> dict:
    """
    Call Groq API to get analysis.
    Uses the Groq API key and model from environment.
    Includes retry logic with exponential backoff for rate limits (429).
    """
    # If model is not provided, use the default from environment
    if model is None:
        model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")

    # Check if API key is set
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logging.error("GROQ_API_KEY not set in environment variables")
        # Return a mock error response that matches the expected structure
        return {
            "narrative_fields": {
                "summary": "Error: Groq API key not configured",
                "details": "Please set the GROQ_API_KEY environment variable"
            },
            "chart_data": {
                "sample_array": [],
                "sample_labels": []
            }
        }

    # Groq API endpoint
    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"}
    }

    # Retry logic with exponential backoff for rate limits
    max_retries = 3
    base_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            # Handle rate limiting (429) with retry
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    # Extract retry-after header if present
                    retry_after = response.headers.get('retry-after')
                    if retry_after:
                        try:
                            delay = int(retry_after)
                        except ValueError:
                            delay = base_delay * (2 ** attempt)
                    else:
                        delay = base_delay * (2 ** attempt)

                    logging.warning(f"Rate limited (429). Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logging.error("Max retries reached for rate limit")
                    return {
                        "narrative_fields": {
                            "summary": "Error: Rate limit exceeded",
                            "details": "Too many requests to Groq API. Please wait a moment and try again."
                        },
                        "chart_data": {
                            "sample_array": [],
                            "sample_labels": []
                        }
                    }

            response.raise_for_status()  # Raise an exception for bad status codes

        result = response.json()

        # Extract the content from the first choice
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {})
            content = message.get("content", "")

            # Try to parse the content as JSON
            try:
                # The content might be a JSON string, or it might have extra text.
                # We assume the prompt instructs the model to return ONLY a JSON object.
                # We'll try to parse the entire content as JSON.
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse Groq response as JSON: {e}")
                logging.error(f"Response content: {content}")
                # Return a fallback structure
                return {
                    "narrative_fields": {
                        "summary": "Error: Failed to parse Groq response",
                        "details": f"Groq API returned invalid JSON: {str(e)}"
                    },
                    "chart_data": {
                        "sample_array": [],
                        "sample_labels": []
                    }
                }
        else:
            logging.error("No choices in Groq API response")
            return {
                "narrative_fields": {
                    "summary": "Error: Empty response from Groq API",
                    "details": "The Groq API returned no choices"
                },
                "chart_data": {
                    "sample_array": [],
                    "sample_labels": []
                }
            }
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to Groq API failed: {e}")
        return {
            "narrative_fields": {
                "summary": "Error: Groq API request failed",
                "details": f"Request error: {str(e)}"
            },
            "chart_data": {
                "sample_array": [],
                "sample_labels": []
            }
        }
    except Exception as e:
        logging.error(f"Unexpected error in call_claude_api: {e}")
        return {
            "narrative_fields": {
                "summary": "Error: Internal error in AI service",
                "details": f"Unexpected error: {str(e)}"
            },
            "chart_data": {
                "sample_array": [],
                "sample_labels": []
            }
        }


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


def generate_governor_summary(module: str) -> str:
    """Generate a concise summary of governor data for a specific AI module."""
    try:
        db = get_db()

        # Get key data
        profile = db.county_leaders.find_one({})
        finances = list(db.county_finances.find({}).sort("financial_year", 1))
        audit_findings = list(db.county_audit.find({}))
        departments = list(db.department_absorption.find({}))

        if module == "fiscal_health":
            # Summarize financial trends
            fin_summary = []
            for f in finances:
                fin_summary.append(f"FY {f.get('financial_year', 'N/A')}: Equitable KSh {f.get('equitable_share_kshb', 0):.1f}B, Conditional KSh {f.get('conditional_grants_kshb', 0):.1f}B, OSR KSh {f.get('osr_kshb', 0):.1f}B, Expenditure KSh {f.get('expenditure_kshb', 0):.1f}B")

            # Summarize audit findings
            total_flagged = sum(a.get('amount_flagged_kshm', 0) for a in audit_findings if a.get('finding_type') == 'misappropriation')
            mis_count = sum(1 for a in audit_findings if a.get('finding_type') == 'misappropriation')

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
FINANCIAL TRENDS:
{chr(10).join(fin_summary) if fin_summary else 'No financial data'}
AUDIT SUMMARY: {mis_count} misappropriation findings, KSh {total_flagged:,.1f}M flagged
DEPARTMENT COUNT: {len(departments)} departments
"""

        elif module == "dept_absorption":
            dept_summary = []
            for d in departments:
                dept_summary.append(f"{d.get('department', 'Unknown')}: {d.get('absorption_rate', 0):.1f}% absorption, KSh {d.get('budget_allocated_kshm', 0):,.0f}M allocated, KSh {d.get('expenditure_kshm', 0):,.0f}M spent")

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
DEPARTMENT ABSORPTION:
{chr(10).join(dept_summary) if dept_summary else 'No department data'}
"""

        elif module == "osr_analysis":
            osr_summary = []
            for f in finances:
                osr_summary.append(f"FY {f.get('financial_year', 'N/A')}: OSR KSh {f.get('osr_kshb', 0):.1f}B (Target: KSh {f.get('osr_target_kshb', 0):.1f}B)")

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
OSR TRENDS:
{chr(10).join(osr_summary) if osr_summary else 'No OSR data'}
"""

        elif module == "department_flags":
            flagged = [d for d in departments if d.get('absorption_rate', 0) < 50 or d.get('absorption_rate', 0) > 100]
            dept_summary = []
            for d in departments:
                risk = "HIGH" if d.get('absorption_rate', 0) < 50 else "MEDIUM" if d.get('absorption_rate', 0) < 70 else "LOW"
                dept_summary.append(f"{d.get('department', 'Unknown')}: {d.get('absorption_rate', 0):.1f}% absorption (Risk: {risk})")

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
DEPARTMENT RISK FLAGS ({len(flagged)} flagged):
{chr(10).join(dept_summary) if dept_summary else 'No department data'}
"""

        elif module == "top_risks":
            # Combine financial, audit, and department risks
            mis_count = sum(1 for a in audit_findings if a.get('finding_type') == 'misappropriation')
            total_flagged = sum(a.get('amount_flagged_kshm', 0) for a in audit_findings if a.get('finding_type') == 'misappropriation')
            low_absorption = [d for d in departments if d.get('absorption_rate', 0) < 70]

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
TOP RISKS:
- {mis_count} audit misappropriations (KSh {total_flagged:,.1f}M flagged)
- {len(low_absorption)} departments with <70% absorption
- Financial sustainability: {'CONCERN' if any(f.get('expenditure_kshb', 0) > f.get('equitable_share_kshb', 0) + f.get('conditional_grants_kshb', 0) + f.get('osr_kshb', 0) for f in finances) else 'STABLE'}
"""

        else:
            # Generic summary
            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
FINANCIAL YEARS: {len(finances)}
AUDIT FINDINGS: {len(audit_findings)} total
DEPARTMENTS: {len(departments)}
"""
    except Exception as e:
        logging.error(f"Failed to generate governor summary: {e}")
        return "Error generating summary"


def generate_constituency_summary(constituency_slug: str, module: str) -> str:
    """Generate a concise summary of constituency data for a specific AI module."""
    try:
        db = get_db()

        constituency = db.constituencies.find_one({"slug": constituency_slug})
        if not constituency:
            return f"Constituency not found: {constituency_slug}"

        allocations = list(db.allocations.find({"constituency_slug": constituency_slug}))
        audit_findings = list(db.audit_findings.find({"constituency_slug": constituency_slug}))
        mp = db.mps.find_one({"constituency_slug": constituency_slug})

        if module == "risk_score" or module == "risk_level" or module == "summary":
            total_alloc = sum(a.get('amount_kshm', 0) for a in allocations)
            mis_count = sum(1 for a in audit_findings if a.get('finding_type') == 'misappropriation')
            total_flagged = sum(a.get('amount_at_risk', 0) for a in audit_findings if a.get('finding_type') == 'misappropriation')

            alloc_summary = []
            for a in allocations:
                alloc_summary.append(f"FY {a.get('financial_year', 'N/A')}: KSh {a.get('amount_kshm', 0):,.0f}M ({a.get('category', 'Unknown')})")

            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
MP: {mp.get('name', 'Unknown') if mp else 'Unknown'}
TOTAL ALLOCATIONS: KSh {total_alloc:,.0f}M across {len(allocations)} records
AUDIT FINDINGS: {len(audit_findings)} total, {mis_count} misappropriations (KSh {total_flagged:,.0f}M at risk)
ALLOCATION DETAILS:
{chr(10).join(alloc_summary) if alloc_summary else 'No allocation data'}
"""

        elif module == "anomalies":
            # Include GNN anomalies and high-severity audit findings
            gnn_anomalies = list(db.gnn_anomalies.find({"metadata.constituency_slug": constituency_slug}))
            high_severity = list(db.audit_findings.find({"constituency_slug": constituency_slug, "finding_type": "misappropriation"}))

            gnn_summary = []
            for a in gnn_anomalies:
                gnn_summary.append(f"Score: {a.get('anomaly_score', 0):.2f}, Rank: {a.get('anomaly_rank', 'N/A')}, FY: {a.get('metadata', {}).get('fiscal_year', 'Unknown')}")

            audit_summary = []
            for a in high_severity:
                audit_summary.append(f"FY {a.get('fy_reviewed', 'Unknown')}: {a.get('note', a.get('finding', 'Misappropriation'))}, Amount: {a.get('amount_at_risk', 'Unknown')}")

            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
MP: {mp.get('name', 'Unknown') if mp else 'Unknown'}
GNN ANOMALIES: {len(gnn_anomalies)} detected
{chr(10).join(gnn_summary) if gnn_summary else 'No GNN anomalies'}
HIGH-SEVERITY AUDIT FINDINGS: {len(high_severity)}
{chr(10).join(audit_summary) if audit_summary else 'No high-severity findings'}
"""

        elif module == "peer_rank":
            all_constituencies = list(db.constituencies.find({}))
            const_scores = []
            for c in all_constituencies:
                c_allocs = list(db.allocations.find({"constituency_slug": c["slug"]}))
                c_audits = list(db.audit_findings.find({"constituency_slug": c["slug"]}))
                total = sum(a.get('amount_kshm', 0) for a in c_allocs)
                mis = sum(1 for a in c_audits if a.get('finding_type') == 'misappropriation')
                const_scores.append(f"{c.get('name', c['slug'])}: KSh {total:,.0f}M allocated, {mis} misappropriations")

            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
PEER COMPARISON ({len(all_constituencies)} constituencies):
{chr(10).join(const_scores)}
"""

        else:
            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
ALLOCATIONS: {len(allocations)} records
AUDIT FINDINGS: {len(audit_findings)} total
MP: {mp.get('name', 'Unknown') if mp else 'Unknown'}
"""
    except Exception as e:
        logging.error(f"Failed to generate constituency summary: {e}")
        return f"Error generating summary for {constituency_slug}"

# MP AI Modules
@ai_bp.route("/mp/<constituency_slug>/risk_score", methods=["GET"])
def mp_risk_score(constituency_slug):
    """AI Risk Scorer Module for MP/Constituency"""
    try:
        # Extract data (for validation)
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Generate concise summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "risk_score")
        governor_summary = generate_governor_summary("risk_score")

        # Prepare prompt for Claude
        prompt = f"""
        Analyze the financial risk for the constituency with slug '{constituency_slug}'.
        Based on the following data, provide a risk assessment:

        Constituency Summary:
        {constituency_summary}

        Governor Summary:
        {governor_summary}

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

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"constituency_slug": constituency_slug, "module": "risk_score"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "risk_score",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP risk score: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/risk_level", methods=["GET"])
def mp_risk_level(constituency_slug):
    """AI Risk Level Analyzer Module for MP/Constituency"""
    try:
        # Extract data (for validation)
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Generate concise summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "risk_level")
        governor_summary = generate_governor_summary("risk_level")

        # Prepare prompt for Claude
        prompt = f"""
        Analyze the risk level and anomalies for the constituency with slug '{constituency_slug}'.
        Based on the following data, provide insights:

        Constituency Summary:
        {constituency_summary}

        Governor Summary:
        {governor_summary}

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

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"constituency_slug": constituency_slug, "module": "risk_level"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "risk_level",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP risk level: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/summary", methods=["GET"])
def mp_summary(constituency_slug):
    """AI Summary Generator Module for MP/Constituency"""
    try:
        # Extract data (for validation)
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Generate concise summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "summary")
        governor_summary = generate_governor_summary("summary")

        # Prepare prompt for Claude
        prompt = f"""
        Generate a comprehensive summary for the constituency with slug '{constituency_slug}'.
        Based on the following data, provide insights:

        Constituency Summary:
        {constituency_summary}

        Governor Summary:
        {governor_summary}

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

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"constituency_slug": constituency_slug, "module": "summary"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "summary",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP summary: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/anomalies", methods=["GET"])
def mp_anomalies(constituency_slug):
    """AI Anomalies Detector Module for MP/Constituency.
    Uses GNN-detected anomalies as context for LLM explanations."""
    try:
        # Extract data (for validation)
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Fetch GNN-detected anomalies for this constituency from database
        db = get_db()
        gnn_anomalies = list(db.gnn_anomalies.find({"metadata.constituency_slug": constituency_slug}))
        for a in gnn_anomalies:
            a["_id"] = str(a["_id"])

        # Fetch high-severity audit findings (misappropriations) for this constituency
        high_severity_findings = list(db.audit_findings.find({
            "constituency_slug": constituency_slug,
            "finding_type": "misappropriation"
        }))
        for f in high_severity_findings:
            f["_id"] = str(f["_id"])

        # Build GNN context for LLM
        gnn_context = ""
        if gnn_anomalies:
            gnn_context = "\n\nGNN MODEL DETECTED ANOMALIES (use as primary context):\n"
            for anomaly in gnn_anomalies:
                gnn_context += f"- {anomaly.get('explanation', 'Anomaly detected')}"
                gnn_context += f" (Score: {anomaly.get('anomaly_score', 0):.2f}, Rank: {anomaly.get('anomaly_rank', 'N/A')})"
                metadata = anomaly.get('metadata', {})
                gnn_context += f" [FY: {metadata.get('fiscal_year', 'Unknown')}]\n"
                features = anomaly.get('features', {})
                financial = features.get('financial', {})
                audit = features.get('audit', {})
                if financial.get('total_allocation_kshm'):
                    gnn_context += f"  Total Allocation: KSh {financial['total_allocation_kshm']:,.1f}M\n"
                if audit.get('num_findings'):
                    gnn_context += f"  Audit Findings: {audit['num_findings']} (Misappropriations: {audit.get('misappropriation_count', 0)})\n"
                if audit.get('amount_flagged_kshm'):
                    gnn_context += f"  Amount Flagged: KSh {audit['amount_flagged_kshm']:,.1f}M\n"
        else:
            gnn_context = "\n\nNo GNN-detected anomalies found for this constituency. The GNN model may not have been trained yet, or no anomalies were detected."

        # Add high-severity audit findings context
        audit_context = ""
        if high_severity_findings:
            audit_context = "\n\nHIGH-SEVERITY AUDIT FINDINGS (Misappropriations from Auditor-General reports):\n"
            for finding in high_severity_findings:
                audit_context += f"- {finding.get('note') or finding.get('finding', 'Misappropriation found')}"
                audit_context += f" [FY: {finding.get('fy_reviewed', 'Unknown')}]"
                if finding.get('amount_at_risk'):
                    audit_context += f" Amount at risk: {finding['amount_at_risk']}"
                audit_context += "\n"
        else:
            audit_context = "\n\nNo high-severity audit findings (misappropriations) found for this constituency in the current dataset."

        # Generate concise summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "anomalies")
        governor_summary = generate_governor_summary("anomalies")

        # Prepare prompt for Claude with GNN context
        prompt = f"""
        You are a financial analyst explaining anomalies and audit findings for the constituency '{constituency_slug}'.

        The Graph Neural Network (GNN) model analyzes constituency-year and governor-year nodes in a financial graph, detecting anomalies via:
        1. Graph reconstruction error (connectivity patterns)
        2. Embedding space distance to k-nearest neighbors
        3. Isolation Forest on node embeddings

        {gnn_context}
        {audit_context}

        Constituency Summary:
        {constituency_summary}

        Governor Summary:
        {governor_summary}

        Return ONLY a JSON object with exactly this structure:
        {{
          "narrative_fields": {{
            "summary": "string (plain-language summary of GNN anomalies AND high-severity audit findings for citizens)",
            "details": "string (detailed explanation combining GNN findings and audit misappropriations, why they matter, and recommended actions)"
          }},
          "chart_data": {{
            "anomaly_points": [{{"fy": "string", "metric": "string", "value": number, "expected": number}}],
            "normal_range": [{{"fy": "string", "min": number, "max": number}}]
          }}
        }}

        For anomaly_points, extract data from BOTH GNN anomalies and high-severity audit findings above.
        Include audit misappropriations as anomaly points with metric "Audit Misappropriation".
        For normal_range, provide typical ranges for the metrics based on the constituency's historical data.
        """

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"constituency_slug": constituency_slug, "module": "anomalies"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "anomalies",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP anomalies: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/peer_rank", methods=["GET"])
def mp_peer_rank(constituency_slug):
    """AI Peer Rank Analyzer Module for MP/Constituency"""
    try:
        # Extract data (for validation)
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Generate concise summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "peer_rank")
        governor_summary = generate_governor_summary("peer_rank")

        # Prepare prompt for Claude
        prompt = f"""
        Analyze the peer ranking for the constituency with slug '{constituency_slug}' based on performance metrics.
        Compare this constituency to other constituencies in the county.

        Constituency Summary:
        {constituency_summary}

        Governor Summary:
        {governor_summary}

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

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"constituency_slug": constituency_slug, "module": "peer_rank"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "peer_rank",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP peer rank: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/citizen_actions", methods=["GET"])
def mp_citizen_actions(constituency_slug):
    """AI Citizen Actions Recommender Module for MP/Constituency"""
    try:
        # Extract data (for validation)
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Generate concise summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "citizen_actions")
        governor_summary = generate_governor_summary("citizen_actions")

        # Prepare prompt for Claude
        prompt = f"""
        Generate recommended actions for citizens for the constituency with slug '{constituency_slug}'.
        Based on audit findings, financial data, and performance metrics, suggest specific actions citizens can take.

        Constituency Summary:
        {constituency_summary}

        Governor Summary:
        {governor_summary}

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

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"constituency_slug": constituency_slug, "module": "citizen_actions"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "citizen_actions",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP citizen actions: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/mp/<constituency_slug>/data_sources", methods=["GET"])
def mp_data_sources(constituency_slug):
    """AI Data Sources Analyzer Module for MP/Constituency"""
    try:
        # Extract data (for validation)
        data = validate_and_extract_data(constituency_slug)
        if "error" in data:
            return jsonify({"error": data["error"]}), 404

        # Generate concise summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "data_sources")
        governor_summary = generate_governor_summary("data_sources")

        # Prepare prompt for Claude
        prompt = f"""
        Evaluate the data sources and quality for the constituency with slug '{constituency_slug}'.
        Assess reliability, completeness, and timeliness of the data used for analysis.

        Constituency Summary:
        {constituency_summary}

        Governor Summary:
        {governor_summary}

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

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"constituency_slug": constituency_slug, "module": "data_sources"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "data_sources",
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
        # Generate concise summary for fiscal health analysis
        governor_summary = generate_governor_summary("fiscal_health")

        prompt = f"""
        Analyze the fiscal health of the county government based on financial data, audit findings, and department performance.
        Assess overall financial stability, sustainability, and performance.

        Governor Data Summary:
        {governor_summary}

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
        """

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"module": "fiscal_health"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "fiscal_health",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor fiscal health: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/dept_absorption", methods=["GET"])
def governor_dept_absorption():
    """AI Dept Absorption Analyst Module for Governor"""
    try:
        # Generate concise summary for department absorption analysis
        governor_summary = generate_governor_summary("dept_absorption")

        # Prepare prompt for Claude
        prompt = f"""
        Analyze department budget absorption rates and identify risks.
        Assess how well departments are utilizing their allocated budgets.

        Governor Data Summary:
        {governor_summary}

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
        """

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"module": "dept_absorption"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "dept_absorption",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor dept absorption: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/osr_analysis", methods=["GET"])
def governor_osr_analysis():
    """AI OSR Analyser Module for Governor"""
    try:
        # Generate concise summary for OSR analysis
        governor_summary = generate_governor_summary("osr_analysis")

        # Prepare prompt for Claude
        prompt = f"""
        Analyze Own Source Revenue (OSR) performance and trends.
        Evaluate the county's ability to generate revenue from local sources.

        Governor Data Summary:
        {governor_summary}

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
        """

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"module": "osr_analysis"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "osr_analysis",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor osr analysis: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/department_flags", methods=["GET"])
def governor_department_flags():
    """AI Department Flags Module for Governor"""
    try:
        # Generate concise summary for department flags analysis
        governor_summary = generate_governor_summary("department_flags")

        # Prepare prompt for Claude
        prompt = f"""
        Identify department-specific risk flags based on budget performance and audit findings.
        Highlight departments that require attention or intervention.

        Governor Data Summary:
        {governor_summary}

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
        """

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"module": "department_flags"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "department_flags",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor department flags: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@ai_bp.route("/governor/top_risks", methods=["GET"])
def governor_top_risks():
    """AI Top Risks & Citizen Actions Module for Governor"""
    try:
        # Generate concise summary for top risks analysis
        governor_summary = generate_governor_summary("top_risks")

        # Prepare prompt for Claude
        prompt = f"""
        Identify the top risks facing the county government and recommend citizen actions.
        Assess financial, operational, and governance risks that could impact service delivery.

        Governor Data Summary:
        {governor_summary}

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
        """

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"module": "top_risks"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "top_risks",
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
        # Generate concise summaries
        governor_summary = generate_governor_summary("county_narrative")

        # Get aggregated constituency summary
        db = get_db()
        all_constituencies = list(db.constituencies.find({}))
        const_summaries = []
        for c in all_constituencies:
            c_allocs = list(db.allocations.find({"constituency_slug": c["slug"]}))
            c_audits = list(db.audit_findings.find({"constituency_slug": c["slug"]}))
            total = sum(a.get('amount_kshm', 0) for a in c_allocs)
            mis = sum(1 for a in c_audits if a.get('finding_type') == 'misappropriation')
            const_summaries.append(f"{c.get('name', c['slug'])}: KSh {total:,.0f}M allocated, {mis} misappropriations")

        constituency_summary = "\n".join(const_summaries)

        # Prepare prompt for Claude
        prompt = f"""
        Generate a comprehensive county narrative covering both MP (NG-CDF) and Governor (county executive) perspectives.
        Include analysis of cross-leader relationships, shared risks, and collaborative opportunities.

        Governor Data Summary:
        {governor_summary}

        Constituency Data Summary:
        {constituency_summary}

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
        """

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {"module": "county_narrative"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "county_narrative",
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

        # Use get_or_compute_ai_response for stampede protection (only if we have specific identifiers for caching)
        cache_parameters = {
            "module": "finding_classifier",
            "finding_id": finding_id,
            "finding_text": finding_text
        }

        if finding_id or finding_text:
            ai_response = get_or_compute_ai_response(
                prompt=prompt,
                model="claude",
                parameters=cache_parameters,
                compute_fn=lambda p, m: call_claude_api(p, m)
            )
            cached = True
        else:
            # No caching for generic "all findings" request
            ai_response = call_claude_api(prompt)
            cached = False

        return jsonify({
            "success": True,
            "module": "finding_classifier",
            "cached": cached,
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

        # Use get_or_compute_ai_response for stampede protection
        cache_parameters = {
            "module": "compare",
            "leader1_type": leader1_type,
            "leader1_id": leader1_id,
            "leader2_type": leader2_type,
            "leader2_id": leader2_id
        }

        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model="claude",
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_claude_api(p, m)
        )

        return jsonify({
            "success": True,
            "module": "compare",
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