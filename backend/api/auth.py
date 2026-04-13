from flask import Flask, Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required, create_access_token

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    admin = body.get("admin_name").strip
    password = body.get("password").strip

    if not admin:
        return jsonify({"error": "admin is required"}), 400
    
    if password != 1234:
        return jsonify({"error": "invalid credentials"}), 401

    token = create_access_token(identity=admin)

    return jsonify({
        "access_token":   token,
        "admin": "admin",
        "name": "mangereti",
    })