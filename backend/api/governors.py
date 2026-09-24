from flask import Blueprint, jsonify, request
from api.database.connection import get_db
from datetime import datetime

governor_bp = Blueprint("governor", __name__)


# creating a function for converting objectid to string
def serializable_doc(data):
    for doc in data:
        doc["_id"] = str(doc["_id"])
    return data

def serializable_single(doc):
    """For a single document (find_one())"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# GOVERNOR PROFILE

@governor_bp.route("/", methods=["GET"])
def get_governor():
    try:
        db = get_db()
        profile = db.county_leaders.find_one({})
        if not profile:
                    return jsonify({"error": "Governor profile not found"}), 404
        
        full_profile = serializable_single(profile)

        return jsonify(full_profile), 200
    
    except Exception as e:
        return jsonify({"error": "Failed to retrieve governor profile", "details": str(e)}), 500

# get county finances
@governor_bp.route("/finances", methods=["GET"])
def get_finances():
    try:
        db = get_db()
        year = request.args.get("year")
        query = {}
        if year:
            query["financial_year"] = year
        data = list(db.county_finances.find(query))
        full_data = serializable_doc(data)
        return jsonify(full_data), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve finances", "details": str(e)}), 500

# get departments data
@governor_bp.route("/departments", methods=["GET"])
def get_departments():
    try:
        db = get_db()
        data = list(db.department_absorption.find({}))
        full_data = serializable_doc(data)
        return jsonify(full_data), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve departments", "details": str(e)}), 500

# get county audit findings
@governor_bp.route("/audit", methods=["GET"])
def get_audit():
    try:
        db = get_db()
        data = list(db.county_audit_findings.find({}))
        full_data = serializable_doc(data)
        return jsonify(full_data), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve audit findings", "details": str(e)}), 500

# scoring model
def calculate_score(finance, audit, department):
    # 1. Absorption: average across departments (already 0-100 scale each)
    absorption_rates = [d.get("absorption_rate", 0) for d in department]
    avg_absorption = sum(absorption_rates) / len(absorption_rates) if absorption_rates else 0

    # 2. Audit penalty: total misappropriated amount as a % of total revenue collected,
    #    then subtracted from 100 (capped so a single huge finding can't go negative)
    total_flagged_kshm = sum(
        a.get("amount_flagged_kshm", 0)
        for a in audit
        if a.get("finding_type") == "misappropriation"
    )

    # finance amounts are in KSh billions; convert to millions for a like-for-like comparison
    total_revenue_kshm = sum(f.get("amount_kshb", 0) for f in finance) * 1000
    flagged_ratio = (total_flagged_kshm / total_revenue_kshm) if total_revenue_kshm else 0
    audit_score = max(0, 100 - (flagged_ratio * 100))

    # 3. Combine with weights that sum to 1.0, then clamp to 0-100
    score = (0.6 * avg_absorption) + (0.4 * audit_score)
    score = max(0, min(100, score))

    return round(score, 2)

@governor_bp.route("/score", methods=["GET"])
def get_score():
    try:
        db = get_db()
        finance = list(db.county_finances.find({}, {"_id": 0}))
        audit = list(db.county_audit_findings.find({}, {"_id": 0}))
        department = list(db.department_absorption.find({}, {"_id": 0}))

        score = calculate_score(finance, audit, department)
        return jsonify({
            "score": score,
            "generated_at": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to calculate score", "details": str(e)}), 500