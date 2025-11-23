# API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently open. JWT authentication planned for production.

## Endpoints

### Search Endpoints

#### POST /search/
Search for jobs using keyword filters.

**Request Body:**
```json
{
  "query": "data engineer",
  "location": "San Francisco",
  "is_remote": false,
  "sponsors_h1b": true,
  "job_category": "Engineering",
  "seniority_level": "Senior",
  "limit": 20
}
```

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "abc123",
      "source": "indeed",
      "title": "Senior Data Engineer",
      "company_name": "Tech Corp",
      "location": "San Francisco, CA",
      "description": "We are hiring...",
      "posted_date": "2025-11-20T00:00:00",
      "url": "https://...",
      "salary_range": "$150,000 - $200,000",
      "job_type": "Full-time",
      "seniority_level": "Senior",
      "job_category": "Engineering",
      "extracted_skills": "Python, SQL, Spark",
      "is_remote": false,
      "likely_sponsors_h1b": true,
      "h1b_application_count": 50
    }
  ],
  "total_count": 15,
  "query": "data engineer"
}
```

#### GET /search/semantic
Semantic search using vector similarity.

**Parameters:**
- `query` (required): Search query
- `limit` (optional): Number of results (default: 20)

**Response:** Same as POST /search/

---

### Resume Endpoints

#### POST /resume/upload
Upload and process a resume.

**Request Body:**
```json
{
  "user_id": "user123",
  "resume_text": "Full resume text..."
}
```

**Response:**
```json
{
  "message": "Resume uploaded successfully",
  "user_id": "user123",
  "extracted_skills": "Python, Java, SQL, AWS"
}
```

#### POST /resume/match
Find matching jobs for a resume.

**Request Body:**
```json
{
  "resume_id": "resume-uuid",
  "top_k": 10,
  "min_similarity": 0.7
}
```

**Response:**
```json
{
  "matches": [
    {
      "job": { /* Job object */ },
      "similarity_score": 0.92
    }
  ],
  "resume_id": "resume-uuid"
}
```

#### GET /resume/user/{user_id}
Get all resumes for a user.

**Response:**
```json
{
  "resumes": [
    {
      "resume_id": "uuid",
      "skills": "Python, Java",
      "uploaded_at": "2025-11-20T10:00:00"
    }
  ]
}
```

---

### Jobs Endpoints

#### GET /jobs/{job_id}
Get detailed job information.

**Parameters:**
- `job_id` (required): Job ID
- `source` (required): Source (e.g., "indeed")

**Response:** Single job object

#### POST /jobs/save
Save a job for a user.

**Request Body:**
```json
{
  "user_id": "user123",
  "job_id": "job456",
  "source": "indeed",
  "notes": "Interesting role, apply next week"
}
```

**Response:**
```json
{
  "message": "Job saved successfully"
}
```

#### GET /jobs/saved/{user_id}
Get all saved jobs for a user.

**Response:**
```json
{
  "saved_jobs": [
    {
      "job_id": "job456",
      "source": "indeed",
      "saved_at": "2025-11-20T10:00:00",
      "notes": "...",
      "title": "Software Engineer",
      "company_name": "Tech Corp",
      "location": "Remote",
      "url": "https://..."
    }
  ]
}
```

#### DELETE /jobs/saved/{user_id}/{job_id}
Remove a saved job.

**Parameters:**
- `source` (required): Job source

**Response:**
```json
{
  "message": "Saved job removed"
}
```

---

### Analytics Endpoints

#### GET /analytics/companies
Get top hiring companies.

**Parameters:**
- `limit` (optional): Number of results (default: 20)

**Response:**
```json
{
  "companies": [
    {
      "company_name": "Tech Corp",
      "job_count": 150,
      "h1b_sponsor_count": 100,
      "remote_count": 75
    }
  ]
}
```

#### GET /analytics/trends
Get job posting trends over time.

**Parameters:**
- `days` (optional): Number of days (default: 30)

**Response:**
```json
{
  "trends": [
    {
      "date": "2025-11-20",
      "job_count": 1250,
      "company_count": 300
    }
  ]
}
```

#### GET /analytics/categories
Get job distribution by category.

**Response:**
```json
{
  "categories": [
    {
      "job_category": "Engineering",
      "count": 5000,
      "h1b_rate": 0.65
    }
  ]
}
```

#### GET /analytics/locations
Get top locations by job count.

**Parameters:**
- `limit` (optional): Number of results (default: 20)

**Response:**
```json
{
  "locations": [
    {
      "location": "San Francisco, CA",
      "job_count": 2500
    }
  ]
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Error message description"
}
```

**Common Status Codes:**
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

Currently no rate limiting. Will be implemented in production.

## Versioning

API version is included in the URL path (`/api/v1/`). Breaking changes will increment the version number.
