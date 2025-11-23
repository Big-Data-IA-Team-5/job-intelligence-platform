"""
Agent 1: Job Search (Without Cortex Analyst)
Simple natural language to SQL conversion
"""
import snowflake.connector
import re
import os
import json
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv


class JobSearchAgent:
    def __init__(self):
        # Try to load from .env first
        env_path = Path(__file__).parent.parent.parent / 'config' / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            account = os.getenv('SNOWFLAKE_ACCOUNT')
        else:
            # Fallback to secrets.json
            secrets_path = Path(__file__).parent.parent.parent / 'secrets.json'
            with open(secrets_path, 'r') as f:
                secrets = json.load(f)
            sf_config = secrets['snowflake']
            account = sf_config['account']
            os.environ['SNOWFLAKE_USER'] = sf_config['user']
            os.environ['SNOWFLAKE_PASSWORD'] = sf_config['password']
            os.environ['SNOWFLAKE_DATABASE'] = sf_config['database']
            os.environ['SNOWFLAKE_WAREHOUSE'] = sf_config['warehouse']
        
        # Connect using credentials
        self.conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            database=os.getenv('SNOWFLAKE_DATABASE', 'job_intelligence'),
            schema='processed',  # Always use processed schema for queries
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'compute_wh')
        )
    
    def search(self, query: str, filters: dict = None) -> Dict:
        """
        Search jobs using natural language or filters.
        
        Args:
            query: Natural language query or keywords
            filters: Optional dict with visa_status, location, salary_min, job_type
            
        Returns:
            {"status": "success", "jobs": [...], "total": int, "sql": "..."}
        """
        # Validate query
        if not query or not query.strip():
            return {
                "status": "error",
                "error": "Query cannot be empty"
            }
        
        cursor = self.conn.cursor()
        
        try:
            # Build SQL based on query and filters
            sql = self._build_sql(query, filters or {})
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return {
                "status": "success",
                "query": query,
                "sql": sql,
                "jobs": results,
                "total": len(results)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }
        
        finally:
            cursor.close()
    
    def _build_sql(self, query: str, filters: dict) -> str:
        """Build SQL query from natural language."""
        query_lower = query.lower()
        
        # Base SQL
        sql = """
            SELECT 
                job_id,
                url,
                title,
                company_clean as company,
                location,
                description,
                salary_min,
                salary_max,
                job_type,
                visa_category,
                h1b_sponsor,
                days_since_posted
            FROM jobs_processed
            WHERE 1=1
        """
        
        # Extract visa category from query
        if 'cpt' in query_lower or 'intern' in query_lower:
            sql += " AND (visa_category = 'CPT' OR job_type = 'Internship')"
        elif 'opt' in query_lower or 'new grad' in query_lower:
            sql += " AND visa_category = 'OPT'"
        elif 'h-1b' in query_lower or 'h1b' in query_lower or 'sponsor' in query_lower:
            sql += " AND (h1b_sponsor = TRUE OR visa_category = 'H-1B')"
        
        # Extract location from query
        location_match = re.search(r'in\s+([A-Za-z\s]+?)(?:\s|$)', query_lower)
        if location_match:
            location = location_match.group(1).strip()
            sql += f" AND location ILIKE '%{location}%'"
        
        # Extract job title keywords
        title_keywords = []
        if 'software' in query_lower or 'engineer' in query_lower:
            title_keywords.append('engineer')
        if 'data' in query_lower and 'analyst' in query_lower:
            title_keywords.append('data analyst')
        if 'data' in query_lower and 'engineer' in query_lower:
            title_keywords.append('data engineer')
        
        if title_keywords:
            conditions = " OR ".join([f"title ILIKE '%{kw}%'" for kw in title_keywords])
            sql += f" AND ({conditions})"
        
        # Apply additional filters
        if filters.get('visa_status'):
            sql += f" AND visa_category = '{filters['visa_status']}'"
        
        if filters.get('location'):
            sql += f" AND location ILIKE '%{filters['location']}%'"
        
        if filters.get('salary_min'):
            sql += f" AND salary_min >= {filters['salary_min']}"
        
        if filters.get('job_type'):
            sql += f" AND job_type = '{filters['job_type']}'"
        
        # Order and limit
        sql += " ORDER BY days_since_posted ASC, title LIMIT 20"
        
        return sql
    
    def close(self):
        self.conn.close()


# Test
if __name__ == "__main__":
    agent = JobSearchAgent()
    
    # Test queries
    test_queries = [
        "Show me all jobs",
        "CPT internships in Boston",
        "Find H-1B sponsors",
        "Data engineer jobs",
        "Software engineer intern"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        result = agent.search(query)
        
        if result['status'] == 'success':
            print(f"✅ Found {result['total']} jobs")
            for job in result['jobs']:
                print(f"   - {job['TITLE']} at {job['COMPANY']} ({job['LOCATION']})")
        else:
            print(f"❌ Error: {result['error']}")
    
    agent.close()