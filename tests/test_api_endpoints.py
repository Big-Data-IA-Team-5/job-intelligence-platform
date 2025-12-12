"""
API Endpoint Tests
Tests all backend REST API endpoints for correctness and data quality
"""
import pytest
import requests
from typing import Dict

# Configuration
BACKEND_URL = "https://job-intelligence-backend-97083220044.us-central1.run.app"


class TestJobSearchAPI:
    """Test /api/jobs/search endpoint."""
    
    def test_basic_search(self):
        """Test basic job search without filters."""
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) <= 10
    
    def test_search_with_location(self):
        """Test search with location filter."""
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"locations": ["Boston, MA"], "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        # Verify location filtering works
        if len(data["jobs"]) > 0:
            assert any("Boston" in job.get("location", "") for job in data["jobs"])
    
    def test_search_with_company(self):
        """Test search with company filter."""
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"companies": ["Amazon"], "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        if len(data["jobs"]) > 0:
            assert any("Amazon" in job.get("company", "") for job in data["jobs"])
    
    def test_search_with_date_filter(self):
        """Test search with posted_within_days filter."""
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"posted_within_days": 7, "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
    
    def test_search_with_visa_filter(self):
        """Test search with H-1B sponsorship filter."""
        response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"visa_sponsorship": "Yes", "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
    
    def test_pagination(self):
        """Test pagination with offset and limit."""
        # Get first page
        response1 = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"limit": 10, "offset": 0}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Get second page
        response2 = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"limit": 10, "offset": 10}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify pagination metadata
        assert "pagination" in data1
        assert data1["pagination"]["offset"] == 0
        assert data2["pagination"]["offset"] == 10
        
        # Verify different results
        if len(data1["jobs"]) > 0 and len(data2["jobs"]) > 0:
            assert data1["jobs"][0]["job_id"] != data2["jobs"][0]["job_id"]
    
    def test_sorting(self):
        """Test different sort options."""
        sort_options = ["most_recent", "highest_salary", "company_az", "h1b_rate"]
        
        for sort_by in sort_options:
            response = requests.post(
                f"{BACKEND_URL}/api/jobs/search",
                json={"sort_by": sort_by, "limit": 5}
            )
            assert response.status_code == 200
            data = response.json()
            assert "jobs" in data


class TestFilterOptionsAPI:
    """Test filter options endpoints."""
    
    def test_get_companies(self):
        """Test /api/jobs/companies endpoint."""
        response = requests.get(f"{BACKEND_URL}/api/jobs/companies")
        assert response.status_code == 200
        data = response.json()
        assert "companies" in data
        assert len(data["companies"]) > 0
        # Verify structure
        assert "name" in data["companies"][0]
        assert "job_count" in data["companies"][0]
    
    def test_get_locations(self):
        """Test /api/jobs/locations endpoint."""
        response = requests.get(f"{BACKEND_URL}/api/jobs/locations")
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        assert len(data["locations"]) > 0
        # Verify structure
        assert "name" in data["locations"][0]
        assert "job_count" in data["locations"][0]


class TestJobDetailsAPI:
    """Test job details endpoint."""
    
    def test_get_job_by_id(self):
        """Test /api/jobs/{job_id} endpoint."""
        # First get a job ID
        search_response = requests.post(
            f"{BACKEND_URL}/api/jobs/search",
            json={"limit": 1}
        )
        assert search_response.status_code == 200
        jobs = search_response.json()["jobs"]
        
        if len(jobs) > 0:
            job_id = jobs[0]["job_id"]
            
            # Get job details
            detail_response = requests.get(f"{BACKEND_URL}/api/jobs/{job_id}")
            assert detail_response.status_code == 200
            job_data = detail_response.json()
            assert job_data["job_id"] == job_id
            assert "title" in job_data
            assert "company" in job_data


class TestAnalyticsAPI:
    """Test analytics endpoints."""
    
    def test_get_stats(self):
        """Test /api/analytics/stats endpoint."""
        response = requests.get(f"{BACKEND_URL}/api/analytics/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_jobs" in data
        assert "avg_salary" in data
        assert "top_companies" in data
        assert data["total_jobs"] > 0
    
    def test_get_company_stats(self):
        """Test /api/analytics/companies endpoint."""
        response = requests.get(f"{BACKEND_URL}/api/analytics/companies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "company" in data[0]
            assert "job_count" in data[0]
    
    def test_get_location_stats(self):
        """Test /api/analytics/locations endpoint."""
        response = requests.get(f"{BACKEND_URL}/api/analytics/locations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "location" in data[0]
            assert "job_count" in data[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
