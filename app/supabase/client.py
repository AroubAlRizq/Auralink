# app/supabase/client.py
"""
Supabase client initialization and configuration.
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv() 

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_API_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL environment variable not set. "
        "Please check your .env file."
    )

if not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_KEY environment variable not set. "
        "Please check your .env file."
    )


def get_supabase_client() -> Client:
    """
    Get Supabase client instance with anon key (for user-level operations).
    
    Returns:
        Client: Supabase client instance
    """
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_admin_client() -> Client:
    """
    Get Supabase client instance with service role key (for admin operations).
    Use this for operations that bypass Row Level Security (RLS).
    
    Returns:
        Client: Supabase admin client instance
    """
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY environment variable not set. "
            "This is required for admin operations."
        )
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


# Singleton instances (optional, for convenience)
_client: Optional[Client] = None
_admin_client: Optional[Client] = None


def get_client(use_admin: bool = False) -> Client:
    """
    Get cached Supabase client instance.
    
    Args:
        use_admin: If True, returns admin client with service role key
        
    Returns:
        Client: Supabase client instance
    """
    global _client, _admin_client
    
    if use_admin:
        if _admin_client is None:
            _admin_client = get_admin_client()
        return _admin_client
    else:
        if _client is None:
            _client = get_supabase_client()
        return _client

