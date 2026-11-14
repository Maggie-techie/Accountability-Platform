"""
Data Access Layer - abstracts MongoDB collections for AI modules.
Single source of truth for collection names and queries.
"""
import logging
from typing import Optional
from api.database.connection import get_db

logger = logging.getLogger(__name__)


class DataAccess:
    """Centralized data access for AI engine."""

    # Collection names - single source of truth
    COLLECTIONS = {
        "constituencies": "constituencies",
        "allocations": "allocations",
        "audit_findings": "audit_findings",
        "mps": "mps",
        "county_leaders": "county_leaders",
        "county_finances": "county_finances",
        "county_audit": "county_audit",
        "department_absorption": "department_absorption",
        "gnn_anomalies": "gnn_anomalies",
        "projects": "projects",
        "departments": "departments",
        "financial_data": "financial_data",
        "ai_cache": "ai_cache",
    }

    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = get_db()
        return self._db

    def collection(self, name: str):
        """Get a collection by logical name."""
        return self.db[self.COLLECTIONS[name]]

    # ============================================================
    # Constituency / MP Data
    # ============================================================

    def get_constituency(self, slug: str) -> Optional[dict]:
        """Get constituency by slug."""
        return self.collection("constituencies").find_one({"slug": slug})

    def get_all_constituencies(self, limit: int = 50) -> list:
        """Get all constituencies."""
        return list(self.collection("constituencies").find({}).limit(limit))

    def get_constituency_allocations(self, slug: str) -> list:
        """Get all allocations for a constituency."""
        return list(self.collection("allocations").find({"constituency_slug": slug}))

    def get_constituency_audit_findings(self, slug: str) -> list:
        """Get all audit findings for a constituency."""
        return list(self.collection("audit_findings").find({"constituency_slug": slug}))

    def get_mp(self, slug: str) -> Optional[dict]:
        """Get MP by constituency slug."""
        return self.collection("mps").find_one({"constituency_slug": slug})

    def get_gnn_anomalies(self, slug: str) -> list:
        """Get GNN anomalies for a constituency."""
        return list(self.collection("gnn_anomalies").find({"metadata.constituency_slug": slug}))

    def validate_constituency_exists(self, slug: str) -> bool:
        """Check if constituency exists."""
        return self.collection("constituencies").find_one({"slug": slug}, {"_id": 1}) is not None

    # ============================================================
    # Governor / County Data
    # ============================================================

    def get_governor_profile(self) -> Optional[dict]:
        """Get governor/county leader profile."""
        return self.collection("county_leaders").find_one({})

    def get_county_finances(self) -> list:
        """Get county financial data by year."""
        return list(self.collection("county_finances").find({}).sort("financial_year", 1))

    def get_county_audit_findings(self) -> list:
        """Get county audit findings."""
        return list(self.collection("county_audit").find({}))

    def get_department_absorption(self) -> list:
        """Get department absorption data."""
        return list(self.collection("department_absorption").find({}))

    # ============================================================
    # General / Search Data
    # ============================================================

    def get_projects(self, limit: int = 50) -> list:
        """Get projects."""
        return list(self.collection("projects").find({}).limit(limit))

    def get_departments(self, limit: int = 50) -> list:
        """Get departments."""
        return list(self.collection("departments").find({}).limit(limit))

    def get_financial_data(self) -> Optional[dict]:
        """Get general financial data."""
        return self.collection("financial_data").find_one({})

    def get_all_mps(self, limit: int = 50) -> list:
        """Get all MPs."""
        return list(self.collection("mps").find({}).limit(limit))

    # ============================================================
    # Aggregated Data for Prompts
    # ============================================================

    def get_constituency_summary_data(self, slug: str) -> dict:
        """Get all data needed for constituency summaries."""
        constituency = self.get_constituency(slug)
        if not constituency:
            return {"error": f"Constituency not found: {slug}"}

        allocations = self.get_constituency_allocations(slug)
        audit_findings = self.get_constituency_audit_findings(slug)
        mp = self.get_mp(slug)
        gnn_anomalies = self.get_gnn_anomalies(slug)

        return {
            "constituency": constituency,
            "allocations": allocations,
            "audit_findings": audit_findings,
            "mp": mp,
            "gnn_anomalies": gnn_anomalies
        }

    def get_governor_summary_data(self) -> dict:
        """Get all data needed for governor summaries."""
        return {
            "profile": self.get_governor_profile(),
            "finances": self.get_county_finances(),
            "audit_findings": self.get_county_audit_findings(),
            "departments": self.get_department_absorption()
        }

    # ============================================================
    # Safe Amount Parsing
    # ============================================================

    @staticmethod
    def safe_sum_amount(findings: list, field: str) -> float:
        """Safely sum amount field handling strings like 'KSh 5M'."""
        import re
        total = 0
        for f in findings:
            val = f.get(field, 0)
            if isinstance(val, (int, float)):
                total += val
            elif isinstance(val, str):
                try:
                    num = re.search(r'[\d,]+\.?\d*', val.replace(',', ''))
                    if num:
                        total += float(num.group())
                except (ValueError, AttributeError):
                    pass
        return total


# Singleton instance
data_access = DataAccess()