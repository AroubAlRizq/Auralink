# app/supabase/test_connection.py
"""
Simple test script to verify Supabase connection and imports.
Run this before the full example_usage.py to test your setup.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def test_imports():
    """Test that all imports work"""
    print("✓ Testing imports...")
    try:
        from app.supabase import (
            get_supabase_client,
            get_admin_client,
            MeetingService,
            FileService,
            ChunkService,
            SummaryService,
            UtteranceService,
            AsrJobService
        )
        print("  ✓ All service imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False


def test_env_vars():
    """Test that required environment variables are set"""
    print("\n✓ Testing environment variables...")
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_API_KEY",
        "DATABASE_URL"
    ]
    
    optional_vars = [
        "SUPABASE_SERVICE_ROLE_KEY",
        "OPENAI_API_KEY"
    ]
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {'*' * 20}... (set)")
        else:
            print(f"  ✗ {var}: NOT SET (required)")
            all_good = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {'*' * 20}... (set)")
        else:
            print(f"  ⚠ {var}: NOT SET (optional, but recommended)")
    
    return all_good


def test_supabase_connection():
    """Test connection to Supabase"""
    print("\n✓ Testing Supabase connection...")
    try:
        from app.supabase import get_supabase_client
        
        client = get_supabase_client()
        print("  ✓ Supabase client created successfully")
        
        # Try a simple query to test connection
        try:
            # This will test if we can connect to the database
            response = client.table("meetings").select("id").limit(1).execute()
            print("  ✓ Database connection successful")
            print(f"  ✓ Found {len(response.data)} meeting(s) in database")
            return True
        except Exception as e:
            error_msg = str(e)
            if "relation" in error_msg.lower() and "does not exist" in error_msg.lower():
                print("  ⚠ Database connection OK, but tables not created yet")
                print("  → Run app/supabase/sql/setup.sql in Supabase SQL Editor")
            else:
                print(f"  ✗ Database query failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"  ✗ Connection error: {e}")
        return False


def test_services():
    """Test that services can be instantiated"""
    print("\n✓ Testing service instantiation...")
    try:
        from app.supabase import (
            get_supabase_client,
            MeetingService,
            FileService,
            ChunkService,
            SummaryService,
            UtteranceService,
            AsrJobService
        )
        
        client = get_supabase_client()
        
        services = {
            "MeetingService": MeetingService(client),
            "FileService": FileService(client),
            "ChunkService": ChunkService(client),
            "SummaryService": SummaryService(client),
            "UtteranceService": UtteranceService(client),
            "AsrJobService": AsrJobService(client)
        }
        
        for name, service in services.items():
            print(f"  ✓ {name} instantiated successfully")
        
        return True
    except Exception as e:
        print(f"  ✗ Service instantiation error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Supabase Integration Test")
    print("=" * 60)
    
    results = []
    
    # Test 1: Imports
    results.append(("Imports", test_imports()))
    
    # Test 2: Environment variables
    results.append(("Environment Variables", test_env_vars()))
    
    # Test 3: Supabase connection (only if previous tests passed)
    if results[-1][1]:
        results.append(("Supabase Connection", test_supabase_connection()))
    
    # Test 4: Services (only if connection test passed or was skipped)
    if results[0][1]:  # If imports worked
        results.append(("Service Instantiation", test_services()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print(f"✅ All tests passed! ({passed}/{total})")
        print("\nYou can now run: python app/supabase/example_usage.py")
    else:
        print(f"⚠ Some tests failed ({passed}/{total} passed)")
        print("\nNext steps:")
        if not results[1][1]:  # Env vars failed
            print("1. Copy .env_example to .env")
            print("2. Fill in your Supabase credentials")
        print("3. Run app/supabase/sql/setup.sql in Supabase SQL Editor")
    print("=" * 60)


if __name__ == "__main__":
    main()

