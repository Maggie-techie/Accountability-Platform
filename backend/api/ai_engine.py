from flask import Blueprint, request, jsonify
from api.database.connection import get_db
from datetime import datetime, timedelta, timezone
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
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

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


def _error(summary: str, details: str) -> dict:
    """Return a standardized error response that won't be cached."""
    return {
        "_error": True,
        "narrative_fields": {
            "summary": f"Error: {summary}",
            "details": details
        },
        "chart_data": {
            "sample_array": [],
            "sample_labels": []
        }
    }


# Create TTL index once at startup
def _ensure_cache_index():
    """Ensure the cache TTL index exists. Call once at app startup."""
    try:
        collection = get_db().ai_cache
        collection.create_index(
            "expires_at",
            expireAfterSeconds=0,
            background=True
        )
    except Exception:
        pass


_ensure_cache_index()


def get_ai_cache_collection():
    """Get the AI cache collection."""
    db = get_db()
    return db.ai_cache


def generate_cache_key(prompt: str, model: str, parameters: dict) -> str:
    """Generate a unique cache key for AI requests."""
    cache_data = {
        "prompt": prompt,
        "model": model,
        "parameters": parameters
    }
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_string.encode()).hexdigest()


def cache_ai_response(prompt: str, model: str, parameters: dict, response: dict, ttl_hours: int = AI_CACHE_TTL_HOURS) -> bool:
    """Cache an AI response with TTL. Skips caching if response has _error flag."""
    if response.get("_error"):
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

        # Filter out expired entries (TTL index may not have cleaned up yet)
        now = datetime.now(timezone.utc)
        cached_doc = collection.find_one({
            "cache_key": cache_key,
            "expires_at": {"$gt": now}
        })

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
    """
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
        logging.info(f"Computing AI response for cache key: {cache_key[:16]}...")
        response = compute_fn(prompt, model)

        # Cache only successful responses
        if not response.get("_error"):
            cache_ai_response(prompt, model, parameters, response, ttl_hours)

        return response
    finally:
        if acquired:
            lock.release()


def call_llm_api(prompt: str, model: str = None) -> dict:
    """
    Call Groq API to get analysis.
    Uses the Groq API key and model from environment.
    Includes retry logic with exponential backoff for rate limits (429).
    """
    if model is None:
        model = GROQ_MODEL

    api_key = GROQ_API_KEY
    if not api_key:
        logging.error("GROQ_API_KEY not set in environment variables")
        return _error("Groq API key not configured", "Please set the GROQ_API_KEY environment variable")

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
        "temperature": 0.2,
        "max_tokens": 4000,
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
                    return _error("Rate limit exceeded", "Too many requests to Groq API. Please wait a moment and try again.")

            if not response.ok:
                logging.error(f"Groq {response.status_code}: {response.text[:300]}")
                response.raise_for_status()

            result = response.json()

            # Extract the content from the first choice
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                finish_reason = result["choices"][0].get("finish_reason")

                # Try to parse the content as JSON
                try:
                    parsed = json.loads(content)
                    return parsed
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse Groq response as JSON: {e}")
                    logging.error(f"Finish reason: {finish_reason}")
                    logging.error(f"Response content: {content[:500]}")
                    return _error("Failed to parse Groq response", f"Groq API returned invalid JSON: {str(e)}")
            else:
                logging.error("No choices in Groq API response")
                return _error("Empty response from Groq API", "The Groq API returned no choices")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request to Groq API failed: {e}")
            return _error("Groq API request failed", "Network or request error")
        except Exception as e:
            logging.error(f"Unexpected error in call_llm_api: {e}")
            return _error("Internal error in AI service", "Unexpected error")


def validate_constituency_exists(constituency_slug: str) -> bool:
    """Lightweight check that constituency exists."""
    try:
        db = get_db()
        return db.constituencies.find_one({"slug": constituency_slug}, {"_id": 1}) is not None
    except Exception as e:
        logging.error(f"Failed to validate constituency: {e}")
        return False


def generate_governor_summary(module: str) -> str:
    """Generate a concise summary of governor data for a specific AI module."""
    try:
        db = get_db()

        profile = db.county_leaders.find_one({})
        finances = list(db.county_finances.find({}).sort("financial_year", 1))
        audit_findings = list(db.county_audit.find({}))
        departments = list(db.department_absorption.find({}))

        if module == "fiscal_health":
            fin_summary = []
            for f in finances:
                fin_summary.append(f"FY {f.get('financial_year', 'N/A')}: Equitable KSh {f.get('equitable_share_kshb', 0):.1f}B, Conditional KSh {f.get('conditional_grants_kshb', 0):.1f}B, OSR KSh {f.get('osr_kshb', 0):.1f}B, Expenditure KSh {f.get('expenditure_kshb', 0):.1f}B")

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

        # Safely sum amount_at_risk handling potential string values
        def safe_sum_amount(findings, field):
            total = 0
            for f in findings:
                val = f.get(field, 0)
                if isinstance(val, (int, float)):
                    total += val
                elif isinstance(val, str):
                    # Try to extract number from strings like "KSh 5M"
                    try:
                        import re
                        num = re.search(r'[\d,]+\.?\d*', val.replace(',', ''))
                        if num:
                            total += float(num.group())
                    except (ValueError, AttributeError):
                        pass
            return total

        if module in ("risk_score", "risk_level", "summary"):
            total_alloc = sum(a.get('amount_kshm', 0) for a in allocations)
            mis_count = sum(1 for a in audit_findings if a.get('finding_type') == 'misappropriation')
            total_flagged = safe_sum_amount(audit_findings, 'amount_at_risk')

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
        if not validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        constituency_summary = generate_constituency_summary(constituency_slug, "risk_score")
        governor_summary = generate_governor_summary("risk_score")

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
    "peer_scores": [{{"constituent": "string", "score": number}}],
    "allocation_trend": [{{"fy": "string", "amount": number, "anomaly_flag": boolean}}]
  }}
}}
"""

        cache_parameters = {"constituency_slug": constituency_slug, "module": "risk_score"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "risk_score", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "risk_score",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP risk score: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/mp/<constituency_slug>/risk_level", methods=["GET"])
def mp_risk_level(constituency_slug):
    """AI Risk Level Analyzer Module for MP/Constituency"""
    try:
        if not validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        constituency_summary = generate_constituency_summary(constituency_slug, "risk_level")
        governor_summary = generate_governor_summary("risk_level")

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

        cache_parameters = {"constituency_slug": constituency_slug, "module": "risk_level"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "risk_level", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "risk_level",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP risk level: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/mp/<constituency_slug>/summary", methods=["GET"])
def mp_summary(constituency_slug):
    """AI Summary Generator Module for MP/Constituency"""
    try:
        if not validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        constituency_summary = generate_constituency_summary(constituency_slug, "summary")
        governor_summary = generate_governor_summary("summary")

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

        cache_parameters = {"constituency_slug": constituency_slug, "module": "summary"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "summary", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "summary",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP summary: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/mp/<constituency_slug>/anomalies", methods=["GET"])
def mp_anomalies(constituency_slug):
    """AI Anomalies Detector Module for MP/Constituency.
    Uses GNN-detected anomalies as context for LLM explanations."""
    try:
        if not validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        db = get_db()
        gnn_anomalies = list(db.gnn_anomalies.find({"metadata.constituency_slug": constituency_slug}))
        for a in gnn_anomalies:
            a["_id"] = str(a["_id"])

        high_severity_findings = list(db.audit_findings.find({
            "constituency_slug": constituency_slug,
            "finding_type": "misappropriation"
        }))
        for f in high_severity_findings:
            f["_id"] = str(f["_id"])

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
            gnn_context = "\n\nNo GNN-detected anomalies found for this constituency."

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
            audit_context = "\n\nNo high-severity audit findings (misappropriations) found."

        constituency_summary = generate_constituency_summary(constituency_slug, "anomalies")
        governor_summary = generate_governor_summary("anomalies")

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

        cache_parameters = {"constituency_slug": constituency_slug, "module": "anomalies"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "anomalies", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "anomalies",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP anomalies: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/mp/<constituency_slug>/peer_rank", methods=["GET"])
def mp_peer_rank(constituency_slug):
    """AI Peer Rank Analyzer Module for MP/Constituency"""
    try:
        if not validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        constituency_summary = generate_constituency_summary(constituency_slug, "peer_rank")
        governor_summary = generate_governor_summary("peer_rank")

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

        cache_parameters = {"constituency_slug": constituency_slug, "module": "peer_rank"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "peer_rank", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "peer_rank",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP peer rank: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/mp/<constituency_slug>/citizen_actions", methods=["GET"])
def mp_citizen_actions(constituency_slug):
    """AI Citizen Actions Recommender Module for MP/Constituency"""
    try:
        if not validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        constituency_summary = generate_constituency_summary(constituency_slug, "citizen_actions")
        governor_summary = generate_governor_summary("citizen_actions")

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

        cache_parameters = {"constituency_slug": constituency_slug, "module": "citizen_actions"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "citizen_actions", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "citizen_actions",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP citizen actions: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/mp/<constituency_slug>/data_sources", methods=["GET"])
def mp_data_sources(constituency_slug):
    """AI Data Sources Analyzer Module for MP/Constituency"""
    try:
        if not validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        constituency_summary = generate_constituency_summary(constituency_slug, "data_sources")
        governor_summary = generate_governor_summary("data_sources")

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

        cache_parameters = {"constituency_slug": constituency_slug, "module": "data_sources"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "data_sources", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "data_sources",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in MP data sources: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/mp/<constituency_slug>/cached_at", methods=["GET"])
def mp_cached_at(constituency_slug):
    """AI Cached At Tracker Module for MP/Constituency"""
    try:
        db = get_db()
        cache_collection = db.ai_cache

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
        return jsonify({"error": "Internal server error"}), 500


# Governor AI Modules
@ai_bp.route("/governor/fiscal_health", methods=["GET"])
def governor_fiscal_health():
    """AI Fiscal Health Scorer Module for Governor"""
    try:
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

        cache_parameters = {"module": "fiscal_health"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "fiscal_health", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "fiscal_health",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor fiscal health: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/governor/dept_absorption", methods=["GET"])
def governor_dept_absorption():
    """AI Dept Absorption Analyst Module for Governor"""
    try:
        governor_summary = generate_governor_summary("dept_absorption")

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
    "dept_absorption": [{{"name": "string", "pct": number, "risk_level": "string"}}]
  }}
}}
"""

        cache_parameters = {"module": "dept_absorption"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "dept_absorption", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "dept_absorption",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor dept absorption: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/governor/osr_analysis", methods=["GET"])
def governor_osr_analysis():
    """AI OSR Analyser Module for Governor"""
    try:
        governor_summary = generate_governor_summary("osr_analysis")

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

        cache_parameters = {"module": "osr_analysis"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "osr_analysis", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "osr_analysis",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor osr analysis: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/governor/department_flags", methods=["GET"])
def governor_department_flags():
    """AI Department Flags Module for Governor"""
    try:
        governor_summary = generate_governor_summary("department_flags")

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
    "dept_risk_scores": [{{"name": "string", "risk_score": number, "risk_level": "string"}}],
    "trend_indicators": [{{"name": "string", "trend": "string", "significance": number}}]
  }}
}}
"""

        cache_parameters = {"module": "department_flags"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "department_flags", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "department_flags",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor department flags: {e}")
        return jsonify({"error": "Internal server error"}), 500


@ai_bp.route("/governor/top_risks", methods=["GET"])
def governor_top_risks():
    """AI Top Risks & Citizen Actions Module for Governor"""
    try:
        governor_summary = generate_governor_summary("top_risks")

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

        cache_parameters = {"module": "top_risks"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "top_risks", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "top_risks",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in governor top risks: {e}")
        return jsonify({"error": "Internal server error"}), 500


# County-Level Modules
@ai_bp.route("/county/narrative", methods=["GET"])
def county_narrative():
    """AI County Narrative Generator Module"""
    try:
        governor_summary = generate_governor_summary("county_narrative")

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

        cache_parameters = {"module": "county_narrative"}
        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "county_narrative", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "county_narrative",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in county narrative: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Finding Classifier Module
@ai_bp.route("/findings/classifier", methods=["POST"])
def findings_classifier():
    """AI Finding Classifier Module"""
    try:
        request_data = request.get_json(silent=True) or {}
        finding_id = request_data.get("finding_id")
        finding_text = request_data.get("finding_text")

        # Extract governor summary only (lightweight)
        governor_summary = generate_governor_summary("finding_classifier")

        prompt = f"""
Classify and analyze audit findings from both MP (NG-CDF) and Governor (county executive) sources.
Categorize by severity, provide plain English summaries, and recommend actions.

Focus on the following finding: {finding_text or finding_id or "all audit findings"}

Governor Data Summary:
{governor_summary}

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
"""

        cache_parameters = {
            "module": "finding_classifier",
            "finding_id": finding_id,
            "finding_text": finding_text
        }

        was_cached = False
        if finding_id or finding_text:
            cached = get_cached_ai_response(prompt, GROQ_MODEL, cache_parameters)
            if cached is not None:
                was_cached = True
            ai_response = get_or_compute_ai_response(
                prompt=prompt,
                model=GROQ_MODEL,
                parameters=cache_parameters,
                compute_fn=lambda p, m: call_llm_api(p, m)
            )
        else:
            # No caching for generic "all findings" request
            ai_response = call_llm_api(prompt)

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "finding_classifier", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "finding_classifier",
            "cached": was_cached,
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in findings classifier: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Cross-Leader Comparator Module
@ai_bp.route("/compare", methods=["POST"])
def compare_leaders():
    """AI Cross-Leader Comparator Module"""
    try:
        request_data = request.get_json(silent=True) or {}
        leader1_type = request_data.get("leader1_type", "governor")
        leader1_id = request_data.get("leader1_id")
        leader2_type = request_data.get("leader2_type", "constituency")
        leader2_id = request_data.get("leader2_id")

        # Extract data using summaries only (not raw JSON)
        data1 = validate_and_extract_data(leader1_id if leader1_type == "constituency" else None)
        if "error" in data1:
            return jsonify({"error": data1["error"]}), 404

        data2 = {}
        if leader2_type == "constituency" and leader2_id:
            data2 = validate_and_extract_data(leader2_id)
            if "error" in data2:
                return jsonify({"error": data2["error"]}), 404
        elif leader2_type == "governor":
            # Governor data is always in data1 when leader1 is governor or we need it from data1
            data2 = data1

        # Generate concise summaries instead of dumping raw JSON
        def get_leader_summary(data, leader_type, leader_id):
            if leader_type == "constituency":
                return generate_constituency_summary(leader_id, "compare")
            else:
                return generate_governor_summary("compare")

        leader1_summary = get_leader_summary(data1, leader1_type, leader1_id)
        leader2_summary = get_leader_summary(data2, leader2_type, leader2_id)

        prompt = f"""
Compare MP (NG-CDF legislative) and Governor (county executive) performance across multiple dimensions.
Analyze allocation effectiveness, audit outcomes, correct appropriations, budget absorption, and fiscal health.

Leader 1 ({leader1_type}): {leader1_summary}
Leader 2 ({leader2_type}): {leader2_summary}

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
"""

        cache_parameters = {
            "module": "compare",
            "leader1_type": leader1_type,
            "leader1_id": leader1_id,
            "leader2_type": leader2_type,
            "leader2_id": leader2_id
        }

        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_api(p, m)
        )

        if ai_response.get("_error"):
            return jsonify({"success": False, "module": "compare", "error": ai_response["narrative_fields"]["details"]}), 502

        return jsonify({
            "success": True,
            "module": "compare",
            "data": ai_response
        })

    except Exception as e:
        logging.error(f"Error in compare leaders: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Health check endpoint for AI engine
@ai_bp.route("/health", methods=["GET"])
def ai_health():
    """Health check for AI engine"""
    try:
        db = get_db()
        collection = db.ai_cache
        collection.find_one({})

        return jsonify({
            "status": "healthy",
            "service": "AI Engine",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logging.error(f"AI health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "service": "AI Engine"
        }), 503