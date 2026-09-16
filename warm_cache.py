#!/usr/bin/env python3
"""
Cache warming utility for the Accountability Platform AI Engine.
Pre-populates the AI cache with commonly requested analyses to improve performance.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.api.ai_engine import (
    get_db,
    generate_cache_key,
    cache_ai_response,
    get_cached_ai_response,
    validate_and_extract_data,
    call_claude_api
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
                    model="claude",
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

                # Generate appropriate prompt based on module
                prompts = {
                    "risk_score": f"Analyze the financial risk for the constituency with slug '{slug}'. Based on the following data, provide a risk assessment:",
                    "risk_level": f"Analyze the risk level and anomalies for the constituency with slug '{slug}'. Based on the following data, provide insights:",
                    "summary": f"Generate a comprehensive summary for the constituency with slug '{slug}'. Based on the following data, provide insights:",
                    "anomalies": f"Detect anomalies in the financial and audit data for the constituency with slug '{slug}'. Based on the following data, identify any anomalies:",
                    "peer_rank": f"Analyze the peer ranking for the constituency with slug '{slug}' based on performance metrics:",
                    "citizen_actions": f"Generate recommended citizen actions for the constituency with slug '{slug}' based on audit findings and financial data:",
                    "data_sources": f"Evaluate the data sources and quality for the constituency with slug '{slug}':"
                }

                prompt = prompts.get(module, f"Analyze {module} for constituency {slug}")

                # Prepare full prompt with data
                full_prompt = f"""
                {prompt}

                Constituency Data: {json.dumps(data.get('constituency', {}), default=str)}
                Governor Data: {json.dumps(data.get('governor', {}), default=str)}

                Return ONLY a JSON object with the appropriate structure for the {module} module.
                """

                # Call Claude API (this would be the real API call in production)
                ai_response = call_claude_api(full_prompt)

                # Cache the response
                cache_ai_response(
                    prompt=full_prompt,
                    model="claude",
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
                    model="claude",
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

                # Generate appropriate prompt based on module
                prompts = {
                    "fiscal_health": "Analyze the fiscal health of the county government based on financial data, audit findings, and department performance:",
                    "dept_absorption": "Analyze department budget absorption rates and identify risks:",
                    "osr_analysis": "Analyze Own Source Revenue (OSR) performance and trends:",
                    "department_flags": "Identify department-specific risk flags based on budget performance and audit findings:",
                    "top_risks": "Identify the top risks facing the county government and recommend citizen actions:"
                }

                prompt = prompts.get(module, f"Analyze {module} for governor")

                # Prepare full prompt with data
                full_prompt = f"""
                {prompt}

                Governor Data: {json.dumps(data.get('governor', {}), default=str)}

                Return ONLY a JSON object with the appropriate structure for the {module} module.
                """

                # Call Claude API (this would be the real API call in production)
                ai_response = call_claude_api(full_prompt)

                # Cache the response
                cache_ai_response(
                    prompt=full_prompt,
                    model="claude",
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
            model="claude",
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

        # Prepare prompt
        prompt = """
        Generate a comprehensive county narrative covering both MP (NG-CDF) and Governor (county executive) perspectives.
        Include analysis of cross-leader relationships, shared risks, and collaborative opportunities.

        Return ONLY a JSON object with the county narrative structure.
        """

        # Prepare full prompt with data
        full_prompt = f"""
        {prompt}

        Constituency Data Summary: {json.dumps(data.get('constituency', {}), default=str) if data.get('constituency') else "No specific constituency"}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with the appropriate structure for the county narrative module.
        """

        # Call Claude API (this would be the real API call in production)
        ai_response = call_claude_api(full_prompt)

        # Cache the response
        cache_ai_response(
            prompt=full_prompt,
            model="claude",
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
            model="claude",
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

        # Prepare prompt
        prompt = """
        Classify and analyze audit findings from both MP (NG-CDF) and Governor (county executive) sources.
        Categorize by severity, provide plain English summaries, and recommend actions.

        Return ONLY a JSON object with the finding classifier structure.
        """

        # Prepare full prompt with data
        full_prompt = f"""
        {prompt}

        Audit Findings Data: {json.dumps(data.get('governor', {}).get('audit_findings', []), default=str)}

        Return ONLY a JSON object with the appropriate structure for the finding classifier module.
        """

        # Call Claude API (this would be the real API call in production)
        ai_response = call_claude_api(full_prompt)

        # Cache the response
        cache_ai_response(
            prompt=full_prompt,
            model="claude",
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
            model="claude",
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

        # Prepare prompt
        prompt = """
        Compare MP (NG-CDF legislative) and Governor (county executive) performance across multiple dimensions.
        Analyze allocation effectiveness, audit outcomes, correct appropriations, budget absorption, and fiscal health.

        Return ONLY a JSON object with the cross-leader comparator structure including radar data for visualization.
        """

        # Prepare full prompt with data
        full_prompt = f"""
        {prompt}

        Constituency Data: {json.dumps(data.get('constituency', {}), default=str) if data.get('constituency') else "Aggregated constituency data"}
        Governor Data: {json.dumps(data.get('governor', {}), default=str)}

        Return ONLY a JSON object with the appropriate structure for the cross-leader comparator module.
        """

        # Call Claude API (this would be the real API call in production)
        ai_response = call_claude_api(full_prompt)

        # Cache the response
        cache_ai_response(
            prompt=full_prompt,
            model="claude",
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