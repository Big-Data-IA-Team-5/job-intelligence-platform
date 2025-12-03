"""
API Client for backend communication
"""
import requests
from typing import Optional, Dict, Any
import os


class APIClient:
    """Client for communicating with the backend API"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("BACKEND_URL", "http://localhost:8000")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def _url(self, endpoint: str) -> str:
        """Build full URL for endpoint"""
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
        
        # If endpoint already has /api prefix, use as-is
        # Otherwise, add /api/v1 prefix for analytics endpoints
        if endpoint.startswith("/api/"):
            return f"{self.base_url}{endpoint}"
        else:
            return f"{self.base_url}/api/v1{endpoint}"
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request"""
        try:
            response = self.session.get(self._url(endpoint), params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"GET request failed with HTTP error: {e.response.status_code}")
            return {"error": str(e), "status_code": e.response.status_code}
        except requests.exceptions.RequestException as e:
            print(f"GET request failed: {str(e)}")
            return {"error": str(e)}
    
    def post(self, endpoint: str, json: Optional[Dict] = None, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make POST request"""
        try:
            response = self.session.post(self._url(endpoint), json=json, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"POST request failed with HTTP error: {e.response.status_code} - {e.response.text}")
            return {"error": str(e), "status_code": e.response.status_code, "detail": e.response.text}
        except requests.exceptions.RequestException as e:
            print(f"POST request failed: {str(e)}")
            return {"error": str(e)}
    
    def put(self, endpoint: str, json: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make PUT request"""
        try:
            response = self.session.put(self._url(endpoint), json=json)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"PUT request failed: {str(e)}")
            return None
    
    def delete(self, endpoint: str) -> bool:
        """Make DELETE request"""
        try:
            response = self.session.delete(self._url(endpoint))
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"DELETE request failed: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """Check if backend is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
