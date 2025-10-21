import os
import psycopg2
from dotenv import load_dotenv
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class SupabaseClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        if not self.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set in .env file")
        
        self._connection = None
        logger.info("Supabase client initialized")
    
    def get_connection(self):
        """Get database connection with auto-reconnect"""
        try:
            if self._connection is None or self._connection.closed:
                self._connection = psycopg2.connect(
                    self.DATABASE_URL, 
                    connect_timeout=10
                )
                self._connection.autocommit = True
                logger.info("Database connection established")
            return self._connection
        except psycopg2.OperationalError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close_connection(self):
        """Close database connection"""
        if self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("Database connection closed")
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
                result = cursor.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[list]:
        """Execute a query and return results"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if cursor.description:  # If it's a SELECT query
                    return cursor.fetchall()
                return None
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

# Global instance
supabase = SupabaseClient()
