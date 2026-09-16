import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime
from flask_cors import CORS
from flask_jwt_extended import JWTManager


# api blueprints

from api.auth import auth_bp
from api.constituency import constituency_bp
from api.governors import governor_bp
from api.ai_engine import ai_bp

def create_app() -> Flask:
    app = Flask(__name__)
    # Cors facilitates api fetches between flask and the frontend

    CORS(app)

    #  Configurations for jwt token manager, mongo database, locally installed ollama and qwen ai model
    app.config["JWT_SECRET_KEY"]          = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False   # long-lived for demo; tighten in prod
    app.config["MONGODB_URI"]             = os.getenv("MONGODB_URI", "mongodb://localhost:27017/Accountability")
    app.config["OLLAMA_HOST"]             = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    app.config["OLLAMA_MODEL"]            = os.getenv("OLLAMA_MODEL", "qwen")

    #  Extensions
    JWTManager(app)

    #  Blueprints
    app.register_blueprint(auth_bp,     url_prefix="/api/auth")
    app.register_blueprint(governor_bp,    url_prefix="/api/governor")
    app.register_blueprint(constituency_bp, url_prefix="/api/constituency")
    app.register_blueprint(ai_bp,        url_prefix="/api/ai")

    #  Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "internal server error", "detail": str(e)}), 500

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "Accountability"})


    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)