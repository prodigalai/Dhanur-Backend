"""
Supabase service for interacting with Supabase database
"""

import json
import os
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_supabase_client():
    """Get Supabase client."""
    try:
        from supabase import create_client, Client
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')
        
        if not url or not key:
            print("❌ Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_ANON_KEY in .env")
            return None
            
        supabase: Client = create_client(url, key)
        return supabase
        
    except ImportError:
        print("❌ Supabase package not installed. Run: pip install supabase")
        return None
    except Exception as e:
        print(f"❌ Error creating Supabase client: {e}")
        return None

class SupabaseService:
    """Service for Supabase database operations"""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    def insert_record(self, table: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Insert a record into a specified table
        
        Args:
            table: Table name
            data: Data to insert
            
        Returns:
            Inserted record data or None if failed
        """
        try:
            result = self.client.table(table).insert(data).execute()
            if result.data:
                return result.data[0] if result.data else None
            return None
        except Exception as e:
            print(f"❌ Error inserting record into {table}: {str(e)}")
            return None
    
    def get_records(self, table: str, filters: Optional[Dict[str, Any]] = None, 
                   select: str = "*", limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get records from a specified table
        
        Args:
            table: Table name
            filters: Filter conditions
            select: Columns to select
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        try:
            query = self.client.table(table).select(select)
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error getting records from {table}: {str(e)}")
            return []
    
    def get_record(self, table: str, filters: Dict[str, Any], 
                   select: str = "*") -> Optional[Dict[str, Any]]:
        """
        Get a single record from a specified table
        
        Args:
            table: Table name
            filters: Filter conditions
            select: Columns to select
            
        Returns:
            Record data or None if not found
        """
        records = self.get_records(table, filters, select, limit=1)
        return records[0] if records else None
    
    def update_record(self, table: str, filters: Dict[str, Any], 
                     data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a record in a specified table
        
        Args:
            table: Table name
            filters: Filter conditions to identify record
            data: Data to update
            
        Returns:
            Updated record data or None if failed
        """
        try:
            query = self.client.table(table).update(data)
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            if result.data:
                return result.data[0] if result.data else None
            return None
        except Exception as e:
            print(f"❌ Error updating record in {table}: {str(e)}")
            return None
    
    def delete_record(self, table: str, filters: Dict[str, Any]) -> bool:
        """
        Delete a record from a specified table
        
        Args:
            table: Table name
            filters: Filter conditions to identify record
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            query = self.client.table(table).delete()
            
            for key, value in filters.items():
                query = query.eq(key, value)
            
            result = query.execute()
            return True
        except Exception as e:
            print(f"❌ Error deleting record from {table}: {str(e)}")
            return False
    
    def count_records(self, table: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records in a table
        
        Args:
            table: Table name
            filters: Filter conditions
            
        Returns:
            Number of records
        """
        try:
            query = self.client.table(table).select("*", count="exact")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            result = query.execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            print(f"❌ Error counting records in {table}: {str(e)}")
            return 0
    
    def execute_rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a stored procedure/function
        
        Args:
            function_name: Name of the function to execute
            params: Parameters to pass to the function
            
        Returns:
            Function result
        """
        try:
            if params is None:
                params = {}
            
            result = self.client.rpc(function_name, params).execute()
            return result.data
        except Exception as e:
            print(f"❌ Error executing RPC {function_name}: {str(e)}")
            return None
    
    def upsert_record(self, table: str, data: Dict[str, Any], 
                     conflict_columns: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Insert or update a record (upsert)
        
        Args:
            table: Table name
            data: Data to upsert
            conflict_columns: Columns to check for conflicts
            
        Returns:
            Upserted record data or None if failed
        """
        try:
            query = self.client.table(table).upsert(data)
            
            if conflict_columns:
                # Supabase Python client handles conflict resolution automatically
                pass
            
            result = query.execute()
            if result.data:
                return result.data[0] if result.data else None
            return None
        except Exception as e:
            print(f"❌ Error upserting record in {table}: {str(e)}")
            return None
    
    def bulk_insert(self, table: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Insert multiple records at once
        
        Args:
            table: Table name
            data: List of records to insert
            
        Returns:
            List of inserted records
        """
        try:
            result = self.client.table(table).insert(data).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error bulk inserting records into {table}: {str(e)}")
            return []
    
    def search_records(self, table: str, column: str, search_term: str,
                      additional_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search records using text search
        
        Args:
            table: Table name
            column: Column to search in
            search_term: Term to search for
            additional_filters: Additional filter conditions
            
        Returns:
            List of matching records
        """
        try:
            query = self.client.table(table).select("*").ilike(column, f"%{search_term}%")
            
            if additional_filters:
                for key, value in additional_filters.items():
                    query = query.eq(key, value)
            
            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error searching records in {table}: {str(e)}")
            return []
    
    def get_records_with_pagination(self, table: str, page: int = 1, limit: int = 10,
                                   filters: Optional[Dict[str, Any]] = None,
                                   order_by: Optional[str] = None,
                                   ascending: bool = True) -> Dict[str, Any]:
        """
        Get records with pagination
        
        Args:
            table: Table name
            page: Page number (1-based)
            limit: Records per page
            filters: Filter conditions
            order_by: Column to order by
            ascending: Order direction
            
        Returns:
            Dictionary with records and pagination info
        """
        try:
            # Calculate offset
            offset = (page - 1) * limit
            
            # Build query
            query = self.client.table(table).select("*")
            
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            if order_by:
                query = query.order(order_by, desc=not ascending)
            
            # Get total count
            count_query = self.client.table(table).select("*", count="exact")
            if filters:
                for key, value in filters.items():
                    count_query = count_query.eq(key, value)
            
            count_result = count_query.execute()
            total_count = count_result.count if count_result.count is not None else 0
            
            # Get paginated data
            result = query.range(offset, offset + limit - 1).execute()
            records = result.data if result.data else []
            
            return {
                "records": records,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total_count,
                    "pages": (total_count + limit - 1) // limit if limit > 0 else 0
                }
            }
        except Exception as e:
            print(f"❌ Error getting paginated records from {table}: {str(e)}")
            return {
                "records": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "pages": 0
                }
            }
