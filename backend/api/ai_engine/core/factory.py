"""
Endpoint Factory - eliminates code duplication across AI endpoints.
All MP, Governor, and County endpoints follow the same pattern:
validate → fetch data → build prompt → call LLM → validate output → return
"""
import logging
from typing import Callable, Optional
from flask import Blueprint, request, jsonify
from functools import wraps

from ..core.llm import call_llm_json, LLMError
from ..core.cache import get_or_compute_ai_response, DISABLE_AI_CACHE
from ..core.schemas import get_schema, ErrorResponse
from ..core.validation import validate_output, sanitize_for_client
from ..data.access import data_access

logger = logging.getLogger(__name__)


def make_mp_endpoint(
    module: str,
    prompt_template: str,
    summary_module: str = None,
    governor_summary_module: str = None,
    extra_context_fn: Callable = None
):
    """
    Factory for MP/Constituency endpoints.

    Args:
        module: Module name (e.g., "risk_score", "anomalies")
        prompt_template: Prompt template with {constituency_summary} and {governor_summary} placeholders
        summary_module: Module name for constituency summary (defaults to module)
        governor_summary_module: Module name for governor summary (defaults to module)
        extra_context_fn: Optional function(constituency_slug) -> extra_context_dict
    """
    summary_module = summary_module or module
    governor_summary_module = governor_summary_module or module
    output_schema = get_schema(module, "mp")

    def endpoint(constituency_slug: str):
        try:
            # Validate constituency exists
            if not data_access.validate_constituency_exists(constituency_slug):
                return jsonify({"error": f"Constituency not found: {constituency_slug}"}), 404

            # Generate data summaries
            from .prompts import (
                generate_constituency_summary,
                generate_governor_summary
            )

            constituency_summary = generate_constituency_summary(constituency_slug, summary_module)
            governor_summary = generate_governor_summary(governor_summary_module)

            # Build extra context if provided
            extra_context = {}
            if extra_context_fn:
                extra_context = extra_context_fn(constituency_slug)

            # Build prompt
            prompt = prompt_template.format(
                constituency_slug=constituency_slug,
                constituency_summary=constituency_summary,
                governor_summary=governor_summary,
                **extra_context
            )

            # Cache parameters
            cache_parameters = {"constituency_slug": constituency_slug, "module": module}

            # Call LLM with caching
            def compute_fn(p, m):
                return call_llm_json(p, m)

            ai_response = get_or_compute_ai_response(
                prompt=prompt,
                model=None,  # Uses default from env
                parameters=cache_parameters,
                compute_fn=compute_fn
            )

            # Validate output against schema
            validated, error = validate_output(ai_response, output_schema, max_retries=1)

            if error:
                return jsonify(sanitize_for_client(error)), 502

            return jsonify({
                "success": True,
                "module": module,
                "data": validated.model_dump()
            })

        except Exception as e:
            logger.error(f"Error in MP {module}: {e}")
            return jsonify({"error": "Internal server error"}), 500

    # Set endpoint name for debugging
    endpoint.__name__ = f"mp_{module}"
    return endpoint


def make_governor_endpoint(
    module: str,
    prompt_template: str,
    summary_module: str = None
):
    """
    Factory for Governor/County endpoints.

    Args:
        module: Module name (e.g., "fiscal_health", "dept_absorption")
        prompt_template: Prompt template with {governor_summary} placeholder
        summary_module: Module name for governor summary (defaults to module)
    """
    summary_module = summary_module or module
    output_schema = get_schema(module, "governor")

    def endpoint():
        try:
            # Generate governor summary
            from .prompts import generate_governor_summary

            governor_summary = generate_governor_summary(summary_module)

            # Build prompt
            prompt = prompt_template.format(
                governor_summary=governor_summary
            )

            # Cache parameters
            cache_parameters = {"module": module}

            # Call LLM with caching
            def compute_fn(p, m):
                return call_llm_json(p, m)

            ai_response = get_or_compute_ai_response(
                prompt=prompt,
                model=None,
                parameters=cache_parameters,
                compute_fn=compute_fn
            )

            # Validate output
            validated, error = validate_output(ai_response, output_schema, max_retries=1)

            if error:
                return jsonify(sanitize_for_client(error)), 502

            return jsonify({
                "success": True,
                "module": module,
                "data": validated.model_dump()
            })

        except Exception as e:
            logger.error(f"Error in Governor {module}: {e}")
            return jsonify({"error": "Internal server error"}), 500

    endpoint.__name__ = f"governor_{module}"
    return endpoint


