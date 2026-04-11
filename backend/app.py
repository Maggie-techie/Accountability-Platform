from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# ----------------------------
# MongoDB Connection
# ----------------------------
client = MongoClient("mongodb://localhost:27017")
db = client["Accountability"]

# ----------------------------
# Root route (home)
# ----------------------------
@app.route("/", methods=["GET"])
def home():
    return "Flask API is running! Available endpoints: /api/governor, /api/finances, /api/audit, /api/departments, /api/score"

# ----------------------------
# Get Governor profile
# ----------------------------
@app.route("/api/governor", methods=["GET"])
def get_governor():
    governor = db.county_leaders.find_one({"role": "Governor"}, {"_id": 0})
    return jsonify(governor)

# ----------------------------
# Get County Finances
# ----------------------------
@app.route("/api/finances", methods=["GET"])
def get_finances():
    year = request.args.get("year")
    query = {}
    if year:
        query["financial_year"] = year
    data = list(db.county_finances.find(query, {"_id": 0}))
    return jsonify(data)

# ----------------------------
# Get Audit Findings
# ----------------------------
@app.route("/api/audit", methods=["GET"])
def get_audit():
    data = list(db.county_audit_findings.find({}, {"_id": 0}))
    return jsonify(data)

# ----------------------------
# Get Departments Data
# ----------------------------
@app.route("/api/departments", methods=["GET"])
def get_departments():
    data = list(db.department_absorption.find({}, {"_id": 0}))
    return jsonify(data)

# ----------------------------
# Scoring Model
# ----------------------------
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

# ----------------------------
# Get Governor Score
# ----------------------------
@app.route("/api/score", methods=["GET"])
def get_score():
    finance = list(db.county_finances.find({}, {"_id": 0}))
    audit = list(db.county_audit_findings.find({}, {"_id": 0}))
    department = list(db.department_absorption.find({}, {"_id": 0}))

    score = calculate_score(finance, audit, department)
    return jsonify({
        "score": score,
        "generated_at": datetime.now().isoformat()
    })

# ----------------------------
# Run the app
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)