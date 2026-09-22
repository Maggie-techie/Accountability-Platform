from flask import Blueprint, request, jsonify
from api.database.connection import get_db
from datetime import datetime

general_bp = Blueprint("general", __name__)

# Unified Findings Endpoint
@general_bp.route("/findings", methods=["GET"])
def get_unified_findings():
    """
    Get all audit findings for both Governor and MP leaders in a unified format.
    Query parameters:
    - leader_type: Filter by leader type (governor/constituency)
    - constituency_slug: Filter by constituency slug (for constituency findings)
    - finding_type: Filter by finding type (misappropriation/correct_appropriation)
    - page: Page number for pagination (default: 1)
    - limit: Number of items per page (default: 10)
    """
    try:
        db = get_db()

        # Build query conditions
        leader_type = request.args.get('leader_type')
        constituency_slug = request.args.get('constituency_slug')
        finding_type = request.args.get('finding_type')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        findings = []
        total_count = 0

        # Get constituency findings (MP/NG-CDF)
        if leader_type != "governor":  # Include constituency findings unless explicitly filtering for governor only
            constituency_query = {}
            if constituency_slug:
                constituency_query["constituency_slug"] = constituency_slug
            if finding_type:
                constituency_query["finding_type"] = finding_type

            constituency_cursor = db.audit_findings.find(constituency_query).skip(skip).limit(limit)

            for finding in constituency_cursor:
                finding["_id"] = str(finding["_id"])
                findings.append({
                    "_id": finding["_id"],
                    "leader_type": "constituency",
                    "leader_id": finding["constituency_slug"],
                    "leader_name": finding["mp_name"],
                    "constituency": finding["constituency"],
                    "financial_year": finding.get("fy_reviewed", ""),
                    "amount_flagged_kshm": 0,  # Constituency findings don't have direct amount in seed data
                    "severity": "",  # Severity not available in constituency findings seed data
                    "finding_type": finding["finding_type"],
                    "misappropriation_notes": "",  # Not in constituency findings
                    "recommendation": "",  # Not in constituency findings
                    "note": finding.get("note", ""),
                    "fy_reviewed": finding.get("fy_reviewed", ""),
                    "amount_at_risk": finding.get("amount_at_risk", ""),
                    "county": finding["county"],
                    "county_code": finding["county_code"]
                })

            # Get count for constituency findings
            constituency_count = db.audit_findings.count_documents(constituency_query)
            total_count += constituency_count

        # Get governor findings
        if leader_type != "constituency":  # Include governor findings unless explicitly filtering for constituency only
            governor_query = {}
            if finding_type:
                # Map finding_type values: "misappropriation" -> "misappropriation", "correct_appropriation" -> "correct"
                if finding_type == "correct_appropriation":
                    governor_query["finding_type"] = "correct"
                else:
                    governor_query["finding_type"] = finding_type

            governor_cursor = db.county_audit.find(governor_query).skip(skip).limit(limit)

            for finding in governor_cursor:
                finding["_id"] = str(finding["_id"])
                findings.append({
                    "_id": finding["_id"],
                    "leader_type": "governor",
                    "leader_id": finding["governor"],
                    "leader_name": finding["governor"],
                    "category": finding.get("category", ""),
                    "constituency": "",  # Not applicable for governor findings
                    "financial_year": finding.get("financial_year", ""),
                    "amount_flagged_kshm": finding.get("amount_flagged_kshm", 0),
                    "severity": finding.get("severity", ""),
                    "finding_type": "misappropriation" if finding.get("finding_type") == "misappropriation" else "correct_appropriation",
                    "misappropriation_notes": finding.get("misappropriation_notes", ""),
                    "recommendation": finding.get("recommendation", ""),
                    "note": "",  # Not in governor findings
                    "fy_reviewed": "",  # Not in governor findings
                    "amount_at_risk": "",  # Not in governor findings
                    "county": finding["county"],
                    "county_code": finding["county_code"]
                })

            # Get count for governor findings
            governor_count = db.county_audit.count_documents(governor_query)
            total_count += governor_count

        # If we filtered by leader_type and only one type was requested, we need to adjust the count
        if leader_type == "governor":
            total_count = db.county_audit.count_documents(governor_query)
        elif leader_type == "constituency":
            total_count = db.audit_findings.count_documents(constituency_query)

        return jsonify({
            "findings": findings,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit if limit > 0 else 0
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve unified findings", "details": str(e)}), 500

# Compare Endpoint
@general_bp.route("/compare", methods=["GET"])
def compare_leaders():
    """
    Compare two leaders (governor or constituency MPs) based on various metrics.
    Query parameters:
    - leader1_type: Type of first leader (governor/constituency)
    - leader1_id: ID of first leader (governor name or constituency slug)
    - leader2_type: Type of second leader (governor/constituency)
    - leader2_id: ID of second leader (governor name or constituency slug)
    - metrics: Comma-separated list of metrics to compare (financial, audit, performance)
    """
    try:
        db = get_db()

        # Get parameters
        leader1_type = request.args.get('leader1_type', 'governor')
        leader1_id = request.args.get('leader1_id')
        leader2_type = request.args.get('leader2_type', 'constituency')
        leader2_id = request.args.get('leader2_id')
        metrics_param = request.args.get('metrics', 'financial,audit,performance')

        # Parse metrics
        metrics = [m.strip() for m in metrics_param.split(',')] if metrics_param else ['financial', 'audit', 'performance']

        # Validate required parameters
        if not leader1_id or not leader2_id:
            return jsonify({"error": "Both leader1_id and leader2_id are required"}), 400

        # Get data for leader 1
        leader1_data = {}
        if leader1_type == "governor":
            leader1_data = get_governor_data(db, leader1_id)
        elif leader1_type == "constituency":
            leader1_data = get_constituency_data(db, leader1_id)
        else:
            return jsonify({"error": "Invalid leader1_type. Must be 'governor' or 'constituency'"}), 400

        if not leader1_data:
            return jsonify({"error": f"Leader 1 not found: {leader1_id}"}), 404

        # Get data for leader 2
        leader2_data = {}
        if leader2_type == "governor":
            leader2_data = get_governor_data(db, leader2_id)
        elif leader2_type == "constituency":
            leader2_data = get_constituency_data(db, leader2_id)
        else:
            return jsonify({"error": "Invalid leader2_type. Must be 'governor' or 'constituency'"}), 400

        if not leader2_data:
            return jsonify({"error": f"Leader 2 not found: {leader2_id}"}), 404

        # Calculate comparison metrics
        leader1_metrics = calculate_leader_metrics(db, leader1_data, leader1_type, metrics)
        leader2_metrics = calculate_leader_metrics(db, leader2_data, leader2_type, metrics)

        comparison = {
            "leader1": {
                "type": leader1_type,
                "id": leader1_id,
                "name": leader1_data.get("name", ""),
                "metrics": leader1_metrics
            },
            "leader2": {
                "type": leader2_type,
                "id": leader2_id,
                "name": leader2_data.get("name", ""),
                "metrics": leader2_metrics
            }
        }

        # Calculate differences and determine winner
        difference = {}
        winner_scores = {"leader1": 0, "leader2": 0}

        for metric in metrics:
            val1 = leader1_metrics.get(metric, 0)
            val2 = leader2_metrics.get(metric, 0)
            diff = val1 - val2
            difference[metric] = diff

            # Simple scoring: higher is better for most metrics
            if diff > 0:
                winner_scores["leader1"] += 1
            elif diff < 0:
                winner_scores["leader2"] += 1
            # Tie: no points awarded

        # Determine winner
        if winner_scores["leader1"] > winner_scores["leader2"]:
            winner = "leader1"
        elif winner_scores["leader2"] > winner_scores["leader1"]:
            winner = "leader2"
        else:
            winner = "tie"

        comparison["difference"] = difference
        comparison["winner"] = winner

        return jsonify({
            "comparison": comparison
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to compare leaders", "details": str(e)}), 500

# Admin Dashboard Endpoints
@general_bp.route("/admin/summary", methods=["GET"])
def admin_summary():
    """Get admin dashboard summary statistics"""
    try:
        db = get_db()

        # Get counts for various entities
        total_constituencies = db.constituencies.count_documents({})
        total_governors = db.county_leaders.count_documents({})
        total_mps = db.mps.count_documents({})
        total_allocations = db.allocations.count_documents({})
        total_audit_findings = db.audit_findings.count_documents({}) + db.county_audit_findings.count_documents({})

        # Get recent financial data
        recent_allocations = list(db.allocations.find().sort([("_id", -1)]).limit(5))
        for alloc in recent_allocations:
            alloc["_id"] = str(alloc["_id"])

        # Get recent audit findings
        recent_findings = list(db.audit_findings.find().sort([("_id", -1)]).limit(5))
        for finding in recent_findings:
            finding["_id"] = str(finding["_id"])

        recent_governor_findings = list(db.county_audit_findings.find().sort([("_id", -1)]).limit(5))
        for finding in recent_governor_findings:
            finding["_id"] = str(finding["_id"])

        return jsonify({
            "success": True,
            "data": {
                "total_constituencies": total_constituencies,
                "total_governors": total_governors,
                "total_mps": total_mps,
                "total_allocations": total_allocations,
                "total_audit_findings": total_audit_findings,
                "recent_allocations": recent_allocations,
                "recent_findings": recent_findings,
                "recent_governor_findings": recent_governor_findings
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch admin summary", "details": str(e)}), 500

@general_bp.route("/anomalies", methods=["GET"])
def get_anomalies():
    """Get detected anomalies from audit data"""
    try:
        db = get_db()

        # Get anomaly parameters from query
        constituency_slug = request.args.get('constituency_slug')
        leader_type = request.args.get('leader_type')  # governor or constituency
        limit = int(request.args.get('limit', 50))

        anomalies = []

        # Build query for constituency anomalies
        if leader_type != "governor":  # Include constituency anomalies
            constituency_query = {}
            if constituency_slug:
                constituency_query["constituency_slug"] = constituency_slug

            # Look for findings that might indicate anomalies
            constituency_cursor = db.audit_findings.find(constituency_query).limit(limit)
            for finding in constituency_cursor:
                finding["_id"] = str(finding["_id"])
                anomalies.append({
                    "_id": finding["_id"],
                    "type": "constituency",
                    "constituency_slug": finding.get("constituency_slug"),
                    "finding_type": finding.get("finding_type"),
                    "note": finding.get("note", ""),
                    "amount_at_risk": finding.get("amount_at_risk", ""),
                    "county": finding.get("county", ""),
                    "financial_year": finding.get("fy_reviewed", ""),
                    "severity": "medium"  # Default severity
                })

        # Build query for governor anomalies
        if leader_type != "constituency":  # Include governor anomalies
            governor_query = {}
            # For governor data, we might look for unusual patterns in financial data
            # For now, we'll get some governor audit findings
            governor_cursor = db.county_audit_findings.find(governor_query).limit(limit)
            for finding in governor_cursor:
                finding["_id"] = str(finding["_id"])
                anomalies.append({
                    "_id": finding["_id"],
                    "type": "governor",
                    "governor_name": finding.get("governor"),
                    "finding_type": finding.get("finding_type"),
                    "misappropriation_notes": finding.get("misappropriation_notes", ""),
                    "amount_flagged_kshm": finding.get("amount_flagged_kshm", 0),
                    "severity": finding.get("severity", "medium"),
                    "county": finding.get("county", ""),
                    "financial_year": finding.get("financial_year", "")
                })

        return jsonify({
            "success": True,
            "data": anomalies,
            "count": len(anomalies)
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch anomalies", "details": str(e)}), 500

@general_bp.route("/admin/import-history", methods=["GET"])
def admin_import_history():
    """Get history of data imports"""
    try:
        db = get_db()

        # For now, we'll return a mock import history since we don't have an import tracking collection
        # In a real implementation, this would query an imports or migrations collection
        import_history = [
            {
                "id": "1",
                "timestamp": "2024-01-15T10:30:00Z",
                "data_type": "constituencies",
                "records_imported": 290,
                "status": "completed",
                "imported_by": "system"
            },
            {
                "id": "2",
                "timestamp": "2024-01-15T11:15:00Z",
                "data_type": "allocations",
                "records_imported": 1450,
                "status": "completed",
                "imported_by": "system"
            },
            {
                "id": "3",
                "timestamp": "2024-01-15T12:00:00Z",
                "data_type": "audit_findings",
                "records_imported": 890,
                "status": "completed",
                "imported_by": "system"
            },
            {
                "id": "4",
                "timestamp": "2024-01-15T12:45:00Z",
                "data_type": "county_leaders",
                "records_imported": 47,
                "status": "completed",
                "imported_by": "system"
            }
        ]

        return jsonify({
            "success": True,
            "data": import_history,
            "count": len(import_history)
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch import history", "details": str(e)}), 500

def get_governor_data(db, governor_name):
    """Get governor data for comparison"""
    # Get governor profile
    profile = db.county_leaders.find_one({"governor": governor_name}, {"_id": 0})
    if not profile:
        return None

    # Get financial data (total revenue across all years)
    finances = list(db.county_finances.find({"governor": governor_name}))
    total_revenue = sum(f.get("amount_kshb", 0) for f in finances)

    # Get audit findings count
    audit_count = db.county_audit_findings.find({"governor": governor_name}).count()

    # Get department performance (average absorption rate)
    depts = list(db.department_absorption.find({}))  # Assuming governor data doesn't have governor field
    avg_absorption = 0
    if depts:
        avg_absorption = sum(d.get("absorption_rate", 0) for d in depts) / len(depts)

    return {
        "name": profile.get("name", ""),
        "total_revenue": total_revenue,
        "audit_count": audit_count,
        "avg_absorption": avg_absorption,
        "role": profile.get("role", ""),
        "tenure": profile.get("tenure", ""),
        "party": profile.get("party", ""),
        "county": profile.get("county", ""),
        "county_code": profile.get("county_code", "")
    }

def get_constituency_data(db, constituency_slug):
    """Get constituency data for comparison"""
    # Get constituency info
    constituency = db.constituencies.find_one({"slug": constituency_slug}, {"_id": 0})
    if not constituency:
        return None

    # Get financial data (total allocations across all years)
    allocations = list(db.allocations.find({"constituency_slug": constituency_slug}))
    total_allocations = sum(a.get("amount_kshm", 0) for a in allocations)

    # Get audit findings count
    audit_count = db.audit_findings.find({"constituency_slug": constituency_slug}).count()

    # Get MP info
    mp = db.mps.find_one({"constituency_slug": constituency_slug}, {"_id": 0})

    return {
        "name": constituency.get("name", ""),
        "total_allocations": total_allocations,
        "audit_count": audit_count,
        "mp_name": mp.get("name", "") if mp else "",
        "mp_party": mp.get("party", "") if mp else "",
        "mp_tenure": mp.get("tenure", "") if mp else "",
        "oag_opinion": constituency.get("oag_opinion", ""),
        "audit_status": constituency.get("audit_status", ""),
        "county": constituency.get("county", ""),
        "county_code": constituency.get("county_code", "")
    }

def calculate_leader_metrics(db, leader_data, leader_type, metrics):
    """Calculate metrics for a leader based on their data"""
    metrics_dict = {}

    if leader_type == "governor":
        # Financial metric: total revenue (normalized)
        if "financial" in metrics:
            # Normalize revenue to 0-100 scale (assuming max ~10B KSH for scaling)
            revenue = leader_data.get("total_revenue", 0)
            metrics_dict["financial"] = min(revenue / 1e6, 100)  # Convert to millions, cap at 100

        # Audit metric: fewer audit findings is better (invert and scale)
        if "audit" in metrics:
            audit_count = leader_data.get("audit_count", 0)
            # Lower audit count = better score, so invert: 100 - (count * 10) but cap at 0-100
            audit_score = max(0, 100 - (audit_count * 10))
            metrics_dict["audit"] = audit_score

        # Performance metric: average department absorption rate
        if "performance" in metrics:
            absorption = leader_data.get("avg_absorption", 0)
            metrics_dict["performance"] = min(absorption, 100)  # Already a percentage

    else:  # constituency
        # Financial metric: total allocations (normalized)
        if "financial" in metrics:
            # Normalize allocations to 0-100 scale (assuming max ~500M KSH for scaling)
            allocations = leader_data.get("total_allocations", 0)
            metrics_dict["financial"] = min(allocations / 5e6, 100)  # Convert to millions, cap at 100

        # Audit metric: fewer audit findings is better (invert and scale)
        if "audit" in metrics:
            audit_count = leader_data.get("audit_count", 0)
            # Lower audit count = better score, so invert: 100 - (count * 10) but cap at 0-100
            audit_score = max(0, 100 - (audit_count * 10))
            metrics_dict["audit"] = audit_score

        # Performance metric: based on OAG opinion and audit status
        if "performance" in metrics:
            # Simple scoring based on OAG opinion
            opinion_scores = {
                "Unqualified": 90,
                "Unqualified*": 85,
                "Qualified": 60,
                "Adverse": 30
            }
            opinion_score = opinion_scores.get(leader_data.get("oag_opinion", ""), 50)

            # Adjust based on audit status
            status_scores = {
                "Clean": 20,
                "Concerning": 0,
                "Unknown": 0
            }
            status_score = status_scores.get(leader_data.get("audit_status", ""), 0)

            metrics_dict["performance"] = min(opinion_score + status_score, 100)

    return metrics_dict