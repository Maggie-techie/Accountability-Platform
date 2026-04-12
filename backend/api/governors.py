from flask import Flask,Blueprint, jsonify, request

from utils import get_db

governor_bp = Blueprint("governor", __name__)

# governors profile
@governor_bp.route("/governor", methods=["GET"])
def get_governor():
    

# get county finances
@governor_bp.route("/governor/finances", methods=["GET"])
def get_finances():
    year = request.args.get("year")
    query = {}
    if year:
        query["financial_year"] = year
    data = list(db.county_finances.find(query, {"_id": 0}))
    return jsonify(data)

# get departments data

@governor_bp.route("/governor/departments", methods=["GET"])
def get_departments():
    data = list(db.department_absorption.find({}, {"_id": 0}))
    return jsonify(data)



# get county audit findings
@governor_bp.route("/governor/audit", methods=["GET"])
def get_audit():
    data = list(db.county_audit_findings.find({}, {"_id": 0}))
    return jsonify(data)


# scoring model
def calculate_score(finance, audit, department):
    score = 0

    # Penalize misappropriation
    for a in audit:
        if a.get("finding_type") == "misappropriation":
            score -= a.get("amount_flagged_kshm", 0)

    # Reward high budget absorption
    for d in department:
        score += d.get("absorption_rate", 0)

    # Reward revenue collection
    for f in finance:
        score += f.get("amount_kshb", 0) / 1e3  # scale down

    return round(score, 2)

# get governor score

@governor_bp.route("/governor/score", methods=["GET"])
def get_score():
    finance = list(db.county_finances.find({}, {"_id": 0}))
    audit = list(db.county_audit_findings.find({}, {"_id": 0}))
    department = list(db.department_absorption.find({}, {"_id": 0}))

    score = calculate_score(finance, audit, department)
    return jsonify({
        "score": score,
        "generated_at": datetime.now().isoformat()
    })
