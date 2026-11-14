"""
Governor/County Executive AI Endpoints.
Generated using factory pattern to eliminate code duplication.
"""
from flask import Blueprint, jsonify
from ..core.factory import make_governor_endpoint, GOVERNOR_PROMPTS
from ..core.prompts import generate_governor_summary
from ..data.access import data_access

# Create blueprint
governor_bp = Blueprint("governor", __name__, url_prefix="/governor")


# ============================================================
# Standard Governor Endpoints (using factory)
# ============================================================

# Fiscal Health
governor_fiscal_health = make_governor_endpoint(
    module="fiscal_health",
    prompt_template=GOVERNOR_PROMPTS["fiscal_health"],
    summary_module="fiscal_health"
)
governor_bp.route("/fiscal_health", methods=["GET"])(governor_fiscal_health)


# Department Absorption
governor_dept_absorption = make_governor_endpoint(
    module="dept_absorption",
    prompt_template=GOVERNOR_PROMPTS["dept_absorption"],
    summary_module="dept_absorption"
)
governor_bp.route("/dept_absorption", methods=["GET"])(governor_dept_absorption)


# OSR Analysis
governor_osr_analysis = make_governor_endpoint(
    module="osr_analysis",
    prompt_template=GOVERNOR_PROMPTS["osr_analysis"],
    summary_module="osr_analysis"
)
governor_bp.route("/osr_analysis", methods=["GET"])(governor_osr_analysis)


# Department Flags
governor_department_flags = make_governor_endpoint(
    module="department_flags",
    prompt_template=GOVERNOR_PROMPTS["department_flags"],
    summary_module="department_flags"
)
governor_bp.route("/department_flags", methods=["GET"])(governor_department_flags)


# Top Risks
governor_top_risks = make_governor_endpoint(
    module="top_risks",
    prompt_template=GOVERNOR_PROMPTS["top_risks"],
    summary_module="top_risks"
)
governor_bp.route("/top_risks", methods=["GET"])(governor_top_risks)