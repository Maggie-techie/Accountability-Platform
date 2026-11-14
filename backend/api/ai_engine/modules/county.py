"""
County-level AI Endpoints (cross-leader, narrative, classifier).
"""
from flask import Blueprint, request, jsonify
from ..core.cache import get_or_compute_ai_response
from ..core.llm import call_llm_json
from ..core.schemas import get_schema
from ..core.validation import validate_output, sanitize_for_client
from ..core.prompts import (
    generate_county_narrative_data,
    generate_comparison_data,
    generate_governor_summary
)
from ..data.access import data_access

# Create blueprint
county_bp = Blueprint("county", __name__, url_prefix="")


@county_bp.route("/county/narrative", methods=["GET"])
def county_narrative():
    """AI County Narrative Generator Module"""
    try:
        data = generate_county_narrative_data()

        from ..core.factory import COUNTY_PROMPTS

        prompt = COUNTY_PROMPTS["county_narrative"].format(
            governor_summary=data["governor_summary"],
            constituency_summary=data["constituency_summary"]
        )

        output_schema = get_schema("county_narrative", "county")
        cache_parameters = {"module": "county_narrative"}

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
            "module": "county_narrative",
            "data": validated.model_dump()
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in county narrative: {e}")
        return jsonify({"error": "Internal server error"}), 500


@county_bp.route("/findings/classifier", methods=["POST"])
def findings_classifier():
    """AI Finding Classifier Module"""
    try:
        request_data = request.get_json(silent=True) or {}
        finding_id = request_data.get("finding_id")
        finding_text = request_data.get("finding_text")

        # Extract governor summary only (lightweight)
        governor_summary = generate_governor_summary("finding_classifier")

        finding_focus = finding_text or finding_id or "all audit findings"

        from ..core.factory import COUNTY_PROMPTS

        prompt = COUNTY_PROMPTS["finding_classifier"].format(
            finding_focus=finding_focus,
            governor_summary=governor_summary
        )

        cache_parameters = {
            "module": "finding_classifier",
            "finding_id": finding_id,
            "finding_text": finding_text
        }

        was_cached = False
        if finding_id or finding_text:
            # Check cache first - if hit, use it directly to accurately track cache status
            from ..core.cache import DISABLE_AI_CACHE, get_cached_ai_response

            if DISABLE_AI_CACHE:
                # Bypass cache entirely
                ai_response = call_llm_json(prompt)
            else:
                cached = get_cached_ai_response(prompt, None, cache_parameters)
                if cached is not None:
                    was_cached = True
                    ai_response = cached
                else:
                    # Cache miss - compute and cache
                    ai_response = get_or_compute_ai_response(
                        prompt=prompt,
                        model=None,
                        parameters=cache_parameters,
                        compute_fn=lambda p, m: call_llm_json(p, m)
                    )
        else:
            # No caching for generic "all findings" request
            ai_response = call_llm_json(prompt)

        output_schema = get_schema("finding_classifier", "county")
        validated, error = validate_output(ai_response, output_schema, max_retries=1)

        if error:
            return jsonify(sanitize_for_client(error)), 502

        return jsonify({
            "success": True,
            "module": "finding_classifier",
            "cached": was_cached,
            "data": validated.model_dump()
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in findings classifier: {e}")
        return jsonify({"error": "Internal server error"}), 500


@county_bp.route("/compare", methods=["POST"])
def compare_leaders():
    """AI Cross-Leader Comparator Module"""
    try:
        request_data = request.get_json(silent=True) or {}
        leader1_type = request_data.get("leader1_type", "governor")
        leader1_id = request_data.get("leader1_id")
        leader2_type = request_data.get("leader2_type", "constituency")
        leader2_id = request_data.get("leader2_id")

        # Validate constituency exists if needed
        if leader1_type == "constituency" and leader1_id:
            if not data_access.validate_constituency_exists(leader1_id):
                return jsonify({"error": f"Constituency not found: {leader1_id}"}), 404
        if leader2_type == "constituency" and leader2_id:
            if not data_access.validate_constituency_exists(leader2_id):
                return jsonify({"error": f"Constituency not found: {leader2_id}"}), 404

        # Compute chart data from database (not LLM)
        from ..core.prompts import generate_comparison_data
        comparison_data = generate_comparison_data(
            leader1_type, leader1_id, leader2_type, leader2_id
        )

        from ..core.factory import COUNTY_PROMPTS

        prompt = COUNTY_PROMPTS["compare"].format(
            leader1_type=comparison_data["leader1_type"],
            leader1_summary=comparison_data["leader1_summary"],
            leader2_type=comparison_data["leader2_type"],
            leader2_summary=comparison_data["leader2_summary"]
        )

        cache_parameters = {
            "module": "compare",
            "leader1_type": leader1_type,
            "leader1_id": leader1_id,
            "leader2_type": leader2_type,
            "leader2_id": leader2_id
        }

        ai_response = get_or_compute_ai_response(
            prompt=prompt,
            model=None,
            parameters=cache_parameters,
            compute_fn=lambda p, m: call_llm_json(p, m)
        )

        output_schema = get_schema("compare", "county")
        validated, error = validate_output(ai_response, output_schema, max_retries=1)

        if error:
            return jsonify(sanitize_for_client(error)), 502

        # Merge server-computed chart data with LLM narrative
        result = validated.model_dump()
        result["chart_data"] = {"radar_data": comparison_data["radar_data"]}

        return jsonify({
            "success": True,
            "module": "compare",
            "data": result
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in compare leaders: {e}")
        return jsonify({"error": "Internal server error"}), 500