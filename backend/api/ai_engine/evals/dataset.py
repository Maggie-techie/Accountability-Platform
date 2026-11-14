"""
Evaluation Dataset - Golden examples for testing AI outputs.
Run these on every prompt/model change to prevent regressions.
"""
from typing import Optional
from dataclasses import dataclass
from api.ai_engine.core.schemas import (
    RiskScoreOutput, RiskLevelOutput, SummaryOutput,
    AnomaliesOutput, PeerRankOutput, CitizenActionsOutput,
    DataSourcesOutput, FiscalHealthOutput, DeptAbsorptionOutput,
    OSRAnalysisOutput, DepartmentFlagsOutput, TopRisksOutput,
    CountyNarrativeOutput, FindingClassifierOutput, CompareOutput
)


@dataclass
class EvalCase:
    """Single evaluation case."""
    module: str                    # e.g., "risk_score", "fiscal_health"
    leader_type: str               # "mp", "governor", "county"
    input_data: dict               # Input parameters (constituency_slug, etc.)
    expected_output: dict          # Expected key fields in response
    min_quality_score: float = 0.8 # Minimum quality threshold (0-1)


# ============================================================
# MP / Constituency Eval Cases
# ============================================================

MP_EVAL_CASES = [
    EvalCase(
        module="risk_score",
        leader_type="mp",
        input_data={"constituency_slug": "tetu"},
        expected_output={
            "narrative_fields": {
                "risk_score": {"type": "int", "min": 0, "max": 100},
                "risk_level": {"type": "str", "enum": ["High", "Medium", "Low"]},
                "summary": {"type": "str", "min_length": 50},
                "key_drivers": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 30},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="risk_level",
        leader_type="mp",
        input_data={"constituency_slug": "kieni"},
        expected_output={
            "narrative_fields": {
                "risk_level": {"type": "str", "enum": ["High", "Medium", "Low"]},
                "summary": {"type": "str", "min_length": 50},
                "anomalies_found": {"type": "int", "min": 0},
                "top_anomalies": {"type": "list"},
                "what_this_means": {"type": "str", "min_length": 30},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="summary",
        leader_type="mp",
        input_data={"constituency_slug": "mathira"},
        expected_output={
            "narrative_fields": {
                "constituency_name": {"type": "str"},
                "mp_name": {"type": "str"},
                "financial_health": {"type": "str", "enum": ["Strong", "Moderate", "Weak"]},
                "summary": {"type": "str", "min_length": 100},
                "key_achievements": {"type": "list", "min_items": 1, "max_items": 5},
                "key_concerns": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="anomalies",
        leader_type="mp",
        input_data={"constituency_slug": "othaya"},
        expected_output={
            "narrative_fields": {
                "anomalies_found": {"type": "int", "min": 0},
                "summary": {"type": "str", "min_length": 50},
                "anomalies": {"type": "list"},
                "what_this_means": {"type": "str", "min_length": 30},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="peer_rank",
        leader_type="mp",
        input_data={"constituency_slug": "mukurweini"},
        expected_output={
            "narrative_fields": {
                "rank": {"type": "int", "min": 1},
                "total_constituencies": {"type": "int", "min": 1},
                "percentile": {"type": "int", "min": 0, "max": 100},
                "summary": {"type": "str", "min_length": 50},
                "strengths": {"type": "list", "min_items": 1, "max_items": 5},
                "weaknesses": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 30},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="citizen_actions",
        leader_type="mp",
        input_data={"constituency_slug": "tetu"},
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 50},
                "priority_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 30},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="data_sources",
        leader_type="mp",
        input_data={"constituency_slug": "kieni"},
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 50},
                "sources": {"type": "list", "min_items": 1, "max_items": 10},
                "gaps": {"type": "list"},
                "what_this_means": {"type": "str", "min_length": 30},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
]


# ============================================================
# Governor Eval Cases
# ============================================================

GOVERNOR_EVAL_CASES = [
    EvalCase(
        module="fiscal_health",
        leader_type="governor",
        input_data={},
        expected_output={
            "narrative_fields": {
                "overall_rating": {"type": "str", "enum": ["Strong", "Moderate", "Weak"]},
                "summary": {"type": "str", "min_length": 100},
                "revenue_analysis": {"type": "str", "min_length": 50},
                "expenditure_analysis": {"type": "str", "min_length": 50},
                "debt_position": {"type": "str", "min_length": 30},
                "audit_outcomes": {"type": "str", "min_length": 50},
                "key_strengths": {"type": "list", "min_items": 1, "max_items": 5},
                "key_risks": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="dept_absorption",
        leader_type="governor",
        input_data={},
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 50},
                "departments": {"type": "list", "min_items": 1},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="osr_analysis",
        leader_type="governor",
        input_data={},
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 50},
                "trend": {"type": "str", "enum": ["Improving", "Stable", "Declining"]},
                "revenue_streams": {"type": "list", "min_items": 1},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="department_flags",
        leader_type="governor",
        input_data={},
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 50},
                "flags": {"type": "list"},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="top_risks",
        leader_type="governor",
        input_data={},
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 50},
                "risks": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
]


# ============================================================
# County / Cross-Leader Eval Cases
# ============================================================

COUNTY_EVAL_CASES = [
    EvalCase(
        module="county_narrative",
        leader_type="county",
        input_data={},
        expected_output={
            "narrative_fields": {
                "county_name": {"type": "str"},
                "governor_name": {"type": "str"},
                "mps": {"type": "list", "min_items": 1},
                "executive_summary": {"type": "str", "min_length": 100},
                "ngcdf_overview": {"type": "str", "min_length": 50},
                "executive_overview": {"type": "str", "min_length": 50},
                "cross_leader_analysis": {"type": "str", "min_length": 50},
                "shared_risks": {"type": "list", "min_items": 1, "max_items": 5},
                "collaborative_opportunities": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="finding_classifier",
        leader_type="county",
        input_data={"finding_text": "Misappropriation of KSh 5M in road construction"},
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 50},
                "findings": {"type": "list"},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
    EvalCase(
        module="compare",
        leader_type="county",
        input_data={
            "leader1_type": "governor",
            "leader2_type": "constituency",
            "leader2_id": "tetu"
        },
        expected_output={
            "narrative_fields": {
                "summary": {"type": "str", "min_length": 100},
                "mp_strengths": {"type": "list", "min_items": 1, "max_items": 5},
                "mp_weaknesses": {"type": "list", "min_items": 1, "max_items": 5},
                "governor_strengths": {"type": "list", "min_items": 1, "max_items": 5},
                "governor_weaknesses": {"type": "list", "min_items": 1, "max_items": 5},
                "shared_challenges": {"type": "list", "min_items": 1, "max_items": 5},
                "what_this_means": {"type": "str", "min_length": 50},
                "citizen_actions": {"type": "list", "min_items": 1, "max_items": 5},
                "data_quality_note": {"type": "str"}
            }
        }
    ),
]


# ============================================================
# All Eval Cases Combined
# ============================================================

ALL_EVAL_CASES = MP_EVAL_CASES + GOVERNOR_EVAL_CASES + COUNTY_EVAL_CASES


# ============================================================
# Evaluation Runner
# ============================================================

def validate_against_expected(response: dict, expected: dict, path: str = "") -> list[str]:
    """
    Validate response against expected structure.
    Returns list of error messages (empty if valid).
    """
    errors = []

    for key, spec in expected.items():
        current_path = f"{path}.{key}" if path else key

        if key not in response:
            errors.append(f"{current_path}: missing required field")
            continue

        value = response[key]

        if isinstance(spec, dict) and "type" in spec:
            # Type check
            expected_type = spec["type"]
            if expected_type == "int" and not isinstance(value, int):
                errors.append(f"{current_path}: expected int, got {type(value).__name__}")
            elif expected_type == "str" and not isinstance(value, str):
                errors.append(f"{current_path}: expected str, got {type(value).__name__}")
            elif expected_type == "list" and not isinstance(value, list):
                errors.append(f"{current_path}: expected list, got {type(value).__name__}")
            elif expected_type == "dict" and not isinstance(value, dict):
                errors.append(f"{current_path}: expected dict, got {type(value).__name__}")

            # Enum check
            if "enum" in spec and value not in spec["enum"]:
                errors.append(f"{current_path}: value '{value}' not in allowed enum {spec['enum']}")

            # Min/max for numbers
            if "min" in spec and isinstance(value, (int, float)) and value < spec["min"]:
                errors.append(f"{current_path}: value {value} below minimum {spec['min']}")
            if "max" in spec and isinstance(value, (int, float)) and value > spec["max"]:
                errors.append(f"{current_path}: value {value} above maximum {spec['max']}")

            # Min/max items for lists
            if "min_items" in spec and isinstance(value, list) and len(value) < spec["min_items"]:
                errors.append(f"{current_path}: list has {len(value)} items, minimum {spec['min_items']}")
            if "max_items" in spec and isinstance(value, list) and len(value) > spec["max_items"]:
                errors.append(f"{current_path}: list has {len(value)} items, maximum {spec['max_items']}")

            # Min length for strings
            if "min_length" in spec and isinstance(value, str) and len(value) < spec["min_length"]:
                errors.append(f"{current_path}: string length {len(value)} below minimum {spec['min_length']}")

        elif isinstance(spec, dict):
            # Nested object - recurse
            if isinstance(value, dict):
                nested_errors = validate_against_expected(value, spec, current_path)
                errors.extend(nested_errors)
            else:
                errors.append(f"{current_path}: expected dict, got {type(value).__name__}")

        elif isinstance(spec, list) and spec:
            # List of items with same spec
            if isinstance(value, list):
                for i, item in enumerate(value):
                    item_errors = validate_against_expected(item, spec[0], f"{current_path}[{i}]")
                    errors.extend(item_errors)

    return errors


def run_eval_case(case: EvalCase, actual_response: dict) -> tuple[bool, list[str]]:
    """
    Run a single eval case against actual response.
    Returns (passed, error_messages).
    """
    # Validate structure
    errors = validate_against_expected(
        actual_response.get("data", actual_response),
        case.expected_output.get("narrative_fields", case.expected_output)
    )

    # Check success field
    if not actual_response.get("success", False):
        errors.append("Response success=False")

    # Check for error flag
    if actual_response.get("data", {}).get("_error"):
        errors.append("Response contains _error flag")

    passed = len(errors) == 0
    return passed, errors


def run_all_evals(eval_function) -> dict:
    """
    Run all eval cases against the provided eval_function.

    eval_function(module, leader_type, input_data) -> response_dict

    Returns summary dict with results.
    """
    results = {
        "total": len(ALL_EVAL_CASES),
        "passed": 0,
        "failed": 0,
        "details": []
    }

    for case in ALL_EVAL_CASES:
        try:
            response = eval_function(case.module, case.leader_type, case.input_data)
            passed, errors = run_eval_case(case, response)

            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "module": case.module,
                "leader_type": case.leader_type,
                "input": case.input_data,
                "passed": passed,
                "errors": errors
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "module": case.module,
                "leader_type": case.leader_type,
                "input": case.input_data,
                "passed": False,
                "errors": [f"Exception: {str(e)}"]
            })

    results["pass_rate"] = results["passed"] / results["total"] if results["total"] > 0 else 0
    return results