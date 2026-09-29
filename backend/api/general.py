from flask import Blueprint, request, jsonify
from api.database.connection import get_db
import logging
import os
import sys
import threading

# Add the ml_models directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml_models'))

# Import the GNN anomaly detector. Catch Exception (not just ImportError):
# torch / torch_geometric can also fail with OSError or version errors.
try:
    from ml_models.gnn_anomaly_detector import get_gnn_detector
    GNN_AVAILABLE = True
except Exception as e:
    GNN_AVAILABLE = False
    logging.warning(f"GNN anomaly detector not available: {e}")

general_bp = Blueprint("general", __name__)

# Prevents two training runs from overlapping (e.g. a double click)
_train_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _int_arg(name, default, minimum=1, maximum=None):
    """Parse an int query param without raising on bad input."""
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    value = max(minimum, value)
    if maximum is not None:
        value = min(value, maximum)
    return value


def normalize_severity(value):
    """Map free-text severities ('Qualified / Medium', 'Ongoing Liability') to High/Medium/Low."""
    text = (value or "").lower()
    if "high" in text or "adverse" in text:
        return "High"
    if "medium" in text:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Unified Findings Endpoint
# ---------------------------------------------------------------------------
@general_bp.route("/findings", methods=["GET"])
def get_unified_findings():
    """
    Get all audit findings for both Governor and MP leaders in a unified format.
    Query parameters:
    - leader_type: governor / constituency
    - constituency_slug: filter constituency findings (implies leader_type=constituency)
    - finding_type: misappropriation / correct_appropriation
    - page (default 1), limit (default 10, max 100)
    """
    try:
        db = get_db()

        leader_type = request.args.get('leader_type')
        constituency_slug = request.args.get('constituency_slug')
        finding_type = request.args.get('finding_type')
        page = _int_arg('page', 1)
        limit = _int_arg('limit', 10, maximum=100)
        skip = (page - 1) * limit

        if constituency_slug and not leader_type:
            leader_type = "constituency"

        findings = []

        if leader_type != "governor":
            query = {}
            if constituency_slug:
                query["constituency_slug"] = constituency_slug
            if finding_type:
                query["finding_type"] = finding_type

            for f in db.audit_findings.find(query):
                findings.append({
                    "_id": str(f["_id"]),
                    "leader_type": "constituency",
                    "leader_id": f.get("constituency_slug", ""),
                    "leader_name": f.get("mp_name", ""),
                    "constituency": f.get("constituency", ""),
                    "financial_year": f.get("fy_reviewed", ""),
                    "amount_flagged_kshm": 0,
                    "severity": "",
                    "finding_type": f.get("finding_type", ""),
                    "misappropriation_notes": "",
                    "recommendation": "",
                    # Some records store the text under "finding" instead of "note"
                    "note": f.get("note") or f.get("finding", ""),
                    "fy_reviewed": f.get("fy_reviewed", ""),
                    "amount_at_risk": f.get("amount_at_risk", ""),
                    "county": f.get("county", ""),
                    "county_code": f.get("county_code", ""),
                })

        if leader_type != "constituency":
            query = {}
            if finding_type:
                # Governor data uses "correct" where MP data uses "correct_appropriation"
                query["finding_type"] = "correct" if finding_type == "correct_appropriation" else finding_type

            # NOTE: collection is county_audit_findings (same one admin/summary and /anomalies use)
            for f in db.county_audit_findings.find(query):
                findings.append({
                    "_id": str(f["_id"]),
                    "leader_type": "governor",
                    "leader_id": f.get("governor", ""),
                    "leader_name": f.get("governor", ""),
                    "category": f.get("category", ""),
                    "constituency": "",
                    "financial_year": f.get("financial_year", ""),
                    "amount_flagged_kshm": f.get("amount_flagged_kshm", 0),
                    "severity": f.get("severity", ""),
                    "finding_type": "misappropriation" if f.get("finding_type") == "misappropriation" else "correct_appropriation",
                    "misappropriation_notes": f.get("misappropriation_notes", ""),
                    "recommendation": f.get("recommendation", ""),
                    "note": "",
                    "fy_reviewed": "",
                    "amount_at_risk": "",
                    "county": f.get("county", ""),
                    "county_code": f.get("county_code", ""),
                })

        # Paginate the combined list so page N really is page N across both sources
        total = len(findings)
        return jsonify({
            "findings": findings[skip:skip + limit],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit,
            },
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve unified findings", "details": str(e)}), 500


# ---------------------------------------------------------------------------
# Compare Endpoint
# ---------------------------------------------------------------------------
@general_bp.route("/compare", methods=["GET"])
def compare_leaders():
    """
    Compare two leaders (governor or constituency MPs).
    Query parameters: leader1_type, leader1_id, leader2_type, leader2_id, metrics
    (governor id = governor name, constituency id = slug).
    """
    try:
        db = get_db()

        leader1_type = request.args.get('leader1_type', 'governor')
        leader1_id = request.args.get('leader1_id')
        leader2_type = request.args.get('leader2_type', 'constituency')
        leader2_id = request.args.get('leader2_id')
        metrics_param = request.args.get('metrics', 'financial,audit,performance')
        metrics = [m.strip() for m in metrics_param.split(',') if m.strip()] or ['financial', 'audit', 'performance']

        if not leader1_id or not leader2_id:
            return jsonify({"error": "Both leader1_id and leader2_id are required"}), 400

        loaders = {"governor": get_governor_data, "constituency": get_constituency_data}
        for label, ltype in (("leader1_type", leader1_type), ("leader2_type", leader2_type)):
            if ltype not in loaders:
                return jsonify({"error": f"Invalid {label}. Must be 'governor' or 'constituency'"}), 400

        leader1_data = loaders[leader1_type](db, leader1_id)
        if not leader1_data:
            return jsonify({"error": f"Leader 1 not found: {leader1_id}"}), 404

        leader2_data = loaders[leader2_type](db, leader2_id)
        if not leader2_data:
            return jsonify({"error": f"Leader 2 not found: {leader2_id}"}), 404

        leader1_metrics = calculate_leader_metrics(db, leader1_data, leader1_type, metrics)
        leader2_metrics = calculate_leader_metrics(db, leader2_data, leader2_type, metrics)

        comparison = {
            "leader1": {"type": leader1_type, "id": leader1_id, "name": leader1_data.get("name", ""), "metrics": leader1_metrics},
            "leader2": {"type": leader2_type, "id": leader2_id, "name": leader2_data.get("name", ""), "metrics": leader2_metrics},
        }

        difference = {}
        winner_scores = {"leader1": 0, "leader2": 0}
        for metric in metrics:
            diff = leader1_metrics.get(metric, 0) - leader2_metrics.get(metric, 0)
            difference[metric] = diff
            if diff > 0:
                winner_scores["leader1"] += 1
            elif diff < 0:
                winner_scores["leader2"] += 1

        if winner_scores["leader1"] > winner_scores["leader2"]:
            winner = "leader1"
        elif winner_scores["leader2"] > winner_scores["leader1"]:
            winner = "leader2"
        else:
            winner = "tie"

        comparison["difference"] = difference
        comparison["winner"] = winner

        return jsonify({"comparison": comparison}), 200

    except Exception as e:
        return jsonify({"error": "Failed to compare leaders", "details": str(e)}), 500


# ---------------------------------------------------------------------------
# Admin Dashboard Endpoints
# ---------------------------------------------------------------------------
@general_bp.route("/admin/summary", methods=["GET"])
def admin_summary():
    """Get admin dashboard summary statistics"""
    try:
        db = get_db()

        total_constituencies = db.constituencies.count_documents({})
        total_governors = db.county_leaders.count_documents({})
        total_mps = db.mps.count_documents({})
        total_allocations = db.allocations.count_documents({})
        total_audit_findings = db.audit_findings.count_documents({}) + db.county_audit_findings.count_documents({})

        recent_allocations = list(db.allocations.find().sort([("_id", -1)]).limit(5))
        for alloc in recent_allocations:
            alloc["_id"] = str(alloc["_id"])

        recent_findings = list(db.audit_findings.find().sort([("_id", -1)]).limit(5))
        for finding in recent_findings:
            finding["_id"] = str(finding["_id"])

        recent_governor_findings = list(db.county_audit_findings.find().sort([("_id", -1)]).limit(5))
        for finding in recent_governor_findings:
            finding["_id"] = str(finding["_id"])

        # Status fields the dashboard cards read
        flagged_findings = db.audit_findings.count_documents({"finding_type": "misappropriation"})
        validation_status = "Attention needed" if flagged_findings > 0 else "No issues flagged"

        model_status, last_trained = "Not available", None
        if GNN_AVAILABLE:
            try:
                detector = get_gnn_detector()
                model_status = "Trained" if detector.is_trained else "Not trained"
                last_trained = detector.trained_at[:10] if detector.trained_at else None
            except Exception as e:
                logging.warning(f"Could not read GNN status for summary: {e}")

        return jsonify({
            "success": True,
            "data": {
                "total_constituencies": total_constituencies,
                "total_governors": total_governors,
                "total_mps": total_mps,
                "total_allocations": total_allocations,
                "total_audit_findings": total_audit_findings,
                "flagged_findings": flagged_findings,
                "validation_status": validation_status,
                "model_status": model_status,
                "last_trained": last_trained,
                "recent_allocations": recent_allocations,
                "recent_findings": recent_findings,
                "recent_governor_findings": recent_governor_findings,
            },
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch admin summary", "details": str(e)}), 500


@general_bp.route("/anomalies", methods=["GET"])
def get_anomalies():
    """
    Get detected anomalies from audit data.
    Constituency: only 'misappropriation' findings count as anomalies (positive
    'correct_appropriation' findings are not anomalies) and are rated High.
    Governor: every finding, with its free-text severity mapped to High/Medium/Low.
    """
    try:
        db = get_db()

        constituency_slug = request.args.get('constituency_slug')
        leader_type = request.args.get('leader_type')  # governor or constituency
        limit = _int_arg('limit', 50, maximum=500)

        anomalies = []

        if leader_type != "governor":
            query = {"finding_type": "misappropriation"}
            if constituency_slug:
                query["constituency_slug"] = constituency_slug

            for finding in db.audit_findings.find(query).limit(limit):
                anomalies.append({
                    "_id": str(finding["_id"]),
                    "type": "constituency",
                    "constituency_slug": finding.get("constituency_slug"),
                    "finding_type": finding.get("finding_type"),
                    "note": finding.get("note") or finding.get("finding", ""),
                    "amount_at_risk": finding.get("amount_at_risk", ""),
                    "county": finding.get("county", ""),
                    "financial_year": finding.get("fy_reviewed", ""),
                    "severity": "High",
                })

        if leader_type != "constituency":
            for finding in db.county_audit_findings.find({}).limit(limit):
                anomalies.append({
                    "_id": str(finding["_id"]),
                    "type": "governor",
                    "governor_name": finding.get("governor"),
                    "finding_type": finding.get("finding_type"),
                    "misappropriation_notes": finding.get("misappropriation_notes", ""),
                    "amount_flagged_kshm": finding.get("amount_flagged_kshm", 0),
                    "severity": normalize_severity(finding.get("severity")),
                    "county": finding.get("county", ""),
                    "financial_year": finding.get("financial_year", ""),
                })

        return jsonify({"success": True, "data": anomalies, "count": len(anomalies)}), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch anomalies", "details": str(e)}), 500


@general_bp.route("/admin/import-history", methods=["GET"])
def admin_import_history():
    """Get history of data imports (mock data until an imports collection exists)"""
    try:
        get_db()  # keep the connection check

        import_history = [
            {"id": "1", "timestamp": "2024-01-15T10:30:00Z", "data_type": "constituencies", "records_imported": 290, "status": "completed", "imported_by": "system"},
            {"id": "2", "timestamp": "2024-01-15T11:15:00Z", "data_type": "allocations", "records_imported": 1450, "status": "completed", "imported_by": "system"},
            {"id": "3", "timestamp": "2024-01-15T12:00:00Z", "data_type": "audit_findings", "records_imported": 890, "status": "completed", "imported_by": "system"},
            {"id": "4", "timestamp": "2024-01-15T12:45:00Z", "data_type": "county_leaders", "records_imported": 47, "status": "completed", "imported_by": "system"},
        ]

        return jsonify({"success": True, "data": import_history, "count": len(import_history)}), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch import history", "details": str(e)}), 500


# ---------------------------------------------------------------------------
# GNN-based Anomaly Detection Endpoints
# ---------------------------------------------------------------------------
@general_bp.route("/anomalies/gnn/train", methods=["POST"])
def train_gnn_anomaly_model():
    """Train the GNN-based anomaly detection model"""
    if not GNN_AVAILABLE:
        return jsonify({"error": "GNN anomaly detection is not available. Required dependencies are missing."}), 503

    if not _train_lock.acquire(blocking=False):
        return jsonify({"error": "Training is already in progress"}), 409

    try:
        db = get_db()
        detector = get_gnn_detector()
        result = detector.train(db)

        if result["status"] == "success":
            return jsonify({
                "success": True,
                "message": "GNN anomaly detection model trained successfully",
                "data": result,
            }), 200

        return jsonify({"error": "Failed to train GNN model", "details": result}), 500

    except Exception as e:
        logging.exception("Error in GNN model training")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
    finally:
        _train_lock.release()


@general_bp.route("/anomalies/gnn/detect", methods=["GET"])
def detect_gnn_anomalies():
    """Detect anomalies using the trained GNN model"""
    if not GNN_AVAILABLE:
        return jsonify({"error": "GNN anomaly detection is not available. Required dependencies are missing."}), 503

    try:
        db = get_db()
        detector = get_gnn_detector()
        result = detector.detect_anomalies(db)

        if result["status"] == "success":
            return jsonify({
                "success": True,
                "message": "GNN anomaly detection completed successfully",
                "data": result,
            }), 200

        return jsonify({"error": "Failed to detect anomalies with GNN model", "details": result}), 500

    except Exception as e:
        logging.exception("Error in GNN anomaly detection")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@general_bp.route("/anomalies/gnn/status", methods=["GET"])
def gnn_model_status():
    """
    Status of the GNN model. Returns 200 with model_available=False when the
    dependencies are missing, so the UI can show that state instead of an error.
    """
    if not GNN_AVAILABLE:
        return jsonify({"success": True, "data": {"model_available": False, "is_trained": False}}), 200

    try:
        detector = get_gnn_detector()
        trained = detector.is_trained

        return jsonify({
            "success": True,
            "data": {
                "model_available": True,
                "is_trained": trained,
                "trained_at": detector.trained_at,
                "num_nodes": detector.num_nodes,
                "num_edges": detector.num_edges,
                "val_auc": detector.val_auc,
                "epochs": detector.epochs,
                "final_loss": detector.train_losses[-1] if detector.train_losses else None,
                "model_parameters": {
                    "input_dim": detector.input_dim,
                    "hidden_dim": detector.hidden_dim,
                    "embedding_dim": detector.embedding_dim,
                } if trained else None,
                "history": list(reversed(detector.training_history)),  # newest first
            },
        }), 200

    except Exception as e:
        logging.exception("Error getting GNN model status")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------
def get_governor_data(db, governor_name):
    """Get governor data for comparison"""
    profile = db.county_leaders.find_one({"governor": governor_name}, {"_id": 0})
    if not profile:
        return None

    # Total revenue across all years (amount_kshb is in KSh billions)
    finances = list(db.county_finances.find({"governor": governor_name}))
    total_revenue = sum(f.get("amount_kshb", 0) for f in finances)

    # cursor.count() was removed in PyMongo 4
    audit_count = db.county_audit_findings.count_documents({"governor": governor_name})

    # Average department absorption rate
    depts = list(db.department_absorption.find({}))
    avg_absorption = sum(d.get("absorption_rate", 0) for d in depts) / len(depts) if depts else 0

    return {
        "name": profile.get("name") or profile.get("governor", ""),
        "total_revenue": total_revenue,
        "audit_count": audit_count,
        "avg_absorption": avg_absorption,
        "role": profile.get("role", ""),
        "tenure": profile.get("tenure", ""),
        "party": profile.get("party", ""),
        "county": profile.get("county", ""),
        "county_code": profile.get("county_code", ""),
    }


def get_constituency_data(db, constituency_slug):
    """Get constituency data for comparison"""
    constituency = db.constituencies.find_one({"slug": constituency_slug}, {"_id": 0})
    if not constituency:
        return None

    # Total allocations across all years (amount_kshm is in KSh millions)
    allocations = list(db.allocations.find({"constituency_slug": constituency_slug}))
    total_allocations = sum(a.get("amount_kshm", 0) for a in allocations)

    audit_count = db.audit_findings.count_documents({"constituency_slug": constituency_slug})

    mp = db.mps.find_one({"constituency_slug": constituency_slug}, {"_id": 0})

    return {
        "name": constituency.get("name", ""),
        "total_allocations": total_allocations,
        "audit_count": audit_count,
        "mp_name": (mp.get("name") or mp.get("mp_name", "")) if mp else "",
        "mp_party": mp.get("party", "") if mp else "",
        "mp_tenure": mp.get("tenure", "") if mp else "",
        "oag_opinion": constituency.get("oag_opinion", ""),
        "audit_status": constituency.get("audit_status", ""),
        "county": constituency.get("county", ""),
        "county_code": constituency.get("county_code", ""),
    }


def calculate_leader_metrics(db, leader_data, leader_type, metrics):
    """Calculate 0-100 metrics for a leader based on their data"""
    metrics_dict = {}

    if "audit" in metrics:
        # Fewer audit findings is better
        metrics_dict["audit"] = max(0, 100 - leader_data.get("audit_count", 0) * 10)

    if leader_type == "governor":
        if "financial" in metrics:
            # total_revenue is in KSh billions; scale so ~10B maps to 100
            metrics_dict["financial"] = min(leader_data.get("total_revenue", 0) / 10.0 * 100, 100)

        if "performance" in metrics:
            # Average department absorption rate (already a percentage)
            metrics_dict["performance"] = min(leader_data.get("avg_absorption", 0), 100)

    else:  # constituency
        if "financial" in metrics:
            # total_allocations is in KSh millions; scale so ~500M maps to 100
            metrics_dict["financial"] = min(leader_data.get("total_allocations", 0) / 500.0 * 100, 100)

        if "performance" in metrics:
            opinion_scores = {"Unqualified": 90, "Unqualified*": 85, "Qualified": 60, "Adverse": 30}
            opinion_score = opinion_scores.get(leader_data.get("oag_opinion", ""), 50)

            status_scores = {"Clean": 20, "Concerning": 0, "Unknown": 0}
            status_score = status_scores.get(leader_data.get("audit_status", ""), 0)

            metrics_dict["performance"] = min(opinion_score + status_score, 100)

    return metrics_dict