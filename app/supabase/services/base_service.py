# app/supabase/services/base_service.py
"""
Base service class with common CRUD operations for Supabase tables.
"""

from typing import List, Dict, Any, Optional
from supabase import Client


class BaseService:
    """
    Base service class providing common database operations.
    All model-specific services inherit from this class.
    """
    
    def __init__(self, client: Client, table_name: str):
        """
        Initialize base service.
        
        Args:
            client: Supabase client instance
            table_name: Name of the table in Supabase
        """
        self.client = client
        self.table_name = table_name
        self.table = client.table(table_name)
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new record. 
        
        Args:
            data: Dictionary containing record data
            
        Returns:
            Created record as dictionary
        """
        response = self.table.insert(data).execute()
        return response.data[0] if response.data else None
    
    def create_many(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple records at once.
        
        Args:
            data: List of dictionaries containing record data
            
        Returns:
            List of created records
        """
        response = self.table.insert(data).execute()
        return response.data if response.data else []
    
    def get_by_id(self, id_value: Any, id_column: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get a single record by ID.
        
        Args:
            id_value: ID value to search for
            id_column: Name of the ID column (default: "id")
            
        Returns:
            Record as dictionary or None if not found
        """
        response = self.table.select("*").eq(id_column, id_value).execute()
        return response.data[0] if response.data else None
    
    def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all records from the table.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of records
        """
        query = self.table.select("*")
        
        if limit is not None:
            query = query.limit(limit)
        
        if offset is not None:
            query = query.offset(offset)
        
        response = query.execute()
        return response.data if response.data else []
    
    def update(self, id_value: Any, data: Dict[str, Any], id_column: str = "id") -> Dict[str, Any]:
        """
        Update a record by ID.
        
        Args:
            id_value: ID value of record to update
            data: Dictionary containing fields to update
            id_column: Name of the ID column (default: "id")
            
        Returns:
            Updated record as dictionary
        """
        response = self.table.update(data).eq(id_column, id_value).execute()
        return response.data[0] if response.data else None
    
    def delete(self, id_value: Any, id_column: str = "id") -> bool:
        """
        Delete a record by ID.
        
        Args:
            id_value: ID value of record to delete
            id_column: Name of the ID column (default: "id")
            
        Returns:
            True if successful, False otherwise
        """
        response = self.table.delete().eq(id_column, id_value).execute()
        return len(response.data) > 0 if response.data else False
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in the table.
        
        Args:
            filters: Optional dictionary of column=value filters
            
        Returns:
            Number of records
        """
        query = self.table.select("*", count="exact")
        
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        
        response = query.execute()
        return response.count if hasattr(response, 'count') else 0
    
    def filter(self, filters: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Filter records by multiple columns.
        
        Args:
            filters: Dictionary of column=value filters
            limit: Maximum number of records to return
            
        Returns:
            List of matching records
        """
        query = self.table.select("*")
        
        for column, value in filters.items():
            query = query.eq(column, value)
        
        if limit is not None:
            query = query.limit(limit)
        
        response = query.execute()
        return response.data if response.data else []
    
    def order_by(self, column: str, ascending: bool = True, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get records ordered by a column.
        
        Args:
            column: Column name to order by
            ascending: If True, order ascending; if False, descending
            limit: Maximum number of records to return
            
        Returns:
            List of ordered records
        """
        query = self.table.select("*").order(column, desc=not ascending)
        
        if limit is not None:
            query = query.limit(limit)
        
        response = query.execute()
        return response.data if response.data else []

