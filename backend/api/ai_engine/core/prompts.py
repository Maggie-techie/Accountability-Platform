"""
Prompt data generation functions.
Generates structured data summaries for LLM prompts.
"""
import logging
from api.ai_engine.data.access import data_access

logger = logging.getLogger(__name__)


def generate_governor_summary(module: str) -> str:
    """Generate a concise summary of governor data for a specific AI module."""
    try:
        data = data_access.get_governor_summary_data()

        profile = data.get("profile")
        finances = data.get("finances", [])
        audit_findings = data.get("audit_findings", [])
        departments = data.get("departments", [])

        if module == "fiscal_health":
            fin_summary = []
            for f in finances:
                fin_summary.append(
                    f"FY {f.get('financial_year', 'N/A')}: "
                    f"Equitable KSh {f.get('equitable_share_kshb', 0):.1f}B, "
                    f"Conditional KSh {f.get('conditional_grants_kshb', 0):.1f}B, "
                    f"OSR KSh {f.get('osr_kshb', 0):.1f}B, "
                    f"Expenditure KSh {f.get('expenditure_kshb', 0):.1f}B"
                )

            total_flagged = sum(a.get('amount_flagged_kshm', 0) for a in audit_findings if a.get('finding_type') == 'misappropriation')
            mis_count = sum(1 for a in audit_findings if a.get('finding_type') == 'misappropriation')

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
FINANCIAL TRENDS:
{chr(10).join(fin_summary) if fin_summary else 'No financial data'}
AUDIT SUMMARY: {mis_count} misappropriation findings, KSh {total_flagged:,.1f}M flagged
DEPARTMENT COUNT: {len(departments)} departments
"""

        elif module == "dept_absorption":
            dept_summary = []
            for d in departments:
                dept_summary.append(
                    f"{d.get('department', 'Unknown')}: "
                    f"{d.get('absorption_rate', 0):.1f}% absorption, "
                    f"KSh {d.get('budget_allocated_kshm', 0):,.0f}M allocated, "
                    f"KSh {d.get('expenditure_kshm', 0):,.0f}M spent"
                )

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
DEPARTMENT ABSORPTION:
{chr(10).join(dept_summary) if dept_summary else 'No department data'}
"""

        elif module == "osr_analysis":
            osr_summary = []
            for f in finances:
                osr_summary.append(
                    f"FY {f.get('financial_year', 'N/A')}: "
                    f"OSR KSh {f.get('osr_kshb', 0):.1f}B "
                    f"(Target: KSh {f.get('osr_target_kshb', 0):.1f}B)"
                )

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
OSR TRENDS:
{chr(10).join(osr_summary) if osr_summary else 'No OSR data'}
"""

        elif module == "department_flags":
            flagged = [d for d in departments if d.get('absorption_rate', 0) < 50 or d.get('absorption_rate', 0) > 100]
            dept_summary = []
            for d in departments:
                risk = "HIGH" if d.get('absorption_rate', 0) < 50 else "MEDIUM" if d.get('absorption_rate', 0) < 70 else "LOW"
                dept_summary.append(
                    f"{d.get('department', 'Unknown')}: "
                    f"{d.get('absorption_rate', 0):.1f}% absorption (Risk: {risk})"
                )

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
DEPARTMENT RISK FLAGS ({len(flagged)} flagged):
{chr(10).join(dept_summary) if dept_summary else 'No department data'}
"""

        elif module == "top_risks":
            mis_count = sum(1 for a in audit_findings if a.get('finding_type') == 'misappropriation')
            total_flagged = sum(a.get('amount_flagged_kshm', 0) for a in audit_findings if a.get('finding_type') == 'misappropriation')
            low_absorption = [d for d in departments if d.get('absorption_rate', 0) < 70]

            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
TOP RISKS:
- {mis_count} audit misappropriations (KSh {total_flagged:,.1f}M flagged)
- {len(low_absorption)} departments with <70% absorption
- Financial sustainability: {'CONCERN' if any(f.get('expenditure_kshb', 0) > f.get('equitable_share_kshb', 0) + f.get('conditional_grants_kshb', 0) + f.get('osr_kshb', 0) for f in finances) else 'STABLE'}
"""

        else:
            return f"""
