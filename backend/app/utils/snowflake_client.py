"""
Snowflake Client Utility
"""
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd
from typing import List, Any, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class SnowflakeClient:
    """Snowflake database client"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish connection to Snowflake"""
        try:
            self.connection = snowflake.connector.connect(
                account=settings.SNOWFLAKE_ACCOUNT,
                user=settings.SNOWFLAKE_USER,
                password=settings.SNOWFLAKE_PASSWORD,
                warehouse=settings.SNOWFLAKE_WAREHOUSE,
                database=settings.SNOWFLAKE_DATABASE,
                schema=settings.SNOWFLAKE_SCHEMA,
                role=settings.SNOWFLAKE_ROLE
            )
            logger.info("Connected to Snowflake successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise
    
    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """
        Execute a query and return results as DataFrame
        
        Args:
            query: SQL query string
            params: Query parameters for parameterized queries
            
        Returns:
            DataFrame with query results
        """
        try:
            if not self.connection or self.connection.is_closed():
                self.connect()
            
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Fetch results
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                data = cursor.fetchall()
                df = pd.DataFrame(data, columns=columns)
            else:
                df = pd.DataFrame()
            
            cursor.close()
            return df
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def execute_many(self, query: str, data: List[tuple]):
        """Execute a query with multiple parameter sets"""
        try:
            if not self.connection or self.connection.is_closed():
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.executemany(query, data)
            self.connection.commit()
            cursor.close()
            
        except Exception as e:
            logger.error(f"Bulk execution failed: {str(e)}")
            self.connection.rollback()
            raise
    
    def write_dataframe(self, df: pd.DataFrame, table_name: str, schema: str = None):
        """Write DataFrame to Snowflake table"""
        try:
            if not self.connection or self.connection.is_closed():
                self.connect()
            
            schema = schema or settings.SNOWFLAKE_SCHEMA
            
            success, nchunks, nrows, _ = write_pandas(
                conn=self.connection,
                df=df,
                table_name=table_name,
                database=settings.SNOWFLAKE_DATABASE,
                schema=schema,
                auto_create_table=False,
                overwrite=False
            )
            
            return success, nrows
            
        except Exception as e:
            logger.error(f"DataFrame write failed: {str(e)}")
            raise
    
    def close(self):
        """Close connection"""
        if self.connection and not self.connection.is_closed():
            self.connection.close()
            logger.info("Snowflake connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Singleton instance
_client = None


def get_snowflake_client() -> SnowflakeClient:
    """Get or create Snowflake client instance"""
    global _client
    if _client is None or _client.connection.is_closed():
        _client = SnowflakeClient()
    return _client