def make_county_endpoint(
    module: str,
    prompt_template: str,
    extra_data_fn: Callable = None
):
    """
    Factory for County-level endpoints (county_narrative, finding_classifier, compare).

    Args:
        module: Module name
        prompt_template: Prompt template
        extra_data_fn: Optional function() -> extra_context_dict
    """
    output_schema = get_schema(module, "county")

    def endpoint():
        try:
            # Get extra data if provided
            extra_context = {}
            if extra_data_fn:
                extra_context = extra_data_fn()

            # Build prompt
            prompt = prompt_template.format(**extra_context)

            # Cache parameters
            cache_parameters = {"module": module}

            # Call LLM with caching
            def compute_fn(p, m):
                return call_llm_json(p, m)

            ai_response = get_or_compute_ai_response(
                prompt=prompt,
                model=None,
                parameters=cache_parameters,
                compute_fn=compute_fn
            )

            # Validate output
            validated, error = validate_output(ai_response, output_schema, max_retries=1)

            if error:
                return jsonify(sanitize_for_client(error)), 502

            return jsonify({
                "success": True,
                "module": module,
                "data": validated.model_dump()
            })

        except Exception as e:
            logger.error(f"Error in County {module}: {e}")
            return jsonify({"error": "Internal server error"}), 500

    endpoint.__name__ = f"county_{module}"
    return endpoint


# ============================================================
# Prompt Templates (extracted from original endpoints)
# ============================================================

MP_PROMPTS = {
    "risk_score": """Analyze the financial risk for the constituency with slug '{constituency_slug}'.
Based on the following data, provide a risk assessment:

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "risk_score": <integer 0-100>,
    "risk_level": "<High|Medium|Low>",
    "summary": "<3-4 sentences: plain English explanation of the risk score, what drives it, and what it means for citizens. No jargon.>",
    "key_drivers": ["<driver 1>", "<driver 2>", "<driver 3>"],
    "what_this_means": "<2-3 sentences: practical implications for residents. What could go wrong? What's at stake?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "risk_level": """Analyze the risk level and anomalies for the constituency with slug '{constituency_slug}'.
Based on the following data, provide insights:

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "risk_level": "<High|Medium|Low>",
    "summary": "<3-4 sentences: plain English explanation of the overall risk level. What are the main concerns? What's going well?>",
    "anomalies_found": <integer count>,
    "top_anomalies": [
      {{
        "title": "<short title>",
        "description": "<2-3 sentences: what was found, why it matters, in plain English>",
        "severity": "<High|Medium|Low>",
        "amount_at_risk": "<formatted string e.g. 'KES 2.3M' or 'Not quantified'>",
        "category": "<procurement|payroll|budget|project|other>"
      }}
    ],
    "what_this_means": "<2-3 sentences: practical implications for residents>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "summary": """Generate a comprehensive summary for the constituency with slug '{constituency_slug}'.
Based on the following data, provide insights:

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "constituency_name": "<name>",
    "mp_name": "<name>",
    "financial_health": "<Strong|Moderate|Weak>",
    "summary": "<4-5 sentences: holistic overview of the constituency's financial situation. Cover NG-CDF allocations, expenditure patterns, audit findings, and project delivery. Plain English, no jargon.>",
    "key_achievements": ["<achievement 1>", "<achievement 2>", "<achievement 3>"],
    "key_concerns": ["<concern 1>", "<concern 2>", "<concern 3>"],
    "what_this_means": "<3-4 sentences: what this means for a resident. How does it affect services, development, accountability?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>", "<specific action 4>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "anomalies": """Detect anomalies in the financial and audit data for the constituency with slug '{constituency_slug}'.
Based on the following data, identify any anomalies:

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "anomalies_found": <integer count>,
    "summary": "<3-4 sentences: overview of anomalies detected. What types? How serious? Any patterns?>",
    "anomalies": [
      {{
        "title": "<short descriptive title>",
        "description": "<3-4 sentences: what happened, why it's anomalous, what the implications are. Plain English.>",
        "severity": "<High|Medium|Low>",
        "amount_at_risk": "<formatted string e.g. 'KES 2.3M' or 'Not quantified'>",
        "category": "<procurement|payroll|budget|project|other>",
        "year": "<financial year>",
        "source": "<audit report|financial statement|other>"
      }}
    ],
    "what_this_means": "<2-3 sentences: practical implications for residents. What's at stake?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "peer_rank": """Analyze the peer ranking for the constituency with slug '{constituency_slug}' based on performance metrics.

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "rank": <integer 1-N>,
    "total_constituencies": <integer>,
    "percentile": <integer 0-100>,
    "summary": "<3-4 sentences: how this constituency compares to peers. What does the rank mean in practical terms? Is it improving or declining?>",
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
    "what_this_means": "<2-3 sentences: what this ranking means for residents. Should they be concerned or reassured?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "citizen_actions": """Generate recommended citizen actions for the constituency with slug '{constituency_slug}' based on audit findings and financial data.

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<3-4 sentences: why citizen engagement matters for this constituency right now. What's at stake?>",
    "priority_actions": [
      {{
        "title": "<short action title>",
        "description": "<2-3 sentences: what to do, how to do it, why it matters. Specific and actionable.>",
        "difficulty": "<Easy|Medium|Hard>",
        "impact": "<High|Medium|Low>",
        "timeframe": "<Immediate|Short-term|Long-term>",
        "channels": ["<channel 1 e.g. 'Attend ward baraza'>", "<channel 2 e.g. 'Write to MP'>", "<channel 3 e.g. 'Social media'>"]
      }}
    ],
    "what_this_means": "<2-3 sentences: what collective action could achieve>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>", "<specific action 4>", "<specific action 5>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "data_sources": """Evaluate the data sources and quality for the constituency with slug '{constituency_slug}'.

Constituency Summary:
{constituency_summary}

Governor Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<3-4 sentences: overview of what data is available, what's missing, and how reliable it is. Plain English.>",
    "sources": [
      {{
        "name": "<source name e.g. 'OAG Audit Report 2022/23'>",
        "type": "<audit|financial|project|other>",
        "coverage": "<Full|Partial|Limited>",
        "reliability": "<High|Medium|Low>",
        "notes": "<1-2 sentences: any caveats, gaps, or limitations>"
      }}
    ],
    "gaps": ["<gap 1>", "<gap 2>", "<gap 3>"],
    "what_this_means": "<2-3 sentences: how data gaps affect accountability. What can't we verify?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend."""
}

