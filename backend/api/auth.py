from flask import Flask, Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity

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


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Get current authenticated user from JWT token"""
    try:
        admin_name = get_jwt_identity()

        # Also check if this admin exists in admin_users collection
        from api.database.connection import get_db
        db = get_db()

        admin_user = db.admin_users.find_one({"email": admin_name})

        return jsonify({
            "success": True,
            "data": {
                "email": admin_name,
                "name": admin_user.get("name", "Admin") if admin_user else "Admin",
                "status": admin_user.get("status", "Active") if admin_user else "Active"
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to get current user", "details": str(e)}), 500