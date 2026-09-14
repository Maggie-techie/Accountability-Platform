from flask import Flask, Blueprint, request, jsonify
from api.utils.utils import get_db


constituency_bp = Blueprint("constituency", __name__)


@constituency_bp.route("/<slug>", methods=["GET"])
def get_constituency(slug):
    db = get_db
    constituency = db.constituency.find_one({"name":"slug"},
                                            {"_id"}: 0)
    
    if not constituency:
        return jsonify ({"error": f" {"slug"} constituency not found"}), 404
    
    return jsonify(constituency)
      

@constituency_bp.route("/<slug>/mp", methods=["GET"])
def get_mp(slug):
    db = get_db
    
    constituency = db.constituency.find_one({"slug": slug},
                                            {"_id":0, "mp":1, "name": 1, "slug": 1})
    if not constituency:
        return jsonify({"error": f"{slug} constituency not found"}), 404
    return jsonify(
        {"constituency": constituency["name"],
         "mp":constituency.get("mp", {})}
    )
    
    
@constituency_bp.route("/<slug>/finance", methods=["GET"])
def get_finance(slug):
    db = get_db()

    constituency = db.constituency.find_one(
        {"slug": slug},
        {"_id": 0}
    )

    if not constituency:
        return jsonify({"error": f"{slug} constituency not found"}), 404

    return jsonify({
        "constituency": constituency["name"],
        "county": constituency.get("county"),
        "county_code": constituency.get("county_code"),

        "allocations_ksm": constituency.get("allocations_ksm", {}),

        "correct_appropriations": constituency.get("correct_appropriations", []),

        "misappropriations": constituency.get("misappropriations", []),

        "financial_review": {
            "fy_reviewed": constituency.get("fy_reviewed"),
            "amount_at_risk": constituency.get("amount_at_risk"),
        },

        "audit": {
            "audit_status": constituency.get("audit_status"),
            "oag_opinion": constituency.get("oag_opinion")
        },

        "data_sources": constituency.get("data_sources", [])
    })
    
@constituency_bp.route("/<slug>/misappropriations", methods=["GET"])
def get_misappropriations(slug):
    db = get_db()

    constituency = db.constituency.find_one(
        {"slug": slug},
        {"_id": 0, "misappropriations": 1}
    )

    if not constituency:
        return jsonify({"error": f"{slug} constituency not found"}), 404

    return jsonify({
        "slug": slug,
        "misappropriations": constituency.get("misappropriations", [])
    })    
    