GOVERNOR_PROMPTS = {
    "fiscal_health": """Analyze the fiscal health of the county government based on financial data, audit findings, and department performance.

Governor Data Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "overall_rating": "<Strong|Moderate|Weak>",
    "summary": "<4-5 sentences: holistic assessment of county fiscal health. Cover revenue, expenditure, debt, audit outcomes, and service delivery. Plain English.>",
    "revenue_analysis": "<3-4 sentences: OSR trends, national transfers, revenue gaps. What's driving changes?>",
    "expenditure_analysis": "<3-4 sentences: recurrent vs development, absorption rates, priority areas. Any red flags?>",
    "debt_position": "<2-3 sentences: debt levels, sustainability, risk of distress>",
    "audit_outcomes": "<3-4 sentences: key audit findings, adverse opinions, improvement/decline trend>",
    "key_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
    "what_this_means": "<3-4 sentences: what this means for county residents. Services, development, accountability?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>", "<specific action 4>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "dept_absorption": """Analyze department budget absorption rates and identify risks.

Governor Data Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<3-4 sentences: overall absorption performance. How many departments? What's the average? Any outliers?>",
    "departments": [
      {{
        "name": "<department name>",
        "absorption_rate": <float 0-100>,
        "rating": "<Excellent|Good|Fair|Poor>",
        "narrative": "<2-3 sentences: why this rate? What does it mean for service delivery? Any specific projects affected?>"
      }}
    ],
    "what_this_means": "<3-4 sentences: implications of low absorption. Wasted resources? Delayed projects? Service gaps?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "osr_analysis": """Analyze Own Source Revenue (OSR) performance and trends.

Governor Data Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<3-4 sentences: OSR trend, target vs actual, key revenue streams. Is the county becoming more or less self-reliant?>",
    "trend": "<Improving|Stable|Declining>",
    "revenue_streams": [
      {{
        "name": "<stream name>",
        "target": <number>,
        "actual": <number>,
        "performance": "<On Target|Below Target|Above Target>",
        "narrative": "<2-3 sentences: what drives this stream? Why over/under? Any collection challenges?>"
      }}
    ],
    "what_this_means": "<3-4 sentences: implications for county autonomy, service funding, development plans>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "department_flags": """Identify department-specific risk flags based on budget performance and audit findings.

Governor Data Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<3-4 sentences: how many departments flagged, what types of issues, overall concern level>",
    "flags": [
      {{
        "department": "<name>",
        "flag_type": "<absorption|audit|procurement|payroll|project|other>",
        "severity": "<High|Medium|Low>",
        "description": "<3-4 sentences: what was found, evidence, implications. Plain English.>",
        "amount_at_risk": "<formatted string e.g. 'KES 2.3M' or 'Not quantified'>",
        "recommended_action": "<1-2 sentences: what should be done?>"
      }}
    ],
    "what_this_means": "<3-4 sentences: systemic implications. Is this isolated or pattern? Leadership/accountability issues?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "top_risks": """Identify the top risks facing the county government and recommend citizen actions.

Governor Data Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<3-4 sentences: top 3-5 risks overall, common themes, urgency>",
    "risks": [
      {{
        "title": "<short risk title>",
        "description": "<3-4 sentences: what is the risk, evidence, likelihood, potential impact. Plain English.>",
        "category": "<fiscal|governance|service_delivery|corruption|compliance|other>",
        "severity": "<Critical|High|Medium|Low>",
        "likelihood": "<Very Likely|Likely|Possible|Unlikely>",
        "affected_areas": ["<area 1>", "<area 2>"],
        "mitigation": "<2-3 sentences: what county should do, what citizens can watch for>"
      }}
    ],
    "what_this_means": "<3-4 sentences: cumulative impact if risks materialize. Effect on services, development, trust?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>", "<specific action 4>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend."""
}

