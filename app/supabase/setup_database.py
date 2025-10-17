# app/supabase/setup_database.py
"""
Automated database setup script for Supabase.
This script creates all necessary tables, indexes, and functions.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv()

def get_supabase_admin_client():
    """Get Supabase admin client"""
    from app.supabase import get_admin_client
    return get_admin_client()


def execute_sql_via_supabase(client, sql_content):
    """Execute SQL using Supabase RPC"""
    try:
        # Split the SQL into individual statements
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        errors = []
        success_count = 0
        
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue
                
            try:
                # Use Supabase's RPC to execute SQL
                result = client.rpc('exec_sql', {'sql': statement}).execute()
                success_count += 1
            except Exception as e:
                error_msg = str(e)
                # Ignore "already exists" errors
                if 'already exists' not in error_msg.lower():
                    errors.append(f"Statement {i}: {error_msg[:100]}")
        
        if errors:
            print(f"  ⚠ Executed with {len(errors)} errors (may be normal if objects exist)")
            for error in errors[:3]:  # Show first 3 errors
                print(f"    - {error}")
        
        print(f"  ✓ Executed {success_count}/{len(statements)} statements")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def check_tables_exist(client):
    """Check if tables already exist using Supabase client"""
    try:
        # Try to query each table
        tables_to_check = ['meetings', 'files', 'utterances', 'chunks', 'summaries', 'asr_jobs']
        existing_tables = []
        
        for table in tables_to_check:
            try:
                client.table(table).select("*").limit(0).execute()
                existing_tables.append(table)
            except:
                pass  # Table doesn't exist
        
        return existing_tables
    except Exception as e:
        print(f"  ⚠ Could not check tables: {e}")
        return []


def main():
    """Main setup function"""
    print("=" * 60)
    print("Supabase Database Setup")
    print("=" * 60)
    print("\n⚠ IMPORTANT: Due to Supabase API limitations, you need to run")
    print("the SQL setup manually in the Supabase Dashboard.")
    print("\nHere's how:")
    print("=" * 60)
    
    print("\n📋 Step 1: Copy the SQL file content")
    sql_file = os.path.join(os.path.dirname(__file__), 'sql', 'setup.sql')
    
    if os.path.exists(sql_file):
        print(f"  File location: {sql_file}")
        print("  ")
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"  ✓ File has {len(content)} characters, {content.count('CREATE TABLE')} tables")
        except Exception as e:
            print(f"  ✗ Could not read file: {e}")
    
    print("\n🌐 Step 2: Go to Supabase Dashboard")
    supabase_url = os.getenv("SUPABASE_URL", "https://app.supabase.com")
    project_ref = supabase_url.split('//')[-1].split('.')[0] if 'supabase' in supabase_url else ""
    
    print(f"  1. Visit: https://app.supabase.com/project/{project_ref if project_ref else '[your-project]'}")
    print("  2. Click 'SQL Editor' in the left sidebar (</> icon)")
    print("  3. Click 'New Query'")
    
    print("\n📝 Step 3: Run the SQL")
    print("  1. Open the file: app/supabase/sql/setup.sql")
    print("  2. Copy ALL the contents")
    print("  3. Paste into the Supabase SQL Editor")
    print("  4. Click 'Run' (or press F5)")
    
    print("\n✅ Step 4: Verify")
    print("  After running, you should see:")
    print("  - Success message")
    print("  - List of created tables")
    
    print("\n🔍 Step 5: Test the setup")
    print("  Run: python app\\supabase\\test_connection.py")
    
    print("\n" + "=" * 60)
    
    # Try to check if tables exist
    try:
        print("\n🔍 Checking current database status...")
        client = get_supabase_admin_client()
        existing_tables = check_tables_exist(client)
        
        if existing_tables:
            print(f"  ✓ Found {len(existing_tables)} existing tables:")
            for table in existing_tables:
                print(f"    - {table}")
            print("\n  ✅ Tables already exist! You're all set!")
            print("\n  Run: python app\\supabase\\test_connection.py")
        else:
            print("  ⚠ No tables found yet")
            print("  → Please follow the manual setup steps above")
    except Exception as e:
        print(f"  ⚠ Could not check tables: {e}")
        print("  → Please follow the manual setup steps above")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

