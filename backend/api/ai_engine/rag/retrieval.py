"""
RAG Retrieval Module - keyword-based with optional semantic search support.
Retrieves relevant data from MongoDB based on query intent.
"""
import logging
import re
from typing import Optional
from api.ai_engine.data.access import data_access

logger = logging.getLogger(__name__)


# Keyword categories for intent detection
FINANCIAL_KEYWORDS = [
    'budget', 'allocation', 'expenditure', 'spending', 'revenue', 'osr',
    'absorption', 'financial', 'money', 'fund', 'cost', 'amount', 'kes',
    'billion', 'million', 'equitable share', 'conditional grant'
]

AUDIT_KEYWORDS = [
    'audit', 'finding', 'irregular', 'misappropriat', 'anomal', 'flag',
    'risk', 'query', 'issue', 'problem', 'misuse', 'fraud', 'corruption'
]

LEADER_KEYWORDS = [
    'governor', 'mp', 'member of parliament', 'leader', 'mutahi', 'kahiga',
    'mp ', 'constituency', 'ward', 'senator', 'mca', 'county assembly'
]

PROJECT_KEYWORDS = [
    'project', 'development', 'infrastructure', 'road', 'water', 'hospital',
    'school', 'construction', 'stall', 'complete', 'stalled', 'renovation'
]

CONSTITUENCY_KEYWORDS = [
    'constituenc', 'ward', 'subcounty', 'sub-county', 'nyeri', 'mathira',
    'tetu', 'kieni', 'mukurweini', 'othaya', 'kiawara', 'naromoru', 'mweiga'
]


def detect_intent(query: str, constituency_slug: str = None) -> dict:
    """
    Detect what data to retrieve based on query keywords.
    Returns dict of boolean flags for each data category.
    """
    query_lower = query.lower()

    needs_financial = any(kw in query_lower for kw in FINANCIAL_KEYWORDS)
    needs_audit = any(kw in query_lower for kw in AUDIT_KEYWORDS)
    needs_leader = any(kw in query_lower for kw in LEADER_KEYWORDS)
    needs_project = any(kw in query_lower for kw in PROJECT_KEYWORDS)
    needs_constituency = (
        any(kw in query_lower for kw in CONSTITUENCY_KEYWORDS) or
        constituency_slug is not None
    )

    # Default to broad retrieval if no specific keywords
    if not (needs_financial or needs_audit or needs_leader or needs_project or needs_constituency):
        needs_financial = needs_audit = needs_leader = needs_constituency = True

    return {
        "needs_financial": needs_financial,
        "needs_audit": needs_audit,
        "needs_leader": needs_leader,
        "needs_project": needs_project,
        "needs_constituency": needs_constituency
    }


def retrieve_relevant_data(
    query: str,
    constituency_slug: Optional[str] = None,
    intent: Optional[dict] = None
) -> dict:
    """
    Retrieve relevant data from MongoDB based on query intent.

    Args:
        query: User's question
        constituency_slug: Optional specific constituency
        intent: Pre-computed intent dict (optional, will detect if not provided)

    Returns:
        Dict with relevant data sections
    """
    if intent is None:
        intent = detect_intent(query, constituency_slug)

    data = {}

    try:
        # Governor/County data - needed for most queries
        if intent.get("needs_leader") or intent.get("needs_financial") or intent.get("needs_audit") or intent.get("needs_constituency"):
            governor = data_access.get_governor_profile()
            if governor:
                data['governor'] = governor

        # Constituency data
        if intent.get("needs_constituency"):
            if constituency_slug:
                constituency = data_access.get_constituency(constituency_slug)
                if constituency:
                    data['constituency'] = constituency
            else:
                # Get all constituencies for broad queries
                constituencies = data_access.get_all_constituencies(limit=8)
                if constituencies:
                    data['constituencies'] = constituencies

        # MP data
        if intent.get("needs_leader"):
            mps = data_access.get_all_mps(limit=8)
            if mps:
                data['mps'] = mps

        # Financial data
        if intent.get("needs_financial"):
            financial = data_access.get_financial_data()
            if financial:
                data['financial_data'] = financial

        # Audit findings
        if intent.get("needs_audit"):
            # Get from governor profile
            if data.get('governor', {}).get('audit_findings'):
                data['audit_findings'] = data['governor']['audit_findings'][:20]

            # Also get from audit_findings collection
            audit_findings = data_access.get_county_audit_findings()
            if audit_findings:
                additional = audit_findings[:10]
                data['audit_findings'] = (data.get('audit_findings', []) + additional)[:30]

        # Projects
        if intent.get("needs_project"):
            projects = data_access.get_projects(limit=15)
            if projects:
                data['projects'] = projects

        # Departments
        if intent.get("needs_financial") or intent.get("needs_leader"):
            depts = data_access.get_departments(limit=15)
            if depts:
                data['departments'] = depts

    except Exception as e:
        logger.error(f"Error retrieving data for RAG: {e}")

    return data


