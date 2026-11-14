#!/usr/bin/env python3
"""
Cache warming utility for the Accountability Platform AI Engine.
Pre-populates the AI cache with commonly requested analyses to improve performance.
"""

import os
import sys
import json

# Add backend directory to path for imports
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)

# Create Flask app and push application context for database access
from app import create_app
app = create_app()
app.app_context().push()

from api.ai_engine import (
    get_db,
    generate_cache_key,
    cache_ai_response,
    get_cached_ai_response,
    validate_and_extract_data,
    call_llm_api,
    GROQ_MODEL
)
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def warm_constituency_cache(constituency_slugs=None):
    """Warm cache for all constituency-related AI modules."""
    if constituency_slugs is None:
        # Get all constituencies from database
        db = get_db()
        constituencies = db.constituencies.find({}, {"slug": 1})
        constituency_slugs = [c["slug"] for c in constituencies]

    modules = [
        "risk_score",
        "risk_level",
        "summary",
        "anomalies",
        "peer_rank",
        "citizen_actions",
        "data_sources"
    ]

    logger.info(f"Warming cache for {len(constituency_slugs)} constituencies and {len(modules)} modules")

    for slug in constituency_slugs:
        logger.info(f"Warming cache for constituency: {slug}")
        for module in modules:
            try:
                # Check if already cached
                cache_parameters = {"constituency_slug": slug, "module": module}
                cached = get_cached_ai_response(
                    prompt=f"Analyze {module} for constituency {slug}",
                    model=GROQ_MODEL,
                    parameters=cache_parameters
                )

                if cached:
                    logger.debug(f"Cache already exists for {slug}/{module}")
                    continue

                # Extract data
                data = validate_and_extract_data(slug)
                if "error" in data:
                    logger.warning(f"Skipping {slug}/{module}: {data['error']}")
                    continue

                # Generate narrative-focused prompt based on module (matching ai_engine.py endpoints)
                prompts = {
                    "risk_score": f"""Analyze the financial risk for the constituency with slug '{slug}'. Based on the following data, provide a risk assessment.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

                    "risk_level": f"""Analyze the risk level and anomalies for the constituency with slug '{slug}'. Based on the following data, provide insights.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

                    "summary": f"""Generate a comprehensive summary for the constituency with slug '{slug}'. Based on the following data, provide insights.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

                    "anomalies": f"""Detect anomalies in the financial and audit data for the constituency with slug '{slug}'. Based on the following data, identify any anomalies.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

                    "peer_rank": f"""Analyze the peer ranking for the constituency with slug '{slug}' based on performance metrics.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

                    "citizen_actions": f"""Generate recommended citizen actions for the constituency with slug '{slug}' based on audit findings and financial data.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

                    "data_sources": f"""Evaluate the data sources and quality for the constituency with slug '{slug}'.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

                prompt = prompts.get(module, f"Analyze {module} for constituency {slug}")

                # Call LLM API
                ai_response = call_llm_api(prompt)

                # Cache the response
                cache_ai_response(
                    prompt=prompt,
                    model=GROQ_MODEL,
                    parameters=cache_parameters,
                    response=ai_response,
                    ttl_hours=24
                )

                logger.info(f"Warmed cache for {slug}/{module}")

            except Exception as e:
                logger.error(f"Failed to warm cache for {slug}/{module}: {e}")


def warm_governor_cache():
    """Warm cache for governor-related AI modules."""
    logger.info("Warming cache for governor AI modules")

    modules = [
        "fiscal_health",
        "dept_absorption",
        "osr_analysis",
        "department_flags",
        "top_risks"
    ]

    try:
        # Check if we have governor data
        db = get_db()
        governor_profile = db.county_leaders.find_one({})
        if not governor_profile:
            logger.warning("No governor data found, skipping governor cache warming")
            return

        for module in modules:
            try:
                # Check if already cached
                cache_parameters = {"module": module}
                cached = get_cached_ai_response(
                    prompt=f"Analyze {module} for governor",
                    model=GROQ_MODEL,
                    parameters=cache_parameters
                )

                if cached:
                    logger.debug(f"Cache already exists for governor/{module}")
                    continue

                # Extract governor data
                data = validate_and_extract_data()  # No constituency slug for governor-wide analysis
                if "error" in data:
                    logger.warning(f"Skipping governor/{module}: {data['error']}")
                    continue

                # Generate narrative-focused prompt based on module (matching ai_engine.py endpoints)
                gov_data_json = json.dumps(data.get('governor', {}), default=str)

                prompts = {
                    "fiscal_health": f"""Analyze the fiscal health of the county government based on financial data, audit findings, and department performance.

Governor Data: {gov_data_json}

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

                    "dept_absorption": f"""Analyze department budget absorption rates and identify risks.

Governor Data: {gov_data_json}

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

                    "osr_analysis": f"""Analyze Own Source Revenue (OSR) performance and trends.

Governor Data: {gov_data_json}

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

                    "department_flags": f"""Identify department-specific risk flags based on budget performance and audit findings.

Governor Data: {gov_data_json}

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

                    "top_risks": f"""Identify the top risks facing the county government and recommend citizen actions.

Governor Data: {gov_data_json}

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

                prompt = prompts.get(module, f"Analyze {module} for governor")

                # Call LLM API
                ai_response = call_llm_api(prompt)

                # Cache the response
                cache_ai_response(
                    prompt=prompt,
                    model=GROQ_MODEL,
                    parameters=cache_parameters,
                    response=ai_response,
                    ttl_hours=24
                )

                logger.info(f"Warmed cache for governor/{module}")

            except Exception as e:
                logger.error(f"Failed to warm cache for governor/{module}: {e}")

    except Exception as e:
        logger.error(f"Failed to warm governor cache: {e}")


def warm_county_narrative_cache():
    """Warm cache for county-level narrative analysis."""
    logger.info("Warming cache for county narrative analysis")

    try:
        # Check if already cached
        cache_parameters = {"module": "county_narrative"}
        cached = get_cached_ai_response(
            prompt="Generate county narrative covering both MP and Governor perspectives",
            model=GROQ_MODEL,
            parameters=cache_parameters
        )

        if cached:
            logger.debug("Cache already exists for county narrative")
            return

        # Extract all data
        data = validate_and_extract_data()
        if "error" in data:
            logger.warning(f"Skipping county narrative: {data['error']}")
            return

        # Prepare prompt matching ai_engine.py endpoint
        prompt = f"""Generate a comprehensive county narrative covering both MP (NG-CDF) and Governor (county executive) perspectives.
Include analysis of cross-leader relationships, shared risks, and collaborative opportunities.

Constituency Data Summary: {json.dumps(data.get('constituency', {}), default=str) if data.get('constituency') else "No specific constituency"}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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
NOTE: Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend."""

        # Call LLM API
        ai_response = call_llm_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            response=ai_response,
            ttl_hours=24
        )

        logger.info("Warmed cache for county narrative")

    except Exception as e:
        logger.error(f"Failed to warm county narrative cache: {e}")


