# AI Engine Module

## Overview

The **AI Engine** (`backend/api/ai_engine`) is a Flask-based microservice that powers AI-driven financial accountability analysis for Kenyan counties and constituencies. It transforms raw audit data, financial records, and GNN-detected anomalies into plain-English narratives, risk assessments, and actionable citizen guidance.

**Built for:** The Accountability Platform — a civic tech tool helping Kenyan citizens understand how their public funds are managed.

---

## Architecture at a Glance

```
ai_engine/
├── __init__.py              # Main entry point, registers all blueprints
├── core/                    # Shared infrastructure
│   ├── factory.py           # Endpoint factories (eliminates code duplication)
│   ├── llm.py               # Groq API wrapper with retry + observability
│   ├── cache.py             # MongoDB cache with TTL + thundering-herd protection
│   ├── schemas.py           # Pydantic output schemas (strict validation)
│   ├── validation.py        # Output validation with retry logic
│   ├── prompts.py           # Data summarization for LLM prompts
│   └── auth.py              # JWT auth + rate limiting (Flask-Limiter)
├── modules/                 # Domain-specific endpoints
│   ├── mp.py                # MP/Constituency endpoints (7 modules)
│   ├── governor.py          # Governor/County Executive endpoints (5 modules)
│   └── county.py            # Cross-leader analysis (3 modules)
├── data/
│   └── access.py            # Single-source-of-truth MongoDB data access
├── rag/
│   ├── assistant.py         # RAG chat assistant endpoints
│   └── retrieval.py         # Semantic retrieval from vector store
└── evals/
    └── dataset.py           # Evaluation dataset generation
```

---

## Why This Design?

### 1. **Factory Pattern Eliminates Boilerplate**

Before: 15+ nearly identical endpoint functions, each ~80 lines.
After: 3 factory functions (`make_mp_endpoint`, `make_governor_endpoint`, `make_county_endpoint`) generate all endpoints from prompt templates + schemas.

```python
# One line creates a full endpoint with validation, caching, error handling
mp_risk_score = make_mp_endpoint(
    module="risk_score",
    prompt_template=MP_PROMPTS["risk_score"],
    summary_module="risk_score",
    governor_summary_module="risk_score"
)
```

**Benefit:** Adding a new analysis module = 1 prompt template + 1 schema + 1 line registration. No copy-paste bugs.

---

### 2. **Strict Output Validation (Pydantic)**

LLMs hallucinate. We treat every LLM response as **untrusted input**.

```python
# Every module has a strict Pydantic schema
class RiskScoreNarrative(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["High", "Medium", "Low"]
    summary: str = Field(min_length=50)
    key_drivers: list[str] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=30)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str
```

**Validation flow:**
1. LLM returns JSON
2. `validate_output()` checks against schema
3. On failure: retry once with error feedback (optional)
4. On final failure: return structured error, **never cache invalid output**

---

### 3. **Smart Caching with Stampede Protection**

AI calls are expensive (~$0.50–2.00 per call) and slow (2–10s). We cache aggressively.

```python
# Cache key = hash(prompt + model + parameters)
# TTL = 24 hours (configurable via AI_CACHE_TTL_HOURS)
# Stampede protection: in-memory lock per cache key
```

**Thundering herd prevention:**
- Request A misses cache → acquires lock → computes → caches → releases
- Requests B, C, D wait on same lock → get cached result when released
- No duplicate API calls for same input

**Cache skip:** Responses with `_error: true` are **never cached**.

---

### 4. **Data Access Layer = Single Source of Truth**

All MongoDB collection names and queries live in `data/access.py`. Endpoints never touch `db.collection` directly.

```python
# Centralized collection names
COLLECTIONS = {
    "constituencies": "constituencies",
    "allocations": "allocations",
    "audit_findings": "audit_findings",
    "gnn_anomalies": "gnn_anomalies",  # From Graph Neural Network
    # ...
}
```

**Benefit:** Schema changes? Update one file. New index? One place. Testing? Mock `data_access`.

---

### 5. **Prompt Engineering as Data, Not Code**

Prompts are **string templates** in `factory.py`, not scattered in endpoint logic.

