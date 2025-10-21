-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Meetings table
CREATE TABLE IF NOT EXISTS meetings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  video_url TEXT,
  status TEXT DEFAULT 'processing'
);

-- ASR job tracking
CREATE TABLE IF NOT EXISTS asr_jobs (
  job_id TEXT PRIMARY KEY,
  meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
  provider TEXT,
  status TEXT DEFAULT 'processing',
  callback_url TEXT,
  raw JSONB,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Utterances (raw diarized transcript)
CREATE TABLE IF NOT EXISTS utterances (
  id BIGSERIAL PRIMARY KEY,
  meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
  speaker TEXT,
  start_seconds DOUBLE PRECISION,
  end_seconds DOUBLE PRECISION,
  text TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Summaries (structured JSON)
CREATE TABLE IF NOT EXISTS summaries (
  meeting_id UUID PRIMARY KEY REFERENCES meetings(id) ON DELETE CASCADE,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RAG chunks with embeddings
-- ✅ MUST BE 1536 dimensions for Supabase
CREATE TABLE IF NOT EXISTS chunks (
  id BIGSERIAL PRIMARY KEY,
  meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
  speaker TEXT,
  start_seconds DOUBLE PRECISION,
  end_seconds DOUBLE PRECISION,
  text TEXT,
  topic TEXT,
  source TEXT DEFAULT 'transcript',
  embedding VECTOR(1536),  -- ✅ Changed from 3072 to 1536
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Regular indexes
CREATE INDEX IF NOT EXISTS idx_chunks_meeting ON chunks(meeting_id);
CREATE INDEX IF NOT EXISTS idx_chunks_topic ON chunks(topic);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);
CREATE INDEX IF NOT EXISTS idx_utterances_meeting ON utterances(meeting_id);
CREATE INDEX IF NOT EXISTS idx_asr_jobs_meeting ON asr_jobs(meeting_id);

-- Vector similarity index (HNSW works better than IVFFlat on Supabase)
CREATE INDEX IF NOT EXISTS idx_chunks_vector ON chunks 
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);