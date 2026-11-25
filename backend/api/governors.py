from flask import Blueprint, jsonify, request
from api.database.connection import get_db
from datetime import datetime
from api.cache_middleware import cached, invalidate_on_write, clear_cache
from bson import ObjectId
import logging

governor_bp = Blueprint("governor", __name__)
logger = logging.getLogger(__name__)


# creating a function for converting objectid to string
def serializable_doc(data):
    for doc in data:
        doc["_id"] = str(doc["_id"])
    return data

def serializable_single(doc):
    """For a single document (find_one())"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# GOVERNOR PROFILE - cached for 10 minutes, auto-invalidated on writes
@governor_bp.route("/", methods=["GET"])
@cached(ttl=600, key_prefix="governor")
def get_governor():
    try:
        db = get_db()
        profile = db.county_leaders.find_one({})
        if not profile:
                    return jsonify({"error": "Governor profile not found"}), 404
        
        full_profile = serializable_single(profile)

        return jsonify(full_profile), 200
    
    except Exception as e:
        return jsonify({"error": "Failed to retrieve governor profile", "details": str(e)}), 500

# get county finances - cached for 10 minutes
@governor_bp.route("/finances", methods=["GET"])
@cached(ttl=600, key_prefix="governor:finances")
def get_finances():
    try:
        db = get_db()
        year = request.args.get("year")
        query = {}
        if year:
            query["financial_year"] = year

        # Get raw financial data
        raw_data = list(db.county_finances.find(query))

        # Pivot data by financial_year to match frontend expectations
        # Database has rows with revenue_source + amount_kshb
        # Frontend expects one document per FY with: equitable_share_kshb, conditional_grants_kshb, osr_kshb, expenditure_kshb
        pivoted = {}
        for row in raw_data:
            fy = row.get("financial_year", "Unknown")
            if fy not in pivoted:
                pivoted[fy] = {
                    "financial_year": fy,
                    "equitable_share_kshb": 0,
                    "conditional_grants_kshb": 0,
                    "osr_kshb": 0,
                    "expenditure_kshb": 0,
                    "development_kshb": 0,
                    "recurrent_kshb": 0,
                    "osr_target_kshb": 0,
                    "county": row.get("county", "Nyeri"),
                    "county_code": row.get("county_code", "019"),
                    "governor": row.get("governor", "")
                }

            source = row.get("revenue_source", "").lower()
            amount = row.get("amount_kshb", 0)

            # Map revenue_source to expected fields
            if "equitable" in source:
                pivoted[fy]["equitable_share_kshb"] = amount
            elif "conditional" in source:
                pivoted[fy]["conditional_grants_kshb"] = amount
            elif "own source" in source or "osr" in source:
                pivoted[fy]["osr_kshb"] = amount
            elif "expenditure" in source or "total" in source:
                pivoted[fy]["expenditure_kshb"] = amount
            elif "development" in source:
                pivoted[fy]["development_kshb"] = amount
            elif "recurrent" in source:
                pivoted[fy]["recurrent_kshb"] = amount

        # Also copy other fields from raw data if present
        for row in raw_data:
            fy = row.get("financial_year", "Unknown")
            if fy in pivoted:
                # Copy any additional fields
                for key in ["development_kshb", "recurrent_kshb", "osr_target_kshb"]:
                    if key in row and row[key]:
                        pivoted[fy][key] = row[key]

        result = list(pivoted.values())
        # Sort by financial_year
        result.sort(key=lambda x: x.get("financial_year", ""))

        # No _id fields in pivoted data, return directly
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve finances", "details": str(e)}), 500

# get departments data - cached for 10 minutes
@governor_bp.route("/departments", methods=["GET"])
@cached(ttl=600, key_prefix="governor:departments")
def get_departments():
    try:
        db = get_db()
        data = list(db.department_absorption.find({}))
        full_data = serializable_doc(data)
        return jsonify(full_data), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve departments", "details": str(e)}), 500

# get county audit findings - cached for 5 minutes
@governor_bp.route("/audit", methods=["GET"])
@cached(ttl=300, key_prefix="governor:audit")
def get_audit():
    try:
        db = get_db()
        data = list(db.county_audit_findings.find({}))
        full_data = serializable_doc(data)
        return jsonify(full_data), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve audit findings", "details": str(e)}), 500

# scoring model
def calculate_score(finance, audit, department):
    # 1. Absorption: average across departments (already 0-100 scale each)
    absorption_rates = [d.get("absorption_rate", 0) for d in department]
    avg_absorption = sum(absorption_rates) / len(absorption_rates) if absorption_rates else 0

    # 2. Audit penalty: total misappropriated amount as a % of total revenue collected,
    #    then subtracted from 100 (capped so a single huge finding can't go negative)
    total_flagged_kshm = sum(
        a.get("amount_flagged_kshm", 0)
        for a in audit
        if a.get("finding_type") == "misappropriation"
    )

    # finance amounts are in KSh billions; convert to millions for a like-for-like comparison
    total_revenue_kshm = sum(f.get("amount_kshb", 0) for f in finance) * 1000
    flagged_ratio = (total_flagged_kshm / total_revenue_kshm) if total_revenue_kshm else 0
    audit_score = max(0, 100 - (flagged_ratio * 100))

    # 3. Combine with weights that sum to 1.0, then clamp to 0-100
    score = (0.6 * avg_absorption) + (0.4 * audit_score)
    score = max(0, min(100, score))

    return round(score, 2)

@governor_bp.route("/score", methods=["GET"])
@cached(ttl=600, key_prefix="governor:score")
def get_score():
    try:
        db = get_db()
        finance = list(db.county_finances.find({}, {"_id": 0}))
        audit = list(db.county_audit_findings.find({}, {"_id": 0}))
        department = list(db.department_absorption.find({}, {"_id": 0}))

        score = calculate_score(finance, audit, department)
        return jsonify({
            "score": score,
            "generated_at": datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({"error": "Failed to calculate score", "details": str(e)}), 500


# =============================================================================
# CRUD ENDPOINTS - Governor Profile
# =============================================================================

@governor_bp.route("/", methods=["POST"])
@invalidate_on_write(key_prefixes=["governor"])
def create_governor():
    """Create a new governor profile"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['name', 'county']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Check if governor profile already exists (assuming single governor)
        existing = db.county_leaders.find_one({})
        if existing:
            return jsonify({"error": "Governor profile already exists. Use PUT to update."}), 409

        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()

        result = db.county_leaders.insert_one(data)
        data['_id'] = str(result.inserted_id)

        logger.info(f"Created governor profile: {data['name']}")
        return jsonify(serialize_single(data)), 201

    except Exception as e:
        logger.error(f"Error creating governor profile: {e}")
        return jsonify({"error": "Failed to create governor profile", "details": str(e)}), 500


