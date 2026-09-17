# Accountability Platform

A Flask-based API for managing and visualizing Nyeri County financial and audit data, promoting transparency in public fund utilization.

## Overview

The Accountability Platform provides RESTful APIs to access:
- Constituency Development Fund (NGCDF) allocations and expenditures
- Governor's office finances and audit findings
- Departmental budget absorption rates
- Performance scoring based on financial management, audit results, and department efficiency
- AI-powered analysis and insights for both MP and governor tracks
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
- AI-powered text panels and charts integrated on all pages
- Mobile-friendly design
- Enhanced frontend UI with bolder colors, crystal white background, improved card styling, pitch dark header and footer, and improved font with better spacing

## Project Structure

```
Accountability-Platform/
├── backend/
│   ├── app.py                 # Main Flask application
│   └── api/
│       ├── auth.py            # Authentication blueprint
│       ├── constituency.py    # Constituency data blueprint
│       ├── governors.py       # Governor data blueprint
│       └── utils/
│           └── utils.py       # Database connection utility
├── Nyeri-frontend/            # React + Vite frontend
│   ├── src/
│   │   ├── components/        # Reusable UI pieces (buttons, cards, tables, charts, etc.)
│   │   ├── layouts/           # PublicLayout (navbar+footer) and AdminLayout (sidebar)
│   │   ├── pages/             # One file per public screen
│   │   ├── pages/admin/       # One file per admin screen
│   │   ├── data/              # mockData.js - stands in for the Flask API responses
│   │   ├── App.jsx            # All routes
│   │   └── main.jsx           # Entry point
│   ├── index.html             # HTML entry point
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.js
│   └── README.md              # Frontend-specific README
├── extract_and_seed.py        # NG-CDF data seeding script
├── governor_seed.py           # Governor data seeding script
├── requirements.txt           # Python dependencies
├── API_DOCS.md                # Detailed API documentation
├── README.md                  # This file
└── .gitignore
```

## Frontend Overview

The frontend is a React application built with Vite and Tailwind CSS, located in the `Nyeri-frontend/` directory. It implements all 19 screens from the design brief with mock data, ready to be wired up to the real Flask API.

To develop the frontend:

1. Ensure you have Node.js 18+ installed.
2. Navigate to the `Nyeri-frontend/` directory.
3. Run `npm install` to install dependencies.
4. Run `npm run dev` to start the development server (usually at http://localhost:5173).
5. The public site is available at http://localhost:5173/ and the admin panel at http://localhost:5173/admin/login (demo login).

To connect to the real backend:
- Add a `.env` file in `Nyeri-frontend/` with `VITE_API_URL=http://localhost:5000`.
- Replace the imports from `src/data/mockData.js` in each page with `fetch()` calls to your Flask endpoints.

Each page features:
- AI text panels with narrative explanations
- Chart.js visualizations consuming data directly from AI JSON responses
- Loading skeletons during AI fetch operations
- Data provenance footnotes citing source documents
- Responsive design for mobile and desktop viewing

## Setup Instructions

### Prerequisites

- Python 3.7+
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

### AI Engine
- `POST /api/ai/mp/<slug>/risk_score` - AI risk scoring for constituency
- `POST /api/ai/mp/<slug>/risk_level` - AI risk level analysis for constituency
- `POST /api/ai/mp/<slug>/summary` - AI summary generation for constituency
- `POST /api/ai/mp/<slug>/anomalies` - AI anomaly detection for constituency
- `POST /api/ai/mp/<slug>/peer_rank` - AI peer ranking analysis for constituency
- `POST /api/ai/mp/<slug>/citizen_actions` - AI citizen action recommendations for constituency
- `POST /api/ai/mp/<slug>/data_sources` - AI data source analysis for constituency
- `GET /api/ai/mp/<slug>/cached_at` - Cache timestamp information for constituency
- `POST /api/ai/governor/fiscal_health` - AI fiscal health scoring for governor
- `POST /api/ai/governor/dept_absorption` - AI department absorption analysis for governor
- `POST /api/ai/governor/osr_analysis` - AI OSR analysis for governor
- `POST /api/ai/governor/department_flags` - AI department flags analysis for governor
- `POST /api/ai/governor/top_risks` - AI top risks and citizen actions for governor
- `GET /api/ai/county/narrative` - AI county-level narrative analysis
- `POST /api/ai/findings/classifier` - AI audit finding classifier
- `POST /api/ai/compare` - AI cross-leader comparator

### Unified Endpoints
- `GET /api/findings` - Get findings for both leaders (with filtering)
- `GET /api/compare` - Compare two leaders

See `API_DOCS.md` and `AI_ENGINE.md` for complete API documentation with request/response examples.

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

All collections include a `county_code` field set to "019" for Nyeri County.

## Development

### Running Tests

```bash
# Run syntax check
python test_syntax.py
```

### Frontend Development

The frontend is located in the `Nyeri-frontend/` directory. For development instructions, see the [Frontend Overview](#frontend-overview) section above.

## Deployment

The application is designed for easy deployment to platforms like:
- Render
- Railway
- Heroku
- Docker
- Traditional VMs

For deployment, ensure:
1. MongoDB is accessible via MONGODB_URI
2. Environment variables are set
3. The application runs on the platform's specified port
4. For production, run `warm_cache.py` to pre-populate AI caches after deployment

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
*Last updated: September 2026*