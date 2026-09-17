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
- Enhanced frontend UI with bolder colors, crystal white background, and improved card styling

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
├── frontend/
│   ├── index.html             # Dashboard/homepage
│   ├── mps.html               # MPs and constituencies page
│   ├── constituency.html      # Constituency detail page
│   ├── findings.html          # Audit findings page
│   ├── allocations.html       # Fund allocations page
│   ├── governor.html          # Governor's office page
│   ├── governor-departments.html  # Governor departments page
│   ├── governor-findings.html     # Governor findings page
│   ├── compare.html           # Cross-leader comparison page
│   ├── css/
│   │   └── style.css          # Main stylesheet
│   └── js/
│       └── main.js            # Main JavaScript with AI service and chart rendering
├── extract_and_seed.py        # NG-CDF data seeding script
├── governor_seed.py           # Governor data seeding script
├── requirements.txt           # Python dependencies
├── API_DOCS.md                # Detailed API documentation
├── README.md                  # This file
└── .gitignore
```

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

6. Access the frontend at `http://localhost:5000`

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

The frontend uses plain HTML, CSS, and JavaScript with Chart.js for visualizations. To modify:
- Edit HTML files in the `frontend/` directory
- Modify styles in `frontend/css/style.css`
- Update logic in `frontend/js/main.js`

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