@governor_bp.route("/", methods=["PUT"])
@invalidate_on_write(key_prefixes=["governor"])
def update_governor():
    """Update the governor profile"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        data['updated_at'] = datetime.utcnow()

        result = db.county_leaders.update_one(
            {},
            {"$set": data}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Governor profile not found"}), 404

        updated = db.county_leaders.find_one({})
        logger.info("Updated governor profile")
        return jsonify(serialize_single(updated)), 200

    except Exception as e:
        logger.error(f"Error updating governor profile: {e}")
        return jsonify({"error": "Failed to update governor profile", "details": str(e)}), 500


@governor_bp.route("/", methods=["DELETE"])
@invalidate_on_write(key_prefixes=["governor"])
def delete_governor():
    """Delete the governor profile"""
    try:
        db = get_db()

        result = db.county_leaders.delete_one({})

        if result.deleted_count == 0:
            return jsonify({"error": "Governor profile not found"}), 404

        logger.info("Deleted governor profile")
        return jsonify({"message": "Governor profile deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting governor profile: {e}")
        return jsonify({"error": "Failed to delete governor profile", "details": str(e)}), 500


# =============================================================================
# CRUD ENDPOINTS - County Finances
# =============================================================================

@governor_bp.route("/finances", methods=["POST"])
@invalidate_on_write(key_prefixes=["governor:finances"])
def create_finance():
    """Create a new county finance record"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['financial_year', 'revenue_source', 'amount_kshb']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()

        result = db.county_finances.insert_one(data)
        data['_id'] = str(result.inserted_id)

        logger.info(f"Created finance record for {data['financial_year']} - {data['revenue_source']}")
        return jsonify(serialize_single(data)), 201

    except Exception as e:
        logger.error(f"Error creating finance record: {e}")
        return jsonify({"error": "Failed to create finance record", "details": str(e)}), 500


@governor_bp.route("/finances/<finance_id>", methods=["PUT"])
@invalidate_on_write(key_prefixes=["governor:finances"])
def update_finance(finance_id):
    """Update a county finance record"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        if '_id' in data:
            del data['_id']

        data['updated_at'] = datetime.utcnow()

        try:
            obj_id = ObjectId(finance_id)
        except:
            return jsonify({"error": "Invalid finance ID"}), 400

        result = db.county_finances.update_one(
            {"_id": obj_id},
            {"$set": data}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Finance record not found"}), 404

        updated = db.county_finances.find_one({"_id": obj_id})
        logger.info(f"Updated finance record: {finance_id}")
        return jsonify(serialize_single(updated)), 200

    except Exception as e:
        logger.error(f"Error updating finance record: {e}")
        return jsonify({"error": "Failed to update finance record", "details": str(e)}), 500


@governor_bp.route("/finances/<finance_id>", methods=["DELETE"])
@invalidate_on_write(key_prefixes=["governor:finances"])
def delete_finance(finance_id):
    """Delete a county finance record"""
    try:
        db = get_db()

        try:
            obj_id = ObjectId(finance_id)
        except:
            return jsonify({"error": "Invalid finance ID"}), 400

        result = db.county_finances.delete_one({"_id": obj_id})

        if result.deleted_count == 0:
            return jsonify({"error": "Finance record not found"}), 404

        logger.info(f"Deleted finance record: {finance_id}")
        return jsonify({"message": "Finance record deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting finance record: {e}")
        return jsonify({"error": "Failed to delete finance record", "details": str(e)}), 500


# =============================================================================
# CRUD ENDPOINTS - Departments
# =============================================================================

@governor_bp.route("/departments", methods=["POST"])
@invalidate_on_write(key_prefixes=["governor:departments"])
def create_department():
    """Create a new department record"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['department', 'financial_year', 'approved_budget_kshm', 'absorption_rate']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()

        result = db.department_absorption.insert_one(data)
        data['_id'] = str(result.inserted_id)

        logger.info(f"Created department record: {data['department']} for {data['financial_year']}")
        return jsonify(serialize_single(data)), 201

    except Exception as e:
        logger.error(f"Error creating department record: {e}")
        return jsonify({"error": "Failed to create department record", "details": str(e)}), 500


