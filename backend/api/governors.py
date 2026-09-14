from flask import Blueprint, jsonify, request
from api.utils.utils import get_db
from datetime import datetime

governor_bp = Blueprint("governor", __name__)


# =========================
# GOVERNOR PROFILE
# =========================
@governor_bp.route("/governor", methods=["GET"])
def get_governor():
    db = get_db()

    profile = db.governor.find({}, {"_id": 0})

    return jsonify(list(profile))


# =========================
# COUNTY FINANCES
# =========================
@governor_bp.route("/governor/finances", methods=["GET"])
def get_finances():
    db = get_db()

    year = request.args.get("year")

    query = {}
    if year:
        query["financial_year"] = year

    data = list(db.county_finances.find(query, {"_id": 0}))

    return jsonify(data)


# =========================
# DEPARTMENTS DATA
# =========================
@governor_bp.route("/governor/departments", methods=["GET"])
def get_departments():
    db = get_db()

    data = list(db.department_absorption.find({}, {"_id": 0}))

    return jsonify(data)


# =========================
# AUDIT FINDINGS
# =========================
@governor_bp.route("/governor/audit", methods=["GET"])
def get_audit():
    db = get_db()

    data = list(db.county_audit_findings.find({}, {"_id": 0}))

    return jsonify(data)


# =========================
# SCORING FUNCTION
# =========================
def calculate_score(finance, audit, department):
    score = 0

    # Penalize misappropriation
    for a in audit:
        if a.get("finding_type") == "misappropriation":
            score -= a.get("amount_flagged_kshm", 0)

    # Reward budget absorption
    for d in department:
        score += d.get("absorption_rate", 0)

    # Reward revenue collection
    for f in finance:
        score += f.get("amount_kshb", 0) / 1000  # scale

    return round(score, 2)


# =========================
# GOVERNOR SCORE
# =========================
@governor_bp.route("/governor/score", methods=["GET"])
def get_score():
    db = get_db()

    finance = list(db.county_finances.find({}, {"_id": 0}))
    audit = list(db.county_audit_findings.find({}, {"_id": 0}))
    department = list(db.department_absorption.find({}, {"_id": 0}))

    score = calculate_score(finance, audit, department)

    return jsonify({
        "score": score,
        "generated_at": datetime.now().isoformat()
    })