# Accountability Platform API Documentation

## Base URL
All API endpoints are prefixed with `/api`

## Authentication
### Login
```
POST /api/auth/login
```
Authenticates a user and returns a JWT token.

**Request Body:**
```json
{
  "admin_name": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "admin": "string",
  "name": "string"
}
```

**Error Responses:**
- 400: Missing admin_name or password
- 401: Invalid credentials

## Governor Endpoints
### Get Governor Profile
```
GET /api/governor/
```
Returns the governor's profile information.

**Response:**
```json
{
  "name": "string",
  "role": "string",
  "county": "string",
  "party": "string",
  "tenure": "string",
  "level": "string",
  "county_code": "string",
  "created_at": "string (ISO date)"
}
```

### Get Governor Finances
```
GET /api/governor/finances
```
Returns financial data (revenue sources) for all financial years.

**Query Parameters:**
- `year`: Filter by financial year (e.g., "2022/23")

**Response:**
```json
[
  {
    "county": "string",
    "governor": "string",
    "revenue_source": "string",
    "description": "string",
    "financial_year": "string",
    "amount_kshb": "number",
    "notes": "string",
    "county_code": "string",
    "created_at": "string (ISO date)"
  }
]
```

### Get Governor Departments
```
GET /api/governor/departments
```
Returns department budget absorption data.

**Response:**
```json
[
  {
    "county": "string",
    "department": "string",
    "financial_year": "string",
    "approved_budget_kshm": "number",
    "q3_spend_kshm": "number",
    "absorption_rate": "number",
    "remaining_budget_kshm": "number",
    "projected_year_end": "number",
    "status": "string",
    "issues": "string",
    "county_code": "string",
    "created_at": "string (ISO date)"
  }
]
```

### Get Governor Audit Findings
```
GET /api/governor/audit
```
Returns Office of the Auditor General (OAG) audit findings.

**Response:**
```json
[
  {
    "county": "string",
    "governor": "string",
    "category": "string",
    "financial_year": "string",
    "amount_flagged_kshm": "number",
    "severity": "string",
    "finding_type": "string",
    "misappropriation_notes": "string",
    "recommendation": "string",
    "county_code": "string",
    "created_at": "string (ISO date)"
  }
]
```

### Get Governor Score
```
GET /api/governor/score
```
Returns a calculated performance score based on financial data, audit findings, and department performance.

**Response:**
```json
{
  "score": "number",
  "generated_at": "string (ISO date)"
}
```

## Constituency Endpoints
### Get All Constituencies
```
GET /api/constituency/
```
Returns a list of all constituencies with optional filtering and pagination.

**Query Parameters:**
- `county`: Filter by county
- `audit_status`: Filter by audit status
- `page`: Page number for pagination (default: 1)
- `limit`: Number of items per page (default: 10)

**Response:**
```json
{
  "constituencies": [
    {
      "slug": "string",
      "name": "string",
      "county": "string",
      "county_code": "string",
      "mp": {
        "name": "string",
        "party": "string",
        "tenure": "string",
        "gender": "string"
      },
      "audit_status": "string",
      "oag_opinion": "string",
      "allocations_ksm": {
        "FY2022_23": "number",
        "FY2023_24": "number",
        "FY2024_25": "number",
        "FY2025_26": "number"
      },
      "misappropriations": [
        {
          "id": "string",
          "finding": "string",
          "finding_type": "string"
        }
      ],
      "correct_appropriations": [
        {
          "id": "string",
          "note": "string",
          "finding_type": "string"
        }
      ],
      "fy_reviewed": "string",
      "amount_at_risk": "string",
      "data_sources": ["string"],
      "created_at": "string (ISO date)",
      "updated_at": "string (ISO date)",
      "_id": "string"
    }
  ],
  "pagination": {
    "page": "number",
    "limit": "number",
    "total": "number",
    "pages": "number"
  }
}
```

### Get Constituency by Slug
```
GET /api/constituency/<slug>
```
Returns a specific constituency by its slug.

**URL Parameters:**
- `slug`: The constituency slug (e.g., "tetu")

**Response:** Same object as in the constituencies array above

### Get All Allocations
```
GET /api/constituency/allocations
```
Returns all allocation records with optional filtering and pagination.

**Query Parameters:**
- `constituency_slug`: Filter by constituency slug
- `fy_key`: Filter by fiscal year key (e.g., FY2022_23)
- `page`: Page number for pagination (default: 1)
- `limit`: Number of items per page (default: 10)

**Response:**
```json
{
  "allocations": [
    {
      "constituency": "string",
      "constituency_slug": "string",
      "mp_name": "string",
      "fy_key": "string",
      "fy_display": "string",
      "amount_kshm": "number",
      "county": "string",
      "county_code": "string",
      "_id": "string"
    }
  ],
  "pagination": {
    "page": "number",
    "limit": "number",
    "total": "number",
    "pages": "number"
  }
}
```

### Get Allocations by Constituency
```
GET /api/constituency/allocations/<slug>
```
Returns allocation records for a specific constituency.

**URL Parameters:**
- `slug`: The constituency slug

**Response:**
```json
{
  "allocations": [
    {
      "constituency": "string",
      "constituency_slug": "string",
      "mp_name": "string",
      "fy_key": "string",
      "fy_display": "string",
      "amount_kshm": "number",
      "county": "string",
      "county_code": "string",
      "_id": "string"
    }
  ],
  "count": "number"
}
```

### Get All Audit Findings
```
GET /api/constituency/audit
```
Returns all audit findings with optional filtering and pagination.

