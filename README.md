# Accountability Platform

A Flask-based API for managing and visualizing Nyeri County financial and audit data, promoting transparency in public fund utilization.

## Overview

The Accountability Platform provides RESTful APIs to access:
- Constituency Development Fund (NGCDF) allocations and expenditures
- Governor's office finances and audit findings
- Departmental budget absorption rates
- Performance scoring based on financial management, audit results, and department efficiency

## Features

- Secure authentication with JWT tokens
- MongoDB data storage with proper indexing
- Comprehensive API documentation
- Data seeding scripts for easy setup
- Filtering, pagination, and error handling
- Unified endpoints for cross-leader comparisons
- Performance scoring algorithms

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
├── extract_and_seed.py        # NG-CDF data seeding script
├── governor_seed.py           # Governor data seeding script
├── requirements.txt           # Python dependencies
├── API_DOCS.md                # Detailed API documentation
├── README.md                  # This file
└── .gitignore
```

## Setup Instructions

### Prerequisites
- Python 3.7+
- MongoDB instance (local or cloud)
- Git (for version control)

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

The API will be available at `http://localhost:5000`

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

### Unified Endpoints
- `GET /api/findings` - Get findings for both leaders (with filtering)
- `GET /api/compare` - Compare two leaders

See `API_DOCS.md` for complete API documentation with request/response examples.

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

### API Documentation
View detailed API documentation in `API_DOCS.md`

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