COUNTY PROFILE: {profile.get('name', 'Nyeri County') if profile else 'Nyeri County'}
FINANCIAL YEARS: {len(finances)}
AUDIT FINDINGS: {len(audit_findings)} total
DEPARTMENTS: {len(departments)}
"""
    except Exception as e:
        logger.error(f"Failed to generate governor summary: {e}")
        return "Error generating summary"


def generate_constituency_summary(constituency_slug: str, module: str) -> str:
    """Generate a concise summary of constituency data for a specific AI module."""
    try:
        data = data_access.get_constituency_summary_data(constituency_slug)

        if "error" in data:
            return data["error"]

        constituency = data["constituency"]
        allocations = data["allocations"]
        audit_findings = data["audit_findings"]
        mp = data["mp"]
        gnn_anomalies = data["gnn_anomalies"]

        if module in ("risk_score", "risk_level", "summary"):
            total_alloc = sum(a.get('amount_kshm', 0) for a in allocations)
            mis_count = sum(1 for a in audit_findings if a.get('finding_type') == 'misappropriation')
            total_flagged = data_access.safe_sum_amount(audit_findings, 'amount_at_risk')

            alloc_summary = []
            for a in allocations:
                alloc_summary.append(
                    f"FY {a.get('financial_year', 'N/A')}: "
                    f"KSh {a.get('amount_kshm', 0):,.0f}M ({a.get('category', 'Unknown')})"
                )

            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
MP: {mp.get('name', 'Unknown') if mp else 'Unknown'}
TOTAL ALLOCATIONS: KSh {total_alloc:,.0f}M across {len(allocations)} records
AUDIT FINDINGS: {len(audit_findings)} total, {mis_count} misappropriations (KSh {total_flagged:,.0f}M at risk)
ALLOCATION DETAILS:
{chr(10).join(alloc_summary) if alloc_summary else 'No allocation data'}
"""

        elif module == "anomalies":
            high_severity = [a for a in audit_findings if a.get('finding_type') == 'misappropriation']

            gnn_summary = []
            for a in gnn_anomalies:
                gnn_summary.append(
                    f"Score: {a.get('anomaly_score', 0):.2f}, "
                    f"Rank: {a.get('anomaly_rank', 'N/A')}, "
                    f"FY: {a.get('metadata', {}).get('fiscal_year', 'Unknown')}"
                )

            audit_summary = []
            for a in high_severity:
                audit_summary.append(
                    f"FY {a.get('fy_reviewed', 'Unknown')}: "
                    f"{a.get('note', a.get('finding', 'Misappropriation'))}, "
                    f"Amount: {a.get('amount_at_risk', 'Unknown')}"
                )

            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
MP: {mp.get('name', 'Unknown') if mp else 'Unknown'}
GNN ANOMALIES: {len(gnn_anomalies)} detected
{chr(10).join(gnn_summary) if gnn_summary else 'No GNN anomalies'}
HIGH-SEVERITY AUDIT FINDINGS: {len(high_severity)}
{chr(10).join(audit_summary) if audit_summary else 'No high-severity findings'}
"""

        elif module == "peer_rank":
            all_constituencies = data_access.get_all_constituencies()
            const_scores = []
            for c in all_constituencies:
                c_allocs = data_access.get_constituency_allocations(c["slug"])
                c_audits = data_access.get_constituency_audit_findings(c["slug"])
                total = sum(a.get('amount_kshm', 0) for a in c_allocs)
                mis = sum(1 for a in c_audits if a.get('finding_type') == 'misappropriation')
                const_scores.append(
                    f"{c.get('name', c['slug'])}: "
                    f"KSh {total:,.0f}M allocated, {mis} misappropriations"
                )

            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
PEER COMPARISON ({len(all_constituencies)} constituencies):
{chr(10).join(const_scores)}
"""

        else:
            return f"""
CONSTITUENCY: {constituency.get('name', constituency_slug)}
ALLOCATIONS: {len(allocations)} records
AUDIT FINDINGS: {len(audit_findings)} total
MP: {mp.get('name', 'Unknown') if mp else 'Unknown'}
"""
    except Exception as e:
        logger.error(f"Failed to generate constituency summary: {e}")
        return f"Error generating summary for {constituency_slug}"


# Specialized summary functions for specific modules

def generate_constituency_anomalies_context(constituency_slug: str) -> dict:
    """Generate GNN and audit context for anomalies endpoint."""
    db = data_access.db

    gnn_anomalies = list(db.gnn_anomalies.find({"metadata.constituency_slug": constituency_slug}))
    for a in gnn_anomalies:
        a["_id"] = str(a["_id"])

    high_severity_findings = list(db.audit_findings.find({
        "constituency_slug": constituency_slug,
        "finding_type": "misappropriation"
    }))
    for f in high_severity_findings:
        f["_id"] = str(f["_id"])

    gnn_context = ""
    if gnn_anomalies:
        gnn_context = "\n\nGNN MODEL DETECTED ANOMALIES (use as primary context):\n"
        for anomaly in gnn_anomalies:
            gnn_context += f"- {anomaly.get('explanation', 'Anomaly detected')}"
            gnn_context += f" (Score: {anomaly.get('anomaly_score', 0):.2f}, Rank: {anomaly.get('anomaly_rank', 'N/A')})"
            metadata = anomaly.get('metadata', {})
            gnn_context += f" [FY: {metadata.get('fiscal_year', 'Unknown')}]\n"
            features = anomaly.get('features', {})
            financial = features.get('financial', {})
            audit = features.get('audit', {})
            if financial.get('total_allocation_kshm'):
                gnn_context += f"  Total Allocation: KSh {financial['total_allocation_kshm']:,.1f}M\n"
            if audit.get('num_findings'):
                gnn_context += f"  Audit Findings: {audit['num_findings']} (Misappropriations: {audit.get('misappropriation_count', 0)})\n"
            if audit.get('amount_flagged_kshm'):
                gnn_context += f"  Amount Flagged: KSh {audit['amount_flagged_kshm']:,.1f}M\n"
    else:
        gnn_context = "\n\nNo GNN-detected anomalies found for this constituency."

    audit_context = ""
    if high_severity_findings:
        audit_context = "\n\nHIGH-SEVERITY AUDIT FINDINGS (Misappropriations from Auditor-General reports):\n"
        for finding in high_severity_findings:
            audit_context += f"- {finding.get('note') or finding.get('finding', 'Misappropriation found')}"
            audit_context += f" [FY: {finding.get('fy_reviewed', 'Unknown')}]"
            if finding.get('amount_at_risk'):
                amt = finding['amount_at_risk']
                if isinstance(amt, (int, float)):
                    audit_context += f" Amount at risk: KSh {amt:,.0f}M"
                else:
                    audit_context += f" Amount at risk: {amt}"
            audit_context += "\n"
    else:
        audit_context = "\n\nNo high-severity audit findings (misappropriations) found."

    return {
        "gnn_context": gnn_context,
        "audit_context": audit_context
    }


