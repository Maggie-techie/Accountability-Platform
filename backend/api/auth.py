from flask import Flask, Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required, create_access_token

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    admin_name = body.get("admin_name", "").strip()
    password = body.get("password", "").strip()

    if not admin_name:
        return jsonify({"error": "admin_name is required"}), 400

    if not password:
        return jsonify({"error": "password is required"}), 400

    # For demo purposes, using hardcoded password (should be moved to environment variable or database in production)
    if password != "1234":
        return jsonify({"error": "invalid credentials"}), 401

    token = create_access_token(identity=admin_name)

    return jsonify({
        "access_token":   token,
        "admin": admin_name,
        "name": "mangereti",
    })