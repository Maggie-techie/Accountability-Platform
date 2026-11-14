"""
RAG Retrieval Module - keyword-based with optional semantic search support.
Retrieves relevant data from MongoDB based on query intent.
"""
import logging
import re
import os
from typing import Optional, List, Dict, Any
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
    Includes semantic search enhancement when enabled.

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

        # Semantic search enhancement
        if semantic_retriever.enabled:
            semantic_results = _semantic_search_enhancement(query, intent, constituency_slug)
            if semantic_results:
                data['semantic_results'] = semantic_results
                logger.info(f"Semantic search added {len(semantic_results)} relevant documents")

    except Exception as e:
        logger.error(f"Error retrieving data for RAG: {e}")

    return data


def _semantic_search_enhancement(
    query: str,
    intent: dict,
    constituency_slug: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Enhance retrieval with semantic search based on intent.
    Searches relevant collections for semantically similar content.
    """
    results = []

    try:
        # Determine which collections to search based on intent
        collections_to_search = []

        if intent.get("needs_audit"):
            collections_to_search.append(("audit_findings", "finding_text"))
        if intent.get("needs_financial"):
            collections_to_search.append(("financial_records", "description"))
        if intent.get("needs_project"):
            collections_to_search.append(("projects", "description"))
        if intent.get("needs_leader"):
            collections_to_search.append(("governor_profile", "bio"))

        # If no specific intent, search broad collections
        if not collections_to_search:
            collections_to_search = [
                ("audit_findings", "finding_text"),
                ("projects", "description"),
                ("financial_records", "description"),
            ]

        # Search each collection
        for collection_name, text_field in collections_to_search:
            try:
                # Try Atlas vector search first
                atlas_results = semantic_retriever.search_mongodb_atlas(
                    query, collection_name, limit=5
                )
                if atlas_results:
                    for r in atlas_results:
                        r['source_collection'] = collection_name
                    results.extend(atlas_results)
                    continue

                # Fallback: load documents and search in-memory
                # Only if collection is not too large
                db = data_access.db
                collection = db[collection_name]
                count = collection.count_documents({})

                # Only do in-memory search for reasonably sized collections
                if count <= 1000:
                    docs = list(collection.find().limit(500))
                    for doc in docs:
                        doc['_id'] = str(doc.get('_id', ''))

                    mem_results = semantic_retriever.search_in_memory(
                        query, docs, text_field=text_field, limit=5
                    )
                    for r in mem_results:
                        r['source_collection'] = collection_name
                    results.extend(mem_results)

            except Exception as e:
                logger.debug(f"Semantic search on {collection_name} failed: {e}")
                continue

        # Deduplicate by _id
        seen = set()
        unique_results = []
        for r in results:
            rid = r.get('_id', '')
            if rid and rid not in seen:
                seen.add(rid)
                unique_results.append(r)
            elif not rid:
                unique_results.append(r)

        return unique_results[:10]  # Limit total results

    except Exception as e:
        logger.error(f"Semantic search enhancement failed: {e}")
        return []


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

    # Semantic search results
    if retrieved_data.get('semantic_results'):
        sem_results = retrieved_data['semantic_results'][:5]
        context_parts.append(f"\n=== SEMANTICALLY RELEVANT DOCUMENTS ({len(sem_results)} shown) ===")
        for r in sem_results:
            score = r.get('similarity_score', r.get('score', 0))
            source = r.get('source_collection', 'unknown')
            # Get text content from various possible fields
            text = (r.get('finding_text') or r.get('description') or
                   r.get('title') or r.get('text') or str(r)[:200])
            context_parts.append(
                f"  - [{source}, relevance: {score:.2f}] {text[:300]}"
            )

    return "\n".join(context_parts) if context_parts else "No specific data retrieved."


# ============================================================
# Semantic Search Implementation
# ============================================================

class SemanticRetriever:
    """
    Semantic search using sentence-transformers embeddings.
    Supports both in-memory vector search and MongoDB Atlas Vector Search.
    """

    def __init__(self):
        self.enabled = False
        self.embedding_model = None
        self.embedding_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self._cache = {}  # Simple in-memory cache for embeddings

    def enable(self, embedding_model: str = None) -> bool:
        """
        Enable semantic search with specified embedding model.
        Returns True if successful, False otherwise.
        """
        if embedding_model:
            self.embedding_model_name = embedding_model

        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            self.enabled = True
            logger.info(f"Semantic search enabled with {self.embedding_model_name}")
            return True
        except ImportError:
            logger.warning("sentence-transformers not installed, semantic search disabled")
            self.enabled = False
            return False
        except Exception as e:
            logger.error(f"Failed to enable semantic search: {e}")
            self.enabled = False
            return False

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for query."""
        if not self.enabled or not self.embedding_model:
            return []

        # Check cache
        if query in self._cache:
            return self._cache[query]

        embedding = self.embedding_model.encode(query).tolist()
        # Cache with size limit
        if len(self._cache) > 1000:
            # Remove oldest entry
            self._cache.pop(next(iter(self._cache)))
        self._cache[query] = embedding
        return embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents."""
        if not self.enabled or not self.embedding_model:
            return []
        return self.embedding_model.encode(texts).tolist()

    def search_in_memory(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        text_field: str = "text",
        limit: int = 10,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Search documents using cosine similarity in memory.

        Args:
            query: Search query
            documents: List of dicts with text content
            text_field: Field name containing text to search
            limit: Maximum results
            threshold: Minimum similarity score (0-1)

        Returns:
            List of matching documents with similarity scores
        """
        if not self.enabled or not documents:
            return []

        query_embedding = self.embed_query(query)
        if not query_embedding:
            return []

        # Extract texts
        texts = [doc.get(text_field, "") for doc in documents]
        if not any(texts):
            return []

        doc_embeddings = self.embed_documents(texts)
        if not doc_embeddings:
            return []

        # Compute cosine similarity
        import numpy as np
        query_vec = np.array(query_embedding)
        doc_vecs = np.array(doc_embeddings)

        # Normalize
        query_norm = np.linalg.norm(query_vec)
        doc_norms = np.linalg.norm(doc_vecs, axis=1)

        # Avoid division by zero
        doc_norms[doc_norms == 0] = 1
        query_norm = query_norm if query_norm > 0 else 1

        similarities = np.dot(doc_vecs, query_vec) / (doc_norms * query_norm)

        # Get top results above threshold
        results = []
        for idx, score in enumerate(similarities):
            if score >= threshold:
                doc = documents[idx].copy()
                doc['similarity_score'] = float(score)
                results.append(doc)

        # Sort by similarity descending
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]

    def search_mongodb_atlas(
        self,
        query: str,
        collection_name: str,
        limit: int = 10,
        index_name: str = "vector_index"
    ) -> List[Dict[str, Any]]:
        """
        Search using MongoDB Atlas Vector Search.
        Requires MongoDB Atlas with vector search index configured.

        Args:
            query: Search query
            collection_name: MongoDB collection name
            limit: Maximum results
            index_name: Vector search index name

        Returns:
            List of matching documents
        """
        if not self.enabled:
            return []

        try:
            query_embedding = self.embed_query(query)
            if not query_embedding:
                return []

            db = data_access.db
            collection = db[collection_name]

            # MongoDB Atlas Vector Search pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": index_name,
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": limit * 10,
                        "limit": limit
                    }
                },
                {
                    "$project": {
                        "embedding": 0,  # Don't return embeddings
                        "score": {"$meta": "vectorSearchScore"}
                    }
                }
            ]

            results = list(collection.aggregate(pipeline))
            logger.info(f"Vector search returned {len(results)} results from {collection_name}")
            return results

        except Exception as e:
            logger.warning(f"MongoDB Atlas Vector Search failed: {e}")
            return []

    def search(
        self,
        query: str,
        collection: str = None,
        limit: int = 10,
        documents: List[Dict[str, Any]] = None,
        text_field: str = "text",
        use_atlas: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Unified search interface.

        Args:
            query: Search query
            collection: MongoDB collection name (for Atlas search)
            limit: Maximum results
            documents: Pre-loaded documents (for in-memory search)
            text_field: Text field for in-memory search
            use_atlas: Use MongoDB Atlas Vector Search

        Returns:
            List of matching documents
        """
        if not self.enabled:
            logger.debug("Semantic search not enabled, returning empty results")
            return []

        # Try Atlas search first if enabled and collection provided
        if use_atlas and collection:
            results = self.search_mongodb_atlas(query, collection, limit)
            if results:
                return results

        # Fallback to in-memory search if documents provided
        if documents:
            return self.search_in_memory(query, documents, text_field, limit)

        return []


# Global instance
semantic_retriever = SemanticRetriever()


# Auto-enable if ENABLE_SEMANTIC_SEARCH env var is set
if os.getenv("ENABLE_SEMANTIC_SEARCH", "false").lower() == "true":
    semantic_retriever.enable()