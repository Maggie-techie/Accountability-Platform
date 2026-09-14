from flask import Flask, Blueprint, request, jsonify
from api.utils.utils import get_db

constituency_bp = Blueprint("constituency", __name__)

@constituency_bp.route("/", methods=["GET"])
def get_constituencies():
    """
    Get all constituencies with optional filtering
    Query parameters:
    - county: filter by county
    - audit_status: filter by audit status
    - page: page number for pagination (default: 1)
    - limit: number of items per page (default: 10)
    """
    try:
        db = get_db()

        # Build query from request parameters
        query = {}
        county = request.args.get('county')
        if county:
            query['county'] = county

        audit_status = request.args.get('audit_status')
        if audit_status:
            query['audit_status'] = audit_status

        # Pagination
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Execute query
        constituencies_cursor = db.constituencies.find(query).skip(skip).limit(limit)

        # Convert to list and handle ObjectId serialization
        constituencies = []
        for constituency in constituencies_cursor:
            # Convert ObjectId to string for JSON serialization
            constituency['_id'] = str(constituency['_id'])
            constituencies.append(constituency)

        # Get total count for pagination
        total_count = db.constituencies.count_documents(query)

        return jsonify({
            "constituencies": constituencies,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve constituencies", "details": str(e)}), 500

@constituency_bp.route("/<slug>", methods=["GET"])
def get_constituency_by_slug(slug):
    """
    Get a specific constituency by its slug
    """
    try:
        db = get_db()

        constituency = db.constituencies.find_one({"slug": slug})
        if not constituency:
            return jsonify({"error": "Constituency not found"}), 404

        # Convert ObjectId to string for JSON serialization
        constituency['_id'] = str(constituency['_id'])

        return jsonify(constituency), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve constituency", "details": str(e)}), 500