COUNTY_PROMPTS = {
    "county_narrative": """Generate a comprehensive county narrative covering both MP (NG-CDF) and Governor (county executive) perspectives.
Include analysis of cross-leader relationships, shared risks, and collaborative opportunities.

Governor Data Summary:
{governor_summary}

Constituency Data Summary:
{constituency_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "county_name": "<county name>",
    "governor_name": "<name>",
    "mps": ["<constituency>: <MP name>", "..."],
    "executive_summary": "<5-6 sentences: the big picture. How are the two arms of government performing? Any friction or synergy? What's the headline story?>",
    "ngcdf_overview": "<3-4 sentences: aggregate NG-CDF performance across constituencies. Allocations, absorption, audit outcomes, project delivery.>",
    "executive_overview": "<3-4 sentences: county executive performance. Revenue, expenditure, service delivery, audit outcomes.>",
    "cross_leader_analysis": "<4-5 sentences: where do MP and Governor priorities align or clash? Shared resources? Duplication? Gaps? Political dynamics?>",
    "shared_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
    "collaborative_opportunities": ["<opportunity 1>", "<opportunity 2>", "<opportunity 3>"],
    "what_this_means": "<4-5 sentences: what this means for a county resident. How does the relationship between leaders affect their daily life?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>", "<specific action 4>", "<specific action 5>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "finding_classifier": """Classify and analyze audit findings from both MP (NG-CDF) and Governor (county executive) sources.
Categorize by severity, provide plain English summaries, and recommend actions.

Focus on the following finding: {finding_focus}

Governor Data Summary:
{governor_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<3-4 sentences: overall finding landscape. How many findings? What's the severity distribution? Any trends?>",
    "findings": [
      {{
        "title": "<short descriptive title>",
        "description": "<3-4 sentences: what was found, why it matters, in plain English. No audit jargon.>",
        "severity": "<High|Medium|Low>",
        "category": "<misappropriation|procurement|payroll|budget|project|compliance|other>",
        "entity": "<MP|Governor|Department|Constituency>",
        "amount_at_risk": "<formatted string e.g. 'KES 2.3M' or 'Not quantified'>",
        "year": "<financial year>",
        "recommendation": "<2-3 sentences: specific, actionable recommendation for resolution>",
        "citizen_action": "<1-2 sentences: what can a citizen do about this?>"
      }}
    ],
    "what_this_means": "<3-4 sentences: cumulative impact of findings. Systemic issues? Leadership failure? Improving?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>", "<specific action 4>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: severity must be High, Medium, or Low. Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend.""",

    "compare": """Compare MP (NG-CDF legislative) and Governor (county executive) performance across multiple dimensions.
Analyze allocation effectiveness, audit outcomes, correct appropriations, budget absorption, and fiscal health.

Leader 1 ({leader1_type}): {leader1_summary}
Leader 2 ({leader2_type}): {leader2_summary}

Return ONLY a JSON object with exactly this structure (all keys required):
{{
  "narrative_fields": {{
    "summary": "<4-5 sentences: headline comparison. Who performs better on what? Key differences in mandate, resources, outcomes. Plain English.>",
    "mp_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "mp_weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
    "governor_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "governor_weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
    "shared_challenges": ["<challenge 1>", "<challenge 2>", "<challenge 3>"],
    "what_this_means": "<4-5 sentences: what this comparison means for citizens. How should they evaluate their leaders differently? What questions should they ask?>",
    "citizen_actions": ["<specific action 1>", "<specific action 2>", "<specific action 3>", "<specific action 4>", "<specific action 5>"],
    "data_quality_note": "<1 sentence on data completeness/reliability>"
  }},
  "chart_data": {{"sample_array": [], "sample_labels": []}}
}}
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend. radar_data is computed server-side and will be merged with your response."""
}