def warm_finding_classifier_cache():
    """Warm cache for audit finding classifier."""
    logger.info("Warming cache for finding classifier")

    try:
        # Check if already cached
        cache_parameters = {"module": "finding_classifier"}
        cached = get_cached_ai_response(
            prompt="Classify and analyze audit findings",
            model=GROQ_MODEL,
            parameters=cache_parameters
        )

        if cached:
            logger.debug("Cache already exists for finding classifier")
            return

        # Extract all data
        data = validate_and_extract_data()
        if "error" in data:
            logger.warning(f"Skipping finding classifier: {data['error']}")
            return

        # Prepare prompt matching ai_engine.py endpoint
        prompt = f"""Classify and analyze audit findings from both MP (NG-CDF) and Governor (county executive) sources.
Categorize by severity, provide plain English summaries, and recommend actions.

Audit Findings Data: {json.dumps(data.get('governor', {}).get('audit_findings', []), default=str)}

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
NOTE: severity must be High, Medium, or Low. Provide comprehensive, accessible narratives. Charts/tables are rendered separately by the frontend."""

        # Call LLM API
        ai_response = call_llm_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            response=ai_response,
            ttl_hours=24
        )

        logger.info("Warmed cache for finding classifier")

    except Exception as e:
        logger.error(f"Failed to warm finding classifier cache: {e}")


def warm_cross_leader_comparator_cache():
    """Warm cache for cross-leader comparator."""
    logger.info("Warming cache for cross-leader comparator")

    try:
        # Check if already cached
        cache_parameters = {"module": "cross_leader_comparator"}
        cached = get_cached_ai_response(
            prompt="Compare MP and Governor performance",
            model=GROQ_MODEL,
            parameters=cache_parameters
        )

        if cached:
            logger.debug("Cache already exists for cross-leader comparator")
            return

        # Extract all data
        data = validate_and_extract_data()
        if "error" in data:
            logger.warning(f"Skipping cross-leader comparator: {data['error']}")
            return

        # Prepare prompt matching ai_engine.py endpoint (note: chart_data/radar_data is computed server-side)
        prompt = f"""Compare MP (NG-CDF legislative) and Governor (county executive) performance across multiple dimensions.
Analyze allocation effectiveness, audit outcomes, correct appropriations, budget absorption, and fiscal health.

Constituency Data: {json.dumps(data.get('constituency', {}), default=str) if data.get('constituency') else "Aggregated constituency data"}
Governor Data: {json.dumps(data.get('governor', {}), default=str)}

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

        # Call LLM API
        ai_response = call_llm_api(prompt)

        # Cache the response
        cache_ai_response(
            prompt=prompt,
            model=GROQ_MODEL,
            parameters=cache_parameters,
            response=ai_response,
            ttl_hours=24
        )

        logger.info("Warmed cache for cross-leader comparator")

    except Exception as e:
        logger.error(f"Failed to warm cross-leader comparator cache: {e}")


def main():
    """Main function to warm all caches."""
    logger.info("Starting cache warming process for Accountability Platform AI Engine")

    try:
        # Warm constituency caches
        warm_constituency_cache()

        # Warm governor caches
        warm_governor_cache()

        # Warm special caches
        warm_county_narrative_cache()
        warm_finding_classifier_cache()
        warm_cross_leader_comparator_cache()

        logger.info("Cache warming process completed successfully")

    except Exception as e:
        logger.error(f"Cache warming process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()