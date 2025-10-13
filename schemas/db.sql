-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Meetings (created by ingestion owner; you can create now)
CREATE TABLE IF NOT EXISTS meetings (
  id UUID PRIMARY KEY,
  title TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  video_url TEXT,
  status TEXT DEFAULT 'processing'
);

-- Utterances (raw diarized ASR) — owner A will fill; you can create now
CREATE TABLE IF NOT EXISTS utterances (
  id BIGSERIAL PRIMARY KEY,
  meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
  speaker TEXT,
  start_seconds DOUBLE PRECISION,
  end_seconds DOUBLE PRECISION,
  text TEXT
);

-- Summaries (structured JSON) — owner B will fill
CREATE TABLE IF NOT EXISTS summaries (
  meeting_id UUID PRIMARY KEY REFERENCES meetings(id) ON DELETE CASCADE,
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- RAG chunks (your ownership)
-- NOTE: adjust dimension to your embedding model (OpenAI = 3072, Voyage varies)
CREATE TABLE IF NOT EXISTS chunks (
  id BIGSERIAL PRIMARY KEY,
  meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
  speaker TEXT,
  start_seconds DOUBLE PRECISION,
  end_seconds DOUBLE PRECISION,
  text TEXT,
  topic TEXT,
  source TEXT DEFAULT 'transcript', -- or 'summary'
  embedding VECTOR(3072)            -- <- change to match model dim
);

CREATE INDEX IF NOT EXISTS idx_chunks_meeting ON chunks(meeting_id);
CREATE INDEX IF NOT EXISTS idx_chunks_topic ON chunks(topic);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);
CREATE INDEX IF NOT EXISTS idx_chunks_vector ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

