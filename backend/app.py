import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
from datetime import datetime
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
load_dotenv() 
# Load environment variables from .env file

# api blueprints
from api.general import general_bp
from api.reports import reports_bp

from api.auth import auth_bp
from api.constituency import constituency_bp
from api.governors import governor_bp
from api.ai_engine import ai_bp
import sys

# Add project root to sys.path dynamically
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def create_app() -> Flask:
    app = Flask(__name__)

    app.config["MONGODB_URI"] = os.getenv("MONGODB_URI")
    #  Configurations for jwt token manager, mongo database, locally installed ollama and qwen ai model
    # Configurations for JWT token manager, MongoDB database,
# locally installed Ollama and Qwen AI model
    app.config["JWT_SECRET_KEY"]          = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False
    app.config["MONGODB_URI"]             = os.getenv("MONGODB_URI")
    app.config["OLLAMA_HOST"]             = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    app.config["OLLAMA_MODEL"]            = os.getenv("OLLAMA_MODEL", "qwen")

    # Cors facilitates api fetches between flask and the frontend
    CORS(app)

    #  Extensions
    JWTManager(app)

    #  Blueprints
    app.register_blueprint(auth_bp,     url_prefix="/api/auth" )
    app.register_blueprint(governor_bp,    url_prefix="/api/governor")
    app.register_blueprint(constituency_bp, url_prefix="/api/constituency")
    app.register_blueprint(ai_bp,        url_prefix="/api/ai")
    app.register_blueprint(general_bp,    url_prefix="/api")
    app.register_blueprint(reports_bp,    url_prefix="/api/reports")

    #  Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "internal server error", "detail": str(e)}), 500

    @app.route("/")
    def root():
        return jsonify({"message": "Welcome to the Accountability API"})

    @app.route("/health")
    def health():
        mongodb_uri = os.getenv("MONGODB_URI", "MONGO_URI")
        mongodb_db = os.getenv("MONGODB_DB", "not_set")
        return jsonify({"status": "ok", "service": "Accountability"})


    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)