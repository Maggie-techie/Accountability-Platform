# Accountability Platform

A Flask-based API for managing and visualizing Nyeri County financial and audit data, promoting transparency in public fund utilization.

## Overview

The Accountability Platform provides RESTful APIs to access:
- Constituency Development Fund (NGCDF) allocations and expenditures
- Governor's office finances and audit findings
- Departmental budget absorption rates
- Performance scoring based on financial management, audit results, and department efficiency
- **Modular AI Engine** — factory-pattern endpoints with strict Pydantic validation, smart caching, and RAG assistant
- Complete frontend interface for data visualization and AI insights

## Features

- Secure authentication with JWT tokens
- MongoDB data storage with proper indexing
- Comprehensive API documentation
- Data seeding scripts for easy setup
- Filtering, pagination, and error handling
- Unified endpoints for cross-leader comparisons
- Performance scoring algorithms
- Responsive frontend dashboard with Chart.js visualizations
- **Modular AI Engine** — factory-pattern endpoints with strict output validation, 24h TTL cache + stampede protection
- **RAG Assistant** — grounded conversational AI with semantic retrieval from audit/financial data
- Mobile-friendly design
- Enhanced frontend UI with bolder colors, crystal white background, improved card styling, pitch dark header and footer

## Project Structure

```
Accountability-Platform/
├── backend/
│   ├── app.py                          # Main Flask application
│   └── api/
│       ├── auth.py                     # Authentication blueprint
│       ├── constituency.py             # Constituency data blueprint
│       ├── governors.py                # Governor data blueprint
│       ├── general.py                  # General endpoints (health, findings, compare)
│       ├── reports.py                  # Reports blueprint
│       └── ai_engine/                  # MODULAR AI ENGINE (NEW)
│           ├── __init__.py             # Main entry point, registers sub-blueprints
│           ├── core/
│           │   ├── factory.py          # Endpoint factories + prompt templates (eliminates boilerplate)
│           │   ├── llm.py              # Groq API wrapper (retry, JSON mode, observability)
│           │   ├── cache.py            # MongoDB cache with TTL + thundering-herd protection
│           │   ├── schemas.py          # Pydantic output schemas (strict validation)
│           │   ├── validation.py       # Output validation with retry logic
│           │   ├── prompts.py          # Data summarization for LLM prompts
│           │   └── auth.py             # JWT auth + rate limiting (Flask-Limiter)
│           ├── modules/
│           │   ├── mp.py               # MP/Constituency endpoints (7 modules)
│           │   ├── governor.py         # Governor/County Executive endpoints (5 modules)
│           │   └── county.py           # Cross-leader analysis (3 modules)
│           ├── data/
│           │   └── access.py           # Single-source-of-truth MongoDB data access
│           ├── rag/
│           │   ├── assistant.py        # RAG chat assistant endpoints
│           │   └── retrieval.py        # Semantic retrieval from vector store
│           └── evals/
│               └── dataset.py          # Evaluation dataset generation
├── Nyeri-frontend/                     # React + Vite frontend
│   ├── src/
│   │   ├── components/                 # Reusable UI pieces (buttons, cards, tables, charts)
│   │   ├── layouts/                    # PublicLayout (navbar+footer) and AdminLayout (sidebar)
│   │   ├── pages/                      # One file per public screen
│   │   ├── pages/admin/                # One file per admin screen
│   │   ├── services/                   # API service layer (api.js)
│   │   ├── App.jsx                     # All routes
│   │   └── main.jsx                    # Entry point
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── README.md                       # Frontend-specific README
├── extract_and_seed.py                 # NG-CDF data seeding script
├── governor_seed.py                    # Governor data seeding script
├── requirements.txt                    # Python dependencies
├── API_DOCS.md                         # Detailed API documentation
├── README.md                           # This file
└── .gitignore
```

> **Note:** The old monolithic `backend/api/ai_engine.py` (~1,900 lines) has been deleted. All AI functionality now lives in the modular `backend/api/ai_engine/` directory.

## Frontend Overview

The frontend is a React application built with Vite and Tailwind CSS, located in the `Nyeri-frontend/` directory. It implements all screens from the design with mock data, ready to be wired up to the real Flask API.

To develop the frontend:

