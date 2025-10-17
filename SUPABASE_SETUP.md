# Supabase Setup Guide for Auralink

Follow these steps to get your Supabase integration up and running.

## Step 1: Get Your Supabase Credentials

### 1.1 Go to Your Supabase Dashboard
1. Visit [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project (or create a new one)

### 1.2 Get Your Database URL
1. In the sidebar, click **Project Settings** (gear icon)
2. Click **Database** tab
3. Scroll down to **Connection string**
4. Select **URI** mode
5. Copy the connection string (looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`)
6. **Replace `[YOUR-PASSWORD]` with your actual database password**

### 1.3 Get Your Supabase API Keys
1. In the sidebar, click **Project Settings** (gear icon)
2. Click **API** tab
3. You'll see:
   - **Project URL** (e.g., `https://abcdefgh.supabase.co`)
   - **anon public** key (long string starting with `eyJ...`)
   - **service_role** key (long string starting with `eyJ...`)

## Step 2: Update Your .env File

Open the `.env` file in the project root and fill in your credentials:

```bash
# Database Connection (from Step 1.2)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

# Supabase Configuration (from Step 1.3)
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_KEY=eyJ...your_anon_key...
SUPABASE_SERVICE_ROLE_KEY=eyJ...your_service_role_key...

# OpenAI Configuration (if you have it)
OPENAI_API_KEY=sk-proj-...
OPENAI_EMBED_MODEL=text-embedding-3-large
OPENAI_MODEL=gpt-4o-mini

# Vector Database Configuration
PGVECTOR_DIM=3072
```

## Step 3: Set Up Your Database Schema

1. Go to your Supabase Dashboard
2. Click **SQL Editor** in the sidebar (</> icon)
3. Click **New Query**
4. Copy the contents of `app/supabase/sql/setup.sql`
5. Paste it into the SQL editor
6. Click **Run** (or press F5)

This will:
- ✅ Enable required extensions (uuid-ossp, pgvector)
- ✅ Create all tables (meetings, files, utterances, chunks, summaries, asr_jobs)
- ✅ Create indexes for performance
- ✅ Create triggers for auto-updating timestamps
- ✅ Create vector similarity search functions

## Step 4: Install Python Dependencies

```bash
# Make sure your virtual environment is activated
# (venv) should appear in your terminal

pip install -r requirements.txt
```

This will install:
- `supabase` - Supabase Python client
- All other required dependencies

## Step 5: Test Your Connection

```bash
python app/supabase/test_connection.py
```

You should see:
```
============================================================
Supabase Integration Test
============================================================
✓ Testing imports...
  ✓ All service imports successful

✓ Testing environment variables...
  ✓ SUPABASE_URL: ******************... (set)
  ✓ SUPABASE_KEY: ******************... (set)
  ✓ DATABASE_URL: ******************... (set)
  ...

✓ Testing Supabase connection...
  ✓ Supabase client created successfully
  ✓ Database connection successful
  ...

============================================================
✅ All tests passed!
============================================================
```

## Step 6: Run the Example

Once all tests pass, try the full example:

```bash
python app/supabase/example_usage.py
```

This will:
1. Create a sample meeting
2. Add file metadata
3. Track an ASR job
4. Create transcript utterances
5. Create chunks with embeddings
6. Perform semantic search
7. Create a meeting summary

## Troubleshooting

### Error: "No module named 'app'"
✅ **Fixed!** The scripts now handle the Python path automatically.

### Error: "SUPABASE_URL environment variable not set"
- Make sure your `.env` file exists in the project root
- Check that the variable names match exactly
- Try restarting your terminal/IDE

### Error: "relation 'meetings' does not exist"
- You need to run the SQL setup script (Step 3)
- Go to Supabase SQL Editor and run `app/supabase/sql/setup.sql`

### Error: "function match_chunks does not exist"
- Run the SQL setup script which includes the vector search functions
- Or run `app/supabase/sql/match_chunks.sql` separately

### Error: OpenAI API errors
- The embeddings are optional for basic testing
- To use semantic search, you'll need a valid OpenAI API key
- Get one at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Next Steps

Once everything is working:

1. **Explore the services** in `app/supabase/services/`
2. **Read the documentation** in `app/supabase/README.md`
3. **Review examples** in `app/supabase/example_usage.py`
4. **Integrate into your app** using the service classes

## Quick Reference

### Using in Your Code

```python
from app.supabase import get_supabase_client, MeetingService

# Create client
client = get_supabase_client()

# Create service
meeting_service = MeetingService(client)

# Create a meeting
meeting = meeting_service.create_meeting(
    title="My Meeting",
    consent=True
)

print(f"Created meeting: {meeting['id']}")
```

## Support

- **Documentation**: `app/supabase/README.md`
- **Architecture**: `app/supabase/STRUCTURE.md`
- **Examples**: `app/supabase/example_usage.py`
- **Test Script**: `app/supabase/test_connection.py`

---

Happy coding! 🚀