```python
MP_PROMPTS = {
    "risk_score": """Analyze the financial risk for constituency '{constituency_slug}'.
    Constituency Summary:
    {constituency_summary}
    Governor Summary:
    {governor_summary}
    Return ONLY JSON with exactly this structure: {...}"""
}
```

**Why this matters:**
- Prompts are version-controllable, diffable, reviewable
- Non-engineers can edit prompts without touching Python
- Same prompt template → consistent output structure across modules

---

### 6. **Observability Built In**

Every LLM call logs:
- Model used
- Prompt tokens / completion tokens
- Finish reason (stop, length, content_filter)
- Latency

```python
logger.info(
    f"LLM call completed | model={model} | "
    f"prompt_tokens={usage.get('prompt_tokens')} | "
    f"completion_tokens={usage.get('completion_tokens')} | "
    f"finish_reason={finish_reason}"
)
```

---

## Endpoints Summary

### MP / Constituency (`/api/ai/mp/<constituency_slug>/...`)

| Endpoint | Purpose |
|----------|---------|
| `/risk_score` | 0–100 risk score + plain English explanation |
| `/risk_level` | Risk level + detected anomalies |
| `/summary` | Holistic constituency overview |
| `/anomalies` | GNN-detected anomalies + audit findings explained |
| `/peer_rank` | How this constituency ranks vs. peers |
| `/citizen_actions` | Specific, prioritized actions for residents |
| `/data_sources` | What data exists, gaps, reliability |
| `/cached_at` | Cache status for debugging |

### Governor / County Executive (`/api/ai/governor/...`)

| Endpoint | Purpose |
|----------|---------|
| `/fiscal_health` | Overall county financial health rating |
| `/dept_absorption` | Department budget absorption rates |
| `/osr_analysis` | Own Source Revenue trends & streams |
| `/department_flags` | Risk flags per department |
| `/top_risks` | Top 5 risks facing the county |

### County / Cross-Leader (`/api/ai/...`)

| Endpoint | Purpose |
|----------|---------|
| `/county/narrative` | Unified MP + Governor narrative |
| `/findings/classifier` | Classify specific audit findings |
| `/compare` | Side-by-side MP vs Governor comparison |

### RAG Assistant (`/api/ai/assistant/...`)

| Endpoint | Purpose |
|----------|---------|
| `/assistant` | Chat with grounded context retrieval |
| `/assistant/intent` | Classify user query intent |

---

## Data Flow: Request → Response

```
GET /api/ai/mp/mathare/risk_score
       │
       ▼
1. Validate constituency exists (data_access)
       │
       ▼
2. Generate data summaries (prompts.py)
   - constituency_summary: allocations, audits, MP info
   - governor_summary: county finances, audits, departments
       │
       ▼
3. Build prompt from template (factory.py)
       │
       ▼
4. Check cache (cache.py)
   - HIT: return cached response ✓
   - MISS: acquire lock → call LLM → validate → cache → return
       │
       ▼
5. LLM Call (llm.py)
   - Groq API (openai/gpt-oss-120b)
   - JSON mode enforced
   - Retry on 429/timeout (3 attempts, exponential backoff)
       │
       ▼
6. Validate output (validation.py)
   - Pydantic schema validation
   - Retry once on failure (optional)
       │
       ▼
7. Return standardized JSON
{
  "success": true,
  "module": "risk_score",
  "data": { "narrative_fields": {...}, "chart_data": {...} }
}
```

---

## Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *required* | Groq API key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | LLM model to use |
| `AI_CACHE_TTL_HOURS` | `24` | Cache time-to-live |
| `DISABLE_AI_CACHE` | `false` | Set `true` to bypass cache |
| `RATE_LIMIT_STORAGE_URL` | `memory://` | Redis URL for distributed rate limiting |

---

## Adding a New Analysis Module

**Example: Add "project_delivery" for MPs**

