from flask import Flask, Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required, create_access_token

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin", methods=["POST"])
#def admin_analysis():
    