**Query Parameters:**
- `constituency_slug`: Filter by constituency slug
- `finding_type`: Filter by finding type (misappropriation/correct_appropriation)
- `page`: Page number for pagination (default: 1)
- `limit`: Number of items per page (default: 10)

**Response:**
```json
{
  "audit_findings": [
    {
      "_id": "string",
      "constituency": "string",
      "constituency_slug": "string",
      "mp_name": "string",
      "county": "string",
      "id": "string",
      "finding": "string",
      "finding_type": "string",
      "note": "string",
      "fy_reviewed": "string",
      "amount_at_risk": "string",
      "county_code": "string"
    }
  ],
  "pagination": {
    "page": "number",
    "limit": "number",
    "total": "number",
    "pages": "number"
  }
}
```

### Get Audit Findings by Constituency
```
GET /api/constituency/audit/<slug>
```
Returns audit findings for a specific constituency.

**URL Parameters:**
- `slug`: The constituency slug

**Response:**
```json
{
  "audit_findings": [
    {
      "_id": "string",
      "constituency": "string",
      "constituency_slug": "string",
      "mp_name": "string",
      "county": "string",
      "id": "string",
      "finding": "string",
      "finding_type": "string",
      "note": "string",
      "fy_reviewed": "string",
      "amount_at_risk": "string",
      "county_code": "string"
    }
  ],
  "count": "number"
}
```

### Get All MPs
```
GET /api/constituency/mps
```
Returns all MP records with optional filtering and pagination.

**Query Parameters:**
- `constituency_slug`: Filter by constituency slug
- `oag_opinion`: Filter by OAG opinion
- `audit_status`: Filter by audit status
- `page`: Page number for pagination (default: 1)
- `limit`: Number of items per page (default: 10)

**Response:**
```json
{
  "mps": [
    {
      "name": "string",
      "party": "string",
      "tenure": "string",
      "constituency": "string",
      "constituency_slug": "string",
      "county": "string",
      "county_code": "string",
      "total_allocation_kshm": "number",
      "misappropriation_count": "number",
      "correct_appropriation_count": "number",
      "oag_opinion": "string",
      "audit_status": "string",
      "amount_at_risk": "string",
      "_id": "string"
    }
  ],
  "pagination": {
    "page": "number",
    "limit": "number",
    "total": "number",
    "pages": "number"
  }
}
```

### Get MP by Constituency
```
GET /api/constituency/mps/<slug>
```
Returns MP data for a specific constituency.

**URL Parameters:**
- `slug`: The constituency slug

**Response:** Same object as in the mps array above

## Unified Findings Endpoint
### Get All Findings (Both Leaders)
```
GET /api/findings
```
Returns audit findings for both Governor and MP leaders in a unified format.

**Query Parameters:**
- `leader_type`: Filter by leader type (governor/constituency)
- `constituency_slug`: Filter by constituency slug (for constituency findings)
- `finding_type`: Filter by finding type (misappropriation/correct_appropriation)
- `page`: Page number for pagination (default: 1)
- `limit`: Number of items per page (default: 10)

**Response:**
```json
{
  "findings": [
    {
      "_id": "string",
      "leader_type": "string", // "governor" or "constituency"
      "leader_id": "string", // governor name or constituency slug
      "leader_name": "string", // full name of leader
      "category": "string", // for governor findings
      "constituency": "string", // for constituency findings
      "financial_year": "string",
      "amount_flagged_kshm": "number",
      "severity": "string",
      "finding_type": "string",
      "misappropriation_notes": "string",
      "recommendation": "string",
      "note": "string", // for constituency findings
      "fy_reviewed": "string", // for constituency findings
      "amount_at_risk": "string", // for constituency findings
      "county": "string",
      "county_code": "string",
      "_id": "string"
    }
  ],
  "pagination": {
    "page": "number",
    "limit": "number",
    "total": "number",
    "pages": "number"
  }
}
```

## Compare Endpoint
### Compare Two Leaders
```
GET /api/compare
```
Compares two leaders (governor or constituency MPs) based on various metrics.

**Query Parameters:**
- `leader1_type`: Type of first leader (governor/constituency)
- `leader1_id`: ID of first leader (governor name or constituency slug)
- `leader2_type`: Type of second leader (governor/constituency)
- `leader2_id`: ID of second leader (governor name or constituency slug)
- `metrics`: Comma-separated list of metrics to compare (financial, audit, performance)

**Response:**
```json
{
  "comparison": {
    "leader1": {
      "type": "string",
      "id": "string",
      "name": "string",
      "metrics": {
        "financial": "number",
        "audit": "number",
        "performance": "number"
      }
    },
    "leader2": {
      "type": "string",
      "id": "string",
      "name": "string",
      "metrics": {
        "financial": "number",
        "audit": "number",
        "performance": "number"
      }
    },
    "difference": {
      "financial": "number",
      "audit": "number",
      "performance": "number"
    },
    "winner": "string" // "leader1" or "leader2" or "tie"
  }
}
```

## Error Handling
All endpoints return JSON error objects with the following format:
```json
{
  "error": "string",
  "details": "string" // optional
}
```

HTTP Status Codes:
- 200: Success
- 400: Bad Request (invalid input)
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error

## Data Notes
- All monetary values are in Kenyan Shillings (KSH)
- Financial year format: "YYYY/YY"
- County code for Nyeri: "019"
- All dates are in ISO 8601 format
- ObjectIds are converted to strings for JSON serialization