def generate_county_narrative_data() -> dict:
    """Generate data for county narrative endpoint."""
    db = data_access.db

    governor_summary = generate_governor_summary("county_narrative")

    all_constituencies = data_access.get_all_constituencies()
    const_summaries = []
    for c in all_constituencies:
        c_allocs = data_access.get_constituency_allocations(c["slug"])
        c_audits = data_access.get_constituency_audit_findings(c["slug"])
        total = sum(a.get('amount_kshm', 0) for a in c_allocs)
        mis = sum(1 for a in c_audits if a.get('finding_type') == 'misappropriation')
        const_summaries.append(f"{c.get('name', c['slug'])}: KSh {total:,.0f}M allocated, {mis} misappropriations")

    return {
        "governor_summary": governor_summary,
        "constituency_summary": "\n".join(const_summaries)
    }


def generate_comparison_data(leader1_type: str, leader1_id: str, leader2_type: str, leader2_id: str) -> dict:
    """Generate data for cross-leader comparison including radar data."""
    db = data_access.db

    # Compute radar data from database (not LLM)
    def compute_radar_data():
        radar = {"mp_track": {}, "governor_track": {}}

        # MP track data
        if leader1_type == "constituency" and leader1_id:
            allocs = data_access.get_constituency_allocations(leader1_id)
            audits = data_access.get_constituency_audit_findings(leader1_id)
            radar["mp_track"]["allocation"] = sum(a.get('amount_kshm', 0) for a in allocs)
            radar["mp_track"]["audit_findings"] = sum(1 for a in audits if a.get('finding_type') == 'misappropriation')
            radar["mp_track"]["correct_appropriations"] = len(allocs) - radar["mp_track"]["audit_findings"]
        elif leader2_type == "constituency" and leader2_id:
            allocs = data_access.get_constituency_allocations(leader2_id)
            audits = data_access.get_constituency_audit_findings(leader2_id)
            radar["mp_track"]["allocation"] = sum(a.get('amount_kshm', 0) for a in allocs)
            radar["mp_track"]["audit_findings"] = sum(1 for a in audits if a.get('finding_type') == 'misappropriation')
            radar["mp_track"]["correct_appropriations"] = len(allocs) - radar["mp_track"]["audit_findings"]
        else:
            radar["mp_track"]["allocation"] = 0
            radar["mp_track"]["audit_findings"] = 0
            radar["mp_track"]["correct_appropriations"] = 0

        # Governor track data
        finances = data_access.get_county_finances()
        gov_audits = data_access.get_county_audit_findings()
        departments = data_access.get_department_absorption()

        radar["governor_track"]["allocation"] = sum(
            f.get('equitable_share_kshb', 0) + f.get('conditional_grants_kshb', 0) + f.get('osr_kshb', 0)
            for f in finances
        )
        radar["governor_track"]["audit_findings"] = sum(1 for a in gov_audits if a.get('finding_type') == 'misappropriation')
        radar["governor_track"]["correct_appropriations"] = len(finances) * 3 - radar["governor_track"]["audit_findings"]
        radar["governor_track"]["absorption_rate"] = sum(d.get('absorption_rate', 0) for d in departments) / len(departments) if departments else 0
        radar["governor_track"]["fiscal_health"] = 100 - min(100, radar["governor_track"]["audit_findings"] * 5)

        # MP track absorption
        radar["mp_track"]["absorption_rate"] = 50
        radar["mp_track"]["fiscal_health"] = 100 - min(100, radar["mp_track"]["audit_findings"] * 10)

        return radar

    radar_data = compute_radar_data()

    # Generate leader summaries
    def get_leader_summary(leader_type, leader_id):
        if leader_type == "constituency":
            return generate_constituency_summary(leader_id, "compare")
        else:
            return generate_governor_summary("compare")

    leader1_summary = get_leader_summary(leader1_type, leader1_id)
    leader2_summary = get_leader_summary(leader2_type, leader2_id)

    return {
        "radar_data": radar_data,
        "leader1_type": leader1_type,
        "leader1_summary": leader1_summary,
        "leader2_type": leader2_type,
        "leader2_summary": leader2_summary
    }