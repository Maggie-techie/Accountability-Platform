from flask import Blueprint, jsonify, request, send_file
from api.database.connection import get_db
import pandas as pd
import io
from datetime import datetime

reports_bp = Blueprint("reports", __name__)

def serializable_doc(data):
    """Convert ObjectId to string for JSON serialization in a list of documents"""
    for doc in data:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
    return data

def serializable_single(doc):
    """Convert ObjectId to string for a single document"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

@reports_bp.route("/governor/<governor_name>", methods=["GET"])
def generate_governor_report(governor_name):
    """
    Generate a report for a specific governor.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()

        # Get governor profile
        profile = db.county_leaders.find_one({"governor": governor_name})
        if not profile:
            return jsonify({"error": f"Governor {governor_name} not found"}), 404

        profile = serializable_single(profile)

        # Get financial data
        finances = list(db.county_finances.find({"governor": governor_name}))
        finances = serializable_doc(finances)

        # Get audit findings
        audit = list(db.county_audit_findings.find({"governor": governor_name}))
        audit = serializable_doc(audit)

        # Get department data (assuming it's not governor-specific, but we can filter if needed)
        department = list(db.department_absorption.find({}))
        department = serializable_doc(department)

        # Create a report dictionary
        report_data = {
            "governor_profile": profile,
            "financial_data": finances,
            "audit_findings": audit,
            "department_performance": department,
            "generated_at": datetime.now().isoformat()
        }

        # Convert to DataFrame for Excel/CSV
        # We'll create multiple sheets for Excel
        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Governor profile
                pd.DataFrame([profile]).to_excel(writer, sheet_name='Profile', index=False)

                # Financial data
                if finances:
                    pd.DataFrame(finances).to_excel(writer, sheet_name='Financials', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Financials', index=False)

                # Audit findings
                if audit:
                    pd.DataFrame(audit).to_excel(writer, sheet_name='Audit', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Audit', index=False)

                # Department performance
                if department:
                    pd.DataFrame(department).to_excel(writer, sheet_name='Departments', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Departments', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{governor_name}_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV format - we'll combine key data into one CSV or return JSON for now
            # For simplicity, we'll return JSON for CSV format request
            # In a real app, we might create a CSV with multiple sections
            return jsonify(report_data), 200

    except Exception as e:
        return jsonify({"error": "Failed to generate governor report", "details": str(e)}), 500

@reports_bp.route("/constituency/<constituency_slug>", methods=["GET"])
def generate_constituency_report(constituency_slug):
    """
    Generate a report for a specific constituency.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()

        # Get constituency info
        constituency = db.constituencies.find_one({"slug": constituency_slug})
        if not constituency:
            return jsonify({"error": f"Constituency {constituency_slug} not found"}), 404

        constituency = serializable_single(constituency)

        # Get MP info
        mp = db.mps.find_one({"constituency_slug": constituency_slug})
        if mp:
            mp = serializable_single(mp)

        # Get allocations
        allocations = list(db.allocations.find({"constituency_slug": constituency_slug}))
        allocations = serializable_doc(allocations)

        # Get audit findings
        audit = list(db.audit_findings.find({"constituency_slug": constituency_slug}))
        audit = serializable_doc(audit)

        # Create a report dictionary
        report_data = {
            "constituency_info": constituency,
            "mp_info": mp,
            "allocations": allocations,
            "audit_findings": audit,
            "generated_at": datetime.now().isoformat()
        }

        # Convert to Excel if requested
        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Constituency info
                pd.DataFrame([constituency]).to_excel(writer, sheet_name='Constituency', index=False)

                # MP info
                if mp:
                    pd.DataFrame([mp]).to_excel(writer, sheet_name='MP', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='MP', index=False)

                # Allocations
                if allocations:
                    pd.DataFrame(allocations).to_excel(writer, sheet_name='Allocations', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Allocations', index=False)

                # Audit findings
                if audit:
                    pd.DataFrame(audit).to_excel(writer, sheet_name='Audit', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Audit', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{constituency_slug}_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV format - return JSON for now
            return jsonify(report_data), 200

    except Exception as e:
        return jsonify({"error": "Failed to generate constituency report", "details": str(e)}), 500

@reports_bp.route("/audit/findings", methods=["GET"])
def generate_audit_findings_report():
    """
    Generate a report of audit findings.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    - leader_type: 'governor' or 'constituency' (optional)
    - constituency_slug: filter by constituency (for constituency findings)
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()
        leader_type = request.args.get('leader_type')
        constituency_slug = request.args.get('constituency_slug')

        # Build query
        query = {}
        if leader_type == "governor":
            query = {}  # We'll search in county_audit_findings
        elif leader_type == "constituency":
            query = {}
            if constituency_slug:
                query["constituency_slug"] = constituency_slug
            # We'll search in audit_findings
        else:
            # If no leader_type specified, we might want to search both? Let's default to both for now
            # But we need to handle different collections
            pass

        # For simplicity, let's get all audit findings from both collections if no filter
        # But we need to standardize the fields

        findings = []

        # Get governor audit findings
        if leader_type != "constituency":  # Include governor unless explicitly filtered out
            governor_findings = list(db.county_audit_findings.find({}))
            for f in governor_findings:
                f = serializable_single(f)
                findings.append({
                    "leader_type": "governor",
                    "leader_id": f.get("governor", ""),
                    "leader_name": f.get("governor", ""),
                    "county": f.get("county", ""),
                    "county_code": f.get("county_code", ""),
                    "financial_year": f.get("financial_year", ""),
                    "finding_type": f.get("finding_type", ""),
                    "amount_flagged_kshm": f.get("amount_flagged_kshm", 0),
                    "severity": f.get("severity", ""),
                    "misappropriation_notes": f.get("misappropriation_notes", ""),
                    "recommendation": f.get("recommendation", ""),
                    "note": ""
                })

        # Get constituency audit findings
        if leader_type != "governor":  # Include constituency unless explicitly filtered out
            constituency_query = {}
            if constituency_slug:
                constituency_query["constituency_slug"] = constituency_slug
            constituency_findings = list(db.audit_findings.find(constituency_query))
            for f in constituency_findings:
                f = serializable_single(f)
                findings.append({
                    "leader_type": "constituency",
                    "leader_id": f.get("constituency_slug", ""),
                    "leader_name": f.get("mp_name", ""),
                    "constituency": f.get("constituency", ""),
                    "county": f.get("county", ""),
                    "county_code": f.get("county_code", ""),
                    "financial_year": f.get("fy_reviewed", ""),
                    "finding_type": f.get("finding_type", ""),
                    "amount_flagged_kshm": 0,  # Constituency findings don't have this in seed data
                    "severity": "",
                    "misappropriation_notes": "",
                    "recommendation": "",
                    "note": f.get("note", ""),
                    "amount_at_risk": f.get("amount_at_risk", "")
                })

        if not findings:
            return jsonify({"message": "No audit findings found"}), 200

        # Convert to DataFrame
        df = pd.DataFrame(findings)

        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Audit Findings', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'audit_findings_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'audit_findings_report_{datetime.now().strftime("%Y%m%d")}.csv'
            )

    except Exception as e:
        return jsonify({"error": "Failed to generate audit findings report", "details": str(e)}), 500

@reports_bp.route("/financial/summary", methods=["GET"])
def generate_financial_summary_report():
    """
    Generate a financial summary report.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    - governor_name: filter by governor (optional)
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()
        governor_name = request.args.get('governor_name')

        # Build query for finances
        query = {}
        if governor_name:
            query["governor"] = governor_name

        # Get financial data
        finances = list(db.county_finances.find(query))
        finances = serializable_doc(finances)

        if not finances:
            return jsonify({"message": "No financial data found"}), 200

        # Convert to DataFrame
        df = pd.DataFrame(finances)

        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Financial Summary', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'financial_summary_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'financial_summary_report_{datetime.now().strftime("%Y%m%d")}.csv'
            )

    except Exception as e:
        return jsonify({"error": "Failed to generate financial summary report", "details": str(e)}), 500


@reports_bp.route("/", methods=["GET"])
def get_reports():
    """
    Get a list of available reports for display in the reports library.
    Returns report metadata in the format expected by the frontend.
    """
    try:
        db = get_db()

        # Get some sample data to create realistic report entries
        # We'll create a few report entries based on actual data in the database

        reports_list = []

        # Get the governor to create a governor report entry
        governor = db.county_leaders.find_one()
        if governor:
            reports_list.append({
                "id": str(governor.get("_id", "gov-001")),
                "title": f"{governor.get('name', 'Governor')} Accountability Report",
                "category": "Accountability Reports",
                "entity": f"{governor.get('county', 'Nyeri County')} County",
                "financialYear": "2024/25",  # We could get this from finances data
                "datePublished": datetime.now().strftime("%Y-%m-%d"),
                "reportType": "governor",
                "reportParams": {
                    "governor_name": governor.get('name', '')
                }
            })

        # Get a few constituencies to create constituency report entries
        constituencies = list(db.constituencies.find().limit(3))
        for i, constituency in enumerate(constituencies):
            reports_list.append({
                "id": f"const-{i+1:03d}",
                "title": f"{constituency.get('name', 'Constituency')} NG-CD Report",
                "category": "NG-CDF Reports",
                "entity": constituency.get('name', 'Unknown Constituency'),
                "financialYear": "2024/25",
                "datePublished": datetime.now().strftime("%Y-%m-%d"),
                "reportType": "constituency",
                "reportParams": {
                    "constituency_slug": constituency.get('slug', '')
                }
            })

        # Add an audit findings report
        reports_list.append({
            "id": "audit-001",
            "title": "County Audit Findings Report",
            "category": "Audit Reports",
            "entity": "Nyeri County",
            "financialYear": "2024/25",
            "datePublished": datetime.now().strftime("%Y-%m-%d"),
            "reportType": "audit_findings",
            "reportParams": {}
        })

        # Add a financial summary report
        reports_list.append({
            "id": "finance-001",
            "title": "County Financial Summary Report",
            "category": "Financial Reports",
            "entity": "Nyeri County",
            "financialYear": "2024/25",
            "datePublished": datetime.now().strftime("%Y-%m-%d"),
            "reportType": "financial_summary",
            "reportParams": {}
        })

        # If we didn't get any data from the database, provide a fallback
        if not reports_list:
            reports_list = [
                {
                    "id": "R-01",
                    "title": "Nyeri County Accountability Report FY2024/25",
                    "category": "Accountability Reports",
                    "entity": "Nyeri County",
                    "financialYear": "2024/25",
                    "datePublished": "2025-08-12"
                },
                {
                    "id": "R-02",
                    "title": "Mathira NG-CDF Audit Summary FY2023/24",
                    "category": "Auditor-General Reports",
                    "entity": "Mathira",
                    "financialYear": "2023/24",
                    "datePublished": "2024-11-03"
                }
            ]

        return jsonify({"reports": reports_list}), 200

    except Exception as e:
        print(f"Error in get_reports: {e}")
        # Fallback to mock-like data to avoid breaking the frontend
        fallback_reports = [
            {
                "id": "R-01",
                "title": "Nyeri County Accountability Report FY2024/25",
                "category": "Accountability Reports",
                "entity": "Nyeri County",
                "financialYear": "2024/25",
                "datePublished": "2025-08-12"
            },
            {
                "id": "R-02",
                "title": "Mathira NG-CDF Audit Summary FY2023/24",
                "category": "Auditor-General Reports",
                "entity": "Mathira",
                "financialYear": "2023/24",
                "datePublished": "2024-11-03"
            }
        ]
        return jsonify({"reports": fallback_reports}), 200