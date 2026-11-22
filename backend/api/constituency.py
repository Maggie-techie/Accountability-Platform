from flask import Blueprint, request, jsonify
from api.database.connection import get_db
from datetime import datetime
from api.cache_middleware import cached, clear_cache

constituency_bp = Blueprint("constituency", __name__)


# Scoring model for constituencies/MPs
def calculate_constituency_score(allocations, audit_findings, mp_data=None):
    """
    Calculate accountability score for a constituency/MP.

    Factors:
    1. Allocation utilization (30% weight) - based on correct vs misappropriation ratio
    2. Audit findings severity (40% weight) - based on misappropriation findings and amounts
    3. OAG opinion & audit status (30% weight) - based on audit opinion and status
    """
    # 1. Allocation utilization score (0-100)
    # Ratio of correct appropriations to total findings
    total_findings = len(audit_findings)
    correct_findings = sum(
        1 for a in audit_findings
        if a.get("finding_type") == "correct_appropriation"
    )
    misappropriation_findings = sum(
        1 for a in audit_findings
        if a.get("finding_type") == "misappropriation"
    )

    if total_findings > 0:
        utilization_ratio = correct_findings / total_findings
        utilization_score = utilization_ratio * 100
    else:
        # No findings - neutral score
        utilization_score = 50

    # 2. Audit findings severity score (0-100)
    # Based on misappropriation count and amount at risk
    total_amount_at_risk = 0
    for a in audit_findings:
        if a.get("finding_type") == "misappropriation":
            # Try to parse amount_at_risk (could be string like "KSh 5M" or number)
            amount = a.get("amount_at_risk", 0)
            if isinstance(amount, str):
                import re
                num_match = re.search(r'[\d,]+\.?\d*', amount.replace(',', ''))
                if num_match:
                    amount = float(num_match.group())
                else:
                    amount = 0
            total_amount_at_risk += amount

    # Normalize: assume 100M at risk = score of 0, 0 at risk = score of 100
    # This is a simple linear scaling
    if misappropriation_findings > 0:
        audit_score = max(0, 100 - (total_amount_at_risk / 100 * 100))
    else:
        audit_score = 100

    # 3. OAG opinion & audit status score (0-100)
    opinion_scores = {
        "Unqualified": 90,
        "Unqualified*": 85,
        "Qualified": 60,
        "Adverse": 30,
        "Disclaimer": 20
    }
    status_scores = {
        "Clean": 90,
        "Concerning": 40,
        "Unknown": 50
    }

    oag_opinion = mp_data.get("oag_opinion", "") if mp_data else ""
    audit_status = mp_data.get("audit_status", "") if mp_data else ""

    opinion_score = opinion_scores.get(oag_opinion, 50)
    status_score = status_scores.get(audit_status, 50)

    oag_score = (opinion_score + status_score) / 2

    # 4. Combine with weights
    # 30% utilization, 40% audit, 30% OAG
    score = (0.3 * utilization_score) + (0.4 * audit_score) + (0.3 * oag_score)
    score = max(0, min(100, score))

    return round(score, 2)


