# test_db_simple.py
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

async def test():
    load_dotenv()
    
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ DATABASE_URL not set in .env")
        return
    
    # Extract hostname for display
    try:
        if "@" in db_url:
            hostname = db_url.split("@")[1].split(":")[0]
            print(f"📡 Attempting to connect to: {hostname}")
        else:
            print(f"📡 Attempting to connect...")
    except:
        print(f"📡 Attempting to connect...")
    
    try:
        print("Connecting...")
        conn = await asyncpg.connect(db_url)
        
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        print("✅ CONNECTION SUCCESSFUL!")
        return True
        
    except asyncpg.InvalidPasswordError:
        print("❌ Invalid password - check your .env DATABASE_URL")
        return False
        
    except Exception as e:
        print(f"❌ Connection failed: {type(e).__name__}")
        print(f"Error: {e}")
        
        # Troubleshooting hints
        if "getaddrinfo failed" in str(e) or "11001" in str(e):
            print("\n🔧 TROUBLESHOOTING:")
            print("1. Check your internet connection")
            print("2. Verify DATABASE_URL in .env is correct")
            print("3. Make sure URL doesn't have [YOUR-PASSWORD] placeholder")
            print("4. Try disabling VPN if you have one")
            print("5. Check if firewall is blocking port 6543 or 5432")
        
        return False

if __name__ == "__main__":
    asyncio.run(test())