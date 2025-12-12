"""
Integration Tests for Backend + Snowflake
Tests the complete data flow from API to database
"""
import pytest
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.utils.agent_wrapper import AgentManager


@pytest.mark.integration
class TestSnowflakeConnection:
    """Test Snowflake database connectivity."""
    
    def test_agent_manager_singleton(self):
        """Test AgentManager singleton pattern."""
        agent1 = AgentManager.get_search_agent()
        agent2 = AgentManager.get_search_agent()
        assert agent1 is agent2
    
    def test_database_connection(self):
        """Test Snowflake database connection."""
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT CURRENT_VERSION()")
        result = cursor.fetchone()
        assert result is not None
        
        cursor.close()
    
    def test_schema_exists(self):
        """Test that required database schema exists."""
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        # Check database and schema
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        # Check table exists
        cursor.execute("SHOW TABLES LIKE 'jobs_processed'")
        tables = cursor.fetchall()
        assert len(tables) > 0
        
        cursor.close()


@pytest.mark.integration
class TestJobsProcessedTable:
    """Test jobs_processed table data quality."""
    
    def test_table_has_data(self):
        """Test that jobs_processed table has data."""
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        cursor.execute("SELECT COUNT(*) FROM jobs_processed")
        
        count = cursor.fetchone()[0]
        assert count > 0
        cursor.close()
    
    def test_required_columns_exist(self):
        """Test that all required columns exist."""
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        cursor.execute("SELECT * FROM jobs_processed LIMIT 1")
        
        columns = [col[0].lower() for col in cursor.description]
        required_columns = [
            'job_id', 'title', 'company', 'location', 
            'salary_min', 'salary_max', 'h1b_sponsor'
        ]
        
        for col in required_columns:
            assert col in columns, f"Missing required column: {col}"
        
        cursor.close()
    
    def test_data_quality(self):
        """Test basic data quality checks."""
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        # Check for jobs with title and company
        cursor.execute("""
            SELECT COUNT(*) 
            FROM jobs_processed 
            WHERE title IS NOT NULL AND company IS NOT NULL
        """)
        valid_jobs = cursor.fetchone()[0]
        assert valid_jobs > 0
        
        cursor.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