@constituency_bp.route("/<slug>/score", methods=["GET"])
@cached(ttl=600, key_prefix="constituency_score")
def get_constituency_score(slug):
    """Get accountability score for a specific constituency."""
    try:
        db = get_db()

        # Verify constituency exists
        constituency = db.constituencies.find_one({"slug": slug})
        if not constituency:
            return jsonify({"error": "Constituency not found"}), 404

        # Get allocations
        allocations = list(db.allocations.find({"constituency_slug": slug}))

        # Get audit findings
        audit_findings = list(db.audit_findings.find({"constituency_slug": slug}))

        # Get MP data for OAG opinion and audit status
        mp_data = db.mps.find_one({"constituency_slug": slug})

        score = calculate_constituency_score(allocations, audit_findings, mp_data)

        return jsonify({
            "constituency": constituency["name"],
            "slug": slug,
            "score": score,
            "generated_at": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to calculate constituency score", "details": str(e)}), 500

# Constituency endpoints - cached for 10 minutes
@constituency_bp.route("/", methods=["GET"])
@cached(ttl=600, key_prefix="constituencies")
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
@cached(ttl=600, key_prefix="constituency")
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

# Allocations endpoints - cached for 10 minutes
@constituency_bp.route("/allocations", methods=["GET"])
@cached(ttl=600, key_prefix="allocations")
def get_allocations():
    """
    Get all allocation records with optional filtering
    Query parameters:
    - constituency_slug: filter by constituency slug
    - fy_key: filter by fiscal year key (e.g., FY2022_23)
    - page: page number for pagination (default: 1)
    - limit: number of items per page (default: 10)
    """
    try:
        db = get_db()

        # Build query from request parameters
        query = {}
        constituency_slug = request.args.get('constituency_slug')
        if constituency_slug:
            query['constituency_slug'] = constituency_slug

        fy_key = request.args.get('fy_key')
        if fy_key:
            query['fy_key'] = fy_key

        # Pagination
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Execute query
        allocations_cursor = db.allocations.find(query).skip(skip).limit(limit)

        # Convert to list and handle ObjectId serialization
        allocations = []
        for allocation in allocations_cursor:
            allocation['_id'] = str(allocation['_id'])
            allocations.append(allocation)

        # Get total count for pagination
        total_count = db.allocations.count_documents(query)

        return jsonify({
            "allocations": allocations,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve allocations", "details": str(e)}), 500

@constituency_bp.route("/allocations/<slug>", methods=["GET"])
@cached(ttl=600, key_prefix="allocations")
def get_allocations_by_constituency(slug):
    """
    Get allocation records for a specific constituency
    """
    try:
        db = get_db()

        # Execute query
        allocations_cursor = db.allocations.find({"constituency_slug": slug})

        # Convert to list and handle ObjectId serialization
        allocations = []
        for allocation in allocations_cursor:
            allocation['_id'] = str(allocation['_id'])
            allocations.append(allocation)

        return jsonify({
            "allocations": allocations,
            "count": len(allocations)
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve allocations for constituency", "details": str(e)}), 500

# Audit Findings endpoints - cached for 5 minutes
@constituency_bp.route("/audit", methods=["GET"])
@cached(ttl=300, key_prefix="audit_findings")
def get_audit_findings():
    """
    Get all audit findings with optional filtering
    Query parameters:
    - constituency_slug: filter by constituency slug
    - finding_type: filter by finding type (misappropriation/correct_appropriation)
    - page: page number for pagination (default: 1)
    - limit: number of items per page (default: 10)
    """
    try:
        db = get_db()

        # Build query from request parameters
        query = {}
        constituency_slug = request.args.get('constituency_slug')
        if constituency_slug:
            query['constituency_slug'] = constituency_slug

        finding_type = request.args.get('finding_type')
        if finding_type:
            query['finding_type'] = finding_type

        # Pagination
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Execute query
        findings_cursor = db.audit_findings.find(query).skip(skip).limit(limit)

        # Convert to list and handle ObjectId serialization
        findings = []
        for finding in findings_cursor:
            finding['_id'] = str(finding['_id'])
            findings.append(finding)

        # Get total count for pagination
        total_count = db.audit_findings.count_documents(query)

        return jsonify({
            "audit_findings": findings,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve audit findings", "details": str(e)}), 500

@constituency_bp.route("/audit/<slug>", methods=["GET"])
@cached(ttl=300, key_prefix="audit_findings")
def get_audit_findings_by_constituency(slug):
    """
    Get audit findings for a specific constituency
    """
    try:
        db = get_db()

        # Execute query
        findings_cursor = db.audit_findings.find({"constituency_slug": slug})

        # Convert to list and handle ObjectId serialization
        findings = []
        for finding in findings_cursor:
            finding['_id'] = str(finding['_id'])
            findings.append(finding)

        return jsonify({
            "audit_findings": findings,
            "count": len(findings)
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve audit findings for constituency", "details": str(e)}), 500

# MPs endpoints - cached for 10 minutes
@constituency_bp.route("/mps", methods=["GET"])
@cached(ttl=600, key_prefix="mps")
def get_mps():
    """
    get all MP records with optional filtering
    Query parameters:
    - constituency_slug: filter by constituency slug
    - oag_opinion: filter by OAG opinion
    - audit_status: filter by audit status
    - page: page number for pagination (default: 1)
    - limit: number of items per page (default: 10)
    """
    try:
        db = get_db()

        # Build query from request parameters
        query = {}
        constituency_slug = request.args.get('constituency_slug')
        if constituency_slug:
            query['constituency_slug'] = constituency_slug

        oag_opinion = request.args.get('oag_opinion')
        if oag_opinion:
            query['oag_opinion'] = oag_opinion

        audit_status = request.args.get('audit_status')
        if audit_status:
            query['audit_status'] = audit_status

        # Pagination
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        skip = (page - 1) * limit

        # Execute query
        mps_cursor = db.mps.find(query).skip(skip).limit(limit)

        # Convert to list and handle ObjectId serialization
        mps_list = []
        for mp in mps_cursor:
            mp['_id'] = str(mp['_id'])
            mps_list.append(mp)

        # Get total count for pagination
        total_count = db.mps.count_documents(query)

        return jsonify({
            "mps": mps_list,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve MPs", "details": str(e)}), 500

@constituency_bp.route("/mps/<slug>", methods=["GET"])
@cached(ttl=600, key_prefix="mp")
def get_mp_by_constituency(slug):
    """
    Get MP data for a specific constituency
    """
    try:
        db = get_db()

        mp = db.mps.find_one({"constituency_slug": slug})
        if not mp:
            return jsonify({"error": "MP not found for constituency"}), 404

        # Convert ObjectId to string for JSON serialization
        mp['_id'] = str(mp['_id'])

        return jsonify(mp), 200

    except Exception as e:
        return jsonify({"error": "Failed to retrieve MP for constituency", "details": str(e)}), 500