1. Ensure you have Node.js 18+ installed.
2. Navigate to the `Nyeri-frontend/` directory.
3. Run `npm install` to install dependencies.
4. Run `npm run dev` to start the development server (usually at http://localhost:5173).
5. The public site is available at http://localhost:5173/ and the admin panel at http://localhost:5173/admin/login (demo login).

To connect to the real backend:
- Add a `.env` file in `Nyeri-frontend/` with `VITE_API_BASE_URL=http://localhost:5000/api`.
- The `APIService` in `src/services/api.js` handles all backend calls.

Each page features:
- AI text panels with narrative explanations
- Chart.js visualizations consuming data directly from AI JSON responses
- Loading skeletons during AI fetch operations
- Data provenance footnotes citing source documents
- Responsive design for mobile and desktop viewing

## Setup Instructions

### Prerequisites

- Python 3.10+
- MongoDB instance (local or cloud)
- Git (for version control)
- Web browser (for frontend)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Accountability-Platform
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (create a `.env` file or set environment variables):
```bash
MONGODB_URI=mongodb://localhost:27017/Accountability
JWT_SECRET_KEY=your-secret-key-here
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b
AI_CACHE_TTL_HOURS=24
DISABLE_AI_CACHE=false
```

4. Seed the database with initial data:
```bash
# Seed governor data
python governor_seed.py

# Seed NGCDF data
python extract_and_seed.py
```

5. Run the application:
```bash
python backend/app.py
```

6. Access the frontend at `http://localhost:5173` (when running `npm run dev` in the `Nyeri-frontend/` directory). The backend API is available at `http://localhost:5000`.

## AI Engine — Modular Architecture

The AI Engine has been refactored from a single 1,900-line file into a clean, modular package. Key design decisions:

| Principle | Implementation |
|---|---|
| **Factory Pattern** | 3 factory functions generate all 15+ endpoints from prompt templates + schemas |
| **Strict Validation** | Every LLM response validated against Pydantic schemas; invalid output never cached |
| **Smart Caching** | 24h TTL, MongoDB-backed, in-memory locks prevent thundering herd |
| **Data Access Layer** | Single source of truth for all MongoDB queries (`data/access.py`) |
| **Prompts as Data** | Prompt templates are version-controllable strings in `core/factory.py` |
| **Observability** | Token usage, latency, finish reason logged per LLM call |

See `backend/api/ai_engine/README.md` for detailed architecture, adding new modules, and troubleshooting.

### AI Endpoints (All under `/api/ai`)

#### MP / Constituency (`/api/ai/mp/<constituency_slug>/...`)
| Endpoint | Method | Description |
|---|---|---|
| `/risk_score` | GET | 0–100 risk score + plain English explanation |
| `/risk_level` | GET | Risk level + detected anomalies |
| `/summary` | GET | Holistic constituency overview |
| `/anomalies` | GET | GNN-detected anomalies + audit findings explained |
| `/peer_rank` | GET | How this constituency ranks vs. peers |
| `/citizen_actions` | GET | Specific, prioritized actions for residents |
| `/data_sources` | GET | What data exists, gaps, reliability |
| `/cached_at` | GET | Cache status for debugging |

#### Governor / County Executive (`/api/ai/governor/...`)
| Endpoint | Method | Description |
|---|---|---|
| `/fiscal_health` | GET | Overall county financial health rating |
| `/dept_absorption` | GET | Department budget absorption rates |
| `/osr_analysis` | GET | Own Source Revenue trends & streams |
| `/department_flags` | GET | Risk flags per department |
| `/top_risks` | GET | Top 5 risks facing the county |

#### County / Cross-Leader (`/api/ai/...`)
| Endpoint | Method | Description |
|---|---|---|
| `/county/narrative` | GET | Unified MP + Governor narrative |
| `/findings/classifier` | POST | Classify specific audit findings |
| `/compare` | POST | Side-by-side MP vs Governor comparison |

#### RAG Assistant (`/api/ai/assistant/...`)
| Endpoint | Method | Description |
|---|---|---|
| `/assistant` | POST | Conversational AI with grounded context retrieval |
| `/assistant/intent` | POST | Classify user query intent |

### Adding a New AI Module (4 steps)

1. **Add schema** in `core/schemas.py`
2. **Add prompt template** in `core/factory.py` (`MP_PROMPTS`, `GOVERNOR_PROMPTS`, or `COUNTY_PROMPTS`)
3. **Register endpoint** in appropriate module (`modules/mp.py`, `modules/governor.py`, or `modules/county.py`)
4. **Update version endpoint** in `__init__.py` to include new route

No other files touched — zero boilerplate duplication.

### Bug Fix: Double URL Prefix (Fixed)

**Problem:** The AI blueprint was created with `url_prefix="/api/ai"` in `__init__.py` AND registered with `url_prefix="/api/ai"` in `app.py`, causing endpoints to resolve to `/api/ai/api/ai/...` (404).

**Fix:** Removed the duplicate prefix from `backend/api/ai_engine/__init__.py`:
```python
# Before
ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

# After
ai_bp = Blueprint("ai", __name__)  # url_prefix set only in app.py
```

Now endpoints correctly resolve to `/api/ai/mp/...`, `/api/ai/governor/...`, etc.

## API Endpoints

All API endpoints are prefixed with `/api`

### Authentication
- `POST /api/auth/login` - Authenticate user and get JWT token

### Governor Data
- `GET /api/governor/` - Get governor profile
- `GET /api/governor/finances` - Get financial data (filter by year)
- `GET /api/governor/departments` - Get department budget absorption
- `GET /api/governor/audit` - Get audit findings
- `GET /api/governor/score` - Get performance score

### Constituency Data
- `GET /api/constituency/` - Get all constituencies (with filtering/pagination)
- `GET /api/constituency/<slug>` - Get specific constituency
- `GET /api/constituency/allocations` - Get allocation records
- `GET /api/constituency/allocations/<slug>` - Get allocations by constituency
- `GET /api/constituency/audit` - Get audit findings
- `GET /api/constituency/audit/<slug>` - Get audit findings by constituency
- `GET /api/constituency/mps` - Get MP records
- `GET /api/constituency/mps/<slug>` - Get MP by constituency

### General / Unified
- `GET /api/findings` - Get findings for both leaders (with filtering)
- `GET /api/compare` - Compare two leaders
- `GET /api/health` - API health check

### AI Engine (modular, see table above)
- Base path: `/api/ai/...`

See `API_DOCS.md` and `backend/api/ai_engine/README.md` for complete API documentation with request/response examples.

## Data Model

The platform stores data in MongoDB with the following collections:

### MP/Constituency Related
- `constituencies`: NGCDF allocations, audit status, MP info
- `allocations`: Per-constituency per-fiscal-year funding records
- `audit_findings`: Misappropriations and correct appropriations
- `mps`: MP summary scorecards

### Governor Related
- `county_leaders`: Governor profile
- `county_finances`: Revenue sources by fiscal year
- `county_audit_findings`: Detailed audit records
- `department_absorption`: Departmental budget utilization
- `gnn_anomalies`: Graph Neural Network anomaly detections

### AI Engine
- `ai_cache`: Cached LLM responses with TTL index

All collections include a `county_code` field set to "019" for Nyeri County.

## Development

### Running Tests

```bash
# Run syntax check
python test_syntax.py

# Run AI engine tests
cd backend && pytest api/ai_engine/ -v
```

### Frontend Development

The frontend is located in the `Nyeri-frontend/` directory. For development instructions, see the [Frontend Overview](#frontend-overview) section above.

### Environment Variables for AI Engine

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *required* | Groq API key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | LLM model to use |
| `AI_CACHE_TTL_HOURS` | `24` | Cache time-to-live |
| `DISABLE_AI_CACHE` | `false` | Set `true` to bypass cache |
| `RATE_LIMIT_STORAGE_URL` | `memory://` | Redis URL for distributed rate limiting |

## Deployment

The application is designed for easy deployment to platforms like:
- Render
- Railway
- Heroku
- Docker
- Traditional VMs

For deployment, ensure:
1. MongoDB is accessible via `MONGODB_URI`
2. Environment variables are set (including `GROQ_API_KEY`)
3. The application runs on the platform's specified port
4. For production, run `warm_cache.py` to pre-populate AI caches after deployment
5. Set `RATE_LIMIT_STORAGE_URL=redis://...` for multi-worker deployments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Nyeri County government for providing data through official channels
- Open data initiatives promoting government transparency
- The Flask and MongoDB communities for excellent documentation and support

---

*Last updated: November 2026*