1. **Add schema** (`core/schemas.py`):
```python
class ProjectDeliveryNarrative(BaseModel):
    completion_rate: float = Field(ge=0, le=100)
    summary: str = Field(min_length=50)
    # ...

class ProjectDeliveryOutput(BaseModel):
    narrative_fields: ProjectDeliveryNarrative
    chart_data: ChartData = Field(default_factory=ChartData)

MP_SCHEMAS["project_delivery"] = ProjectDeliveryOutput
```

2. **Add prompt template** (`core/factory.py`):
```python
MP_PROMPTS["project_delivery"] = """Analyze project delivery for '{constituency_slug}'...
Return ONLY JSON: {...}"""
```

3. **Register endpoint** (`modules/mp.py`):
```python
mp_project_delivery = make_mp_endpoint(
    module="project_delivery",
    prompt_template=MP_PROMPTS["project_delivery"],
    summary_module="project_delivery",
    governor_summary_module="project_delivery"
)
mp_bp.route("/<constituency_slug>/project_delivery", methods=["GET"])(mp_project_delivery)
```

4. **Update version endpoint** (`__init__.py`) to include new endpoint in list.

**Done.** No other files touched.

---

## Testing

```bash
# Run AI engine tests
cd backend
pytest api/ai_engine/ -v

# Test specific module
pytest api/ai_engine/modules/test_mp.py -v
```

Key test areas:
- Schema validation (valid/invalid inputs)
- Cache hit/miss/stampede scenarios
- Prompt template rendering
- Data access layer queries
- LLM error handling (mock Groq API)

---

## Common Pitfalls & Solutions

| Problem | Solution |
|---------|----------|
| LLM returns invalid JSON | `json_mode=True` in payload + retry logic in `llm.py` |
| Validation fails silently | `validate_output()` logs every failure with field-level details |
| Cache stampede on cold start | In-memory locks per cache key in `cache.py` |
| Rate limit errors in production | `RATE_LIMIT_STORAGE_URL=redis://...` for multi-worker |
| Prompt too long for context window | Summaries in `prompts.py` are concise; max_tokens=8000 |
| GNN anomalies not showing | Check `gnn_anomalies` collection has `metadata.constituency_slug` |

---

## Performance Notes

- **Cold cache:** ~3–8s (LLM latency)
- **Warm cache:** ~50–100ms (MongoDB read)
- **Cache size:** ~2–5 KB per entry
- **Concurrent requests:** Stampede protection limits duplicate LLM calls
- **Model:** `openai/gpt-oss-120b` on Groq (fast inference, large context)

---

## Security

- **Authentication:** JWT required for all endpoints (configurable via `@require_auth`)
- **Rate limiting:** 30 req/min per user/IP (MP/Governor/County), 20 req/min (Assistant)
- **Input validation:** Constituency slugs validated against DB
- **Output sanitization:** Errors never leak internal details (`sanitize_for_client`)
- **No PII in prompts:** Only aggregated financial/audit data sent to LLM

---

## Future Enhancements

- [ ] Redis-backed cache locks for multi-worker deployments
- [ ] Async LLM calls with `httpx` + connection pooling
- [ ] Prompt versioning + A/B testing framework
- [ ] Structured logging → OpenTelemetry / DataDog
- [ ] Fine-tuned model for Kenyan audit terminology
- [ ] WebSocket streaming for Assistant chat

---

## File Reference Quick Links

| File | Purpose |
|------|---------|
| `core/factory.py` | Endpoint factories + all prompt templates |
| `core/schemas.py` | All Pydantic output schemas |
| `core/llm.py` | Groq API wrapper |
| `core/cache.py` | MongoDB cache + stampede protection |
| `core/validation.py` | Output validation + retry |
| `core/prompts.py` | Data → prompt summary generators |
| `core/auth.py` | JWT + rate limiting |
| `data/access.py` | MongoDB data access layer |
| `modules/mp.py` | MP endpoints (7 modules) |
| `modules/governor.py` | Governor endpoints (5 modules) |
| `modules/county.py` | Cross-leader endpoints (3 modules) |
| `rag/assistant.py` | RAG chat endpoints |
| `rag/retrieval.py` | Semantic search |
| `evals/dataset.py` | Evaluation data generation |

---

## License

Part of the Accountability Platform. Internal use only.