def format_context_for_prompt(retrieved_data: dict) -> str:
    """
    Format retrieved data as structured context for LLM prompt.
    """
    context_parts = []

    # Governor / County Executive
    if retrieved_data.get('governor'):
        gov = retrieved_data['governor']
        context_parts.append(
            f"=== GOVERNOR / COUNTY EXECUTIVE ===\n"
            f"Name: {gov.get('name', 'N/A')}\n"
            f"Title: {gov.get('title', 'Governor')}\n"
            f"Party: {gov.get('party', 'N/A')}\n"
        )

        if gov.get('financial_data'):
            fd = gov['financial_data']
            context_parts.append(
                f"Financial Data: Revenue KES {fd.get('total_revenue', 'N/A'):,}, "
                f"Expenditure KES {fd.get('total_expenditure', 'N/A'):,}, "
                f"OSR KES {fd.get('osr', 'N/A'):,}, "
                f"Absorption Rate: {fd.get('absorption_rate', 'N/A')}%"
            )

        if gov.get('audit_findings'):
            findings = gov['audit_findings'][:5]
            context_parts.append(f"Recent Audit Findings ({len(findings)} shown):")
            for f in findings:
                context_parts.append(
                    f"  - {f.get('title', 'Finding')}: {f.get('description', '')[:150]} "
                    f"(Severity: {f.get('severity', 'N/A')}, Amount: {f.get('amount_at_risk', 'N/A')})"
                )

    # Specific constituency
    if retrieved_data.get('constituency'):
        const = retrieved_data['constituency']
        context_parts.append(
            f"\n=== CONSTITUENCY: {const.get('name', 'N/A')} ===\n"
            f"MP: {const.get('mp_name', 'N/A')}\n"
            f"County: {const.get('county', 'Nyeri')}\n"
            f"Population: {const.get('population', 'N/A')}"
        )
        if const.get('ng_cdf_allocations'):
            context_parts.append(f"NG-CDF Allocations: {const['ng_cdf_allocations']}")

    # All constituencies summary
    if retrieved_data.get('constituencies'):
        context_parts.append(
            f"\n=== ALL CONSTITUENCIES ({len(retrieved_data['constituencies'])}) ==="
        )
        for c in retrieved_data['constituencies'][:5]:
            context_parts.append(f"  - {c.get('name', 'N/A')}: MP {c.get('mp_name', 'N/A')}")

    # MPs
    if retrieved_data.get('mps'):
        context_parts.append(
            f"\n=== MEMBERS OF PARLIAMENT ({len(retrieved_data['mps'])}) ==="
        )
        for mp in retrieved_data['mps'][:5]:
            context_parts.append(f"  - {mp.get('name', 'N/A')}: {mp.get('constituency', 'N/A')}")

    # Audit findings
    if retrieved_data.get('audit_findings'):
        findings = retrieved_data['audit_findings'][:10]
        context_parts.append(f"\n=== AUDIT FINDINGS ({len(findings)} shown) ===")
        for f in findings:
            context_parts.append(
                f"  - {f.get('title', 'Finding')}: {f.get('description', '')[:200]} "
                f"(Entity: {f.get('entity', 'N/A')}, Severity: {f.get('severity', 'N/A')})"
            )

    # Projects
    if retrieved_data.get('projects'):
        projs = retrieved_data['projects'][:10]
        context_parts.append(f"\n=== PROJECTS ({len(projs)} shown) ===")
        for p in projs:
            context_parts.append(
                f"  - {p.get('name', 'N/A')}: {p.get('status', 'N/A')}, "
                f"Budget: KES {p.get('budget', 'N/A'):,}, Location: {p.get('location', 'N/A')}"
            )

    # Departments
    if retrieved_data.get('departments'):
        depts = retrieved_data['departments'][:10]
        context_parts.append(f"\n=== DEPARTMENTS ({len(depts)} shown) ===")
        for d in depts:
            context_parts.append(
                f"  - {d.get('name', 'N/A')}: Absorption {d.get('absorption_rate', 'N/A')}%, "
                f"Budget: KES {d.get('budget', 'N/A'):,}"
            )

    return "\n".join(context_parts) if context_parts else "No specific data retrieved."


# ============================================================
# Future: Semantic Search Integration
# ============================================================

class SemanticRetriever:
    """
    Placeholder for future semantic search integration.
    Will use embeddings + vector search when enabled.
    """

    def __init__(self):
        self.enabled = False
        self.embedding_model = None
        self.vector_index = None

    def enable(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Enable semantic search with specified embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(embedding_model)
            self.enabled = True
            logger.info(f"Semantic search enabled with {embedding_model}")
        except ImportError:
            logger.warning("sentence-transformers not installed, semantic search disabled")

    def embed_query(self, query: str) -> list:
        """Generate embedding for query."""
        if not self.enabled:
            return []
        return self.embedding_model.encode(query).tolist()

    def search(self, query: str, collection: str, limit: int = 10) -> list:
        """Search collection using vector similarity."""
        if not self.enabled:
            return []
        # TODO: Implement with MongoDB Atlas Vector Search or pgvector
        return []


# Global instance for future use
semantic_retriever = SemanticRetriever()