@governor_bp.route("/departments/<dept_id>", methods=["PUT"])
@invalidate_on_write(key_prefixes=["governor:departments"])
def update_department(dept_id):
    """Update a department record"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        if '_id' in data:
            del data['_id']

        data['updated_at'] = datetime.utcnow()

        try:
            obj_id = ObjectId(dept_id)
        except:
            return jsonify({"error": "Invalid department ID"}), 400

        result = db.department_absorption.update_one(
            {"_id": obj_id},
            {"$set": data}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Department record not found"}), 404

        updated = db.department_absorption.find_one({"_id": obj_id})
        logger.info(f"Updated department record: {dept_id}")
        return jsonify(serialize_single(updated)), 200

    except Exception as e:
        logger.error(f"Error updating department record: {e}")
        return jsonify({"error": "Failed to update department record", "details": str(e)}), 500


@governor_bp.route("/departments/<dept_id>", methods=["DELETE"])
@invalidate_on_write(key_prefixes=["governor:departments"])
def delete_department(dept_id):
    """Delete a department record"""
    try:
        db = get_db()

        try:
            obj_id = ObjectId(dept_id)
        except:
            return jsonify({"error": "Invalid department ID"}), 400

        result = db.department_absorption.delete_one({"_id": obj_id})

        if result.deleted_count == 0:
            return jsonify({"error": "Department record not found"}), 404

        logger.info(f"Deleted department record: {dept_id}")
        return jsonify({"message": "Department record deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting department record: {e}")
        return jsonify({"error": "Failed to delete department record", "details": str(e)}), 500


# =============================================================================
# CRUD ENDPOINTS - County Audit Findings
# =============================================================================

@governor_bp.route("/audit", methods=["POST"])
@invalidate_on_write(key_prefixes=["governor:audit"])
def create_audit_finding():
    """Create a new county audit finding"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['entity', 'category', 'finding_type', 'fy_display']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        data['created_at'] = datetime.utcnow()
        data['updated_at'] = datetime.utcnow()

        result = db.county_audit_findings.insert_one(data)
        data['_id'] = str(result.inserted_id)

        logger.info(f"Created county audit finding: {data['entity']} - {data['category']}")
        return jsonify(serialize_single(data)), 201

    except Exception as e:
        logger.error(f"Error creating audit finding: {e}")
        return jsonify({"error": "Failed to create audit finding", "details": str(e)}), 500


@governor_bp.route("/audit/<audit_id>", methods=["PUT"])
@invalidate_on_write(key_prefixes=["governor:audit"])
def update_audit_finding(audit_id):
    """Update a county audit finding"""
    try:
        db = get_db()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        if '_id' in data:
            del data['_id']

        data['updated_at'] = datetime.utcnow()

        try:
            obj_id = ObjectId(audit_id)
        except:
            return jsonify({"error": "Invalid audit finding ID"}), 400

        result = db.county_audit_findings.update_one(
            {"_id": obj_id},
            {"$set": data}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Audit finding not found"}), 404

        updated = db.county_audit_findings.find_one({"_id": obj_id})
        logger.info(f"Updated county audit finding: {audit_id}")
        return jsonify(serialize_single(updated)), 200

    except Exception as e:
        logger.error(f"Error updating audit finding: {e}")
        return jsonify({"error": "Failed to update audit finding", "details": str(e)}), 500


@governor_bp.route("/audit/<audit_id>", methods=["DELETE"])
@invalidate_on_write(key_prefixes=["governor:audit"])
def delete_audit_finding(audit_id):
    """Delete a county audit finding"""
    try:
        db = get_db()

        try:
            obj_id = ObjectId(audit_id)
        except:
            return jsonify({"error": "Invalid audit finding ID"}), 400

        result = db.county_audit_findings.delete_one({"_id": obj_id})

        if result.deleted_count == 0:
            return jsonify({"error": "Audit finding not found"}), 404

        logger.info(f"Deleted county audit finding: {audit_id}")
        return jsonify({"message": "Audit finding deleted successfully"}), 200

    except Exception as e:
        logger.error(f"Error deleting audit finding: {e}")
        return jsonify({"error": "Failed to delete audit finding", "details": str(e)}), 500