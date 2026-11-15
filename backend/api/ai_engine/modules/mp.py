"""
MP/Constituency AI Endpoints.
Generated using factory pattern to eliminate code duplication.
"""
from flask import Blueprint, jsonify
from ..core.factory import make_mp_endpoint, MP_PROMPTS
from ..core.prompts import (
    generate_constituency_summary,
    generate_governor_summary,
    generate_constituency_anomalies_context
)
from ..data.access import data_access

# Create blueprint
mp_bp = Blueprint("mp", __name__, url_prefix="/mp")


# ============================================================
# Standard MP Endpoints (using factory)
# ============================================================

# Risk Score
mp_risk_score = make_mp_endpoint(
    module="risk_score",
    prompt_template=MP_PROMPTS["risk_score"],
    summary_module="risk_score",
    governor_summary_module="risk_score"
)
mp_bp.route("/<constituency_slug>/risk_score", methods=["GET"])(mp_risk_score)


# Risk Level
mp_risk_level = make_mp_endpoint(
    module="risk_level",
    prompt_template=MP_PROMPTS["risk_level"],
    summary_module="risk_level",
    governor_summary_module="risk_level"
)
mp_bp.route("/<constituency_slug>/risk_level", methods=["GET"])(mp_risk_level)


# Summary
mp_summary = make_mp_endpoint(
    module="summary",
    prompt_template=MP_PROMPTS["summary"],
    summary_module="summary",
    governor_summary_module="summary"
)
mp_bp.route("/<constituency_slug>/summary", methods=["GET"])(mp_summary)


# Peer Rank
mp_peer_rank = make_mp_endpoint(
    module="peer_rank",
    prompt_template=MP_PROMPTS["peer_rank"],
    summary_module="peer_rank",
    governor_summary_module="peer_rank"
)
mp_bp.route("/<constituency_slug>/peer_rank", methods=["GET"])(mp_peer_rank)


# Citizen Actions
mp_citizen_actions = make_mp_endpoint(
    module="citizen_actions",
    prompt_template=MP_PROMPTS["citizen_actions"],
    summary_module="citizen_actions",
    governor_summary_module="citizen_actions"
)
mp_bp.route("/<constituency_slug>/citizen_actions", methods=["GET"])(mp_citizen_actions)


# Data Sources
mp_data_sources = make_mp_endpoint(
    module="data_sources",
    prompt_template=MP_PROMPTS["data_sources"],
    summary_module="data_sources",
    governor_summary_module="data_sources"
)
mp_bp.route("/<constituency_slug>/data_sources", methods=["GET"])(mp_data_sources)


# ============================================================
# Specialized MP Endpoints (custom logic)
# ============================================================

@mp_bp.route("/<constituency_slug>/anomalies", methods=["GET"])
def mp_anomalies(constituency_slug):
    """AI Anomalies Detector Module for MP/Constituency.
    Uses GNN-detected anomalies as context for LLM explanations."""
    try:
        if not data_access.validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        # Get specialized context
        extra_context = generate_constituency_anomalies_context(constituency_slug)

        # Generate summaries
        constituency_summary = generate_constituency_summary(constituency_slug, "anomalies")
        governor_summary = generate_governor_summary("anomalies")

        # Build prompt with GNN context - matching AnomaliesOutput schema
        prompt = f"""You are a financial analyst explaining anomalies and audit findings for the constituency '{constituency_slug}'.

The Graph Neural Network (GNN) model analyzes constituency-year and governor-year nodes in a financial graph, detecting anomalies via:
1. Graph reconstruction error (connectivity patterns)
2. Embedding space distance to k-nearest neighbors
3. Isolation Forest on node embeddings

{extra_context['gnn_context']}
{extra_context['audit_context']}

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "anomalies_found": 0,
    "summary": "Plain-language summary of anomalies and audit findings for citizens (min 50 chars)",
    "anomalies": [
      {{
        "title": "Anomaly title",
        "description": "Detailed description of the anomaly (min 30 chars)",
        "severity": "High|Medium|Low",
        "amount_at_risk": "Amount at risk as string",
        "category": "procurement|payroll|budget|project|other",
        "year": "Fiscal year",
        "source": "Source of detection"
      }}
    ],
    "what_this_means": "What these anomalies mean for citizens and public funds (min 30 chars)",
    "citizen_actions": ["Action 1", "Action 2"],
    "data_quality_note": "Note about data quality and limitations"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. The anomalies array can be empty if none found. Charts/tables are rendered separately by the frontend."""

        from ..core.cache import get_or_compute_ai_response
        from ..core.llm import call_llm_json
        from ..core.schemas import get_schema
        from ..core.validation import validate_output, sanitize_for_client

        output_schema = get_schema("anomalies", "mp")
        cache_parameters = {"constituency_slug": constituency_slug, "module": "anomalies"}

        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=None,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_json(p, m)
        )

        validated, error = validate_output(ai_response, output_schema, max_retries=1)

        if error:
            return jsonify(sanitize_for_client(error)), 502

        return jsonify({
            "success": True,
            "module": "anomalies",
            "data": validated.model_dump()
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in MP anomalies: {e}")
        return jsonify({"error": "Internal server error"}), 500


@mp_bp.route("/<constituency_slug>/cached_at", methods=["GET"])
def mp_cached_at(constituency_slug):
    """AI Cached At Tracker Module for MP/Constituency"""
    try:
        if not data_access.validate_constituency_exists(constituency_slug):
            return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

        from ..core.cache import get_cache_stats

        stats = get_cache_stats(constituency_slug)

        return jsonify({
            "success": True,
            "module": "cached_at",
            "cached": stats["total_entries"] > 0,
            "data": stats
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in MP cached at: {e}")
        return jsonify({"error": "Internal server error"}), 500