-- Complete Supabase Setup SQL (CORRECTED VERSION)
-- Run this script in your Supabase SQL Editor to set up the complete schema

-- ============================================================================
-- 1. Enable Required Extensions
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 2. Create Tables
-- ============================================================================

-- Meetings table
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    video_url TEXT,
    consent BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'uploaded',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT meetings_status_check CHECK (status IN ('uploaded', 'asr_started', 'asr_done', 'indexed', 'summarized', 'error'))
);

-- Files table
CREATE TABLE IF NOT EXISTS files (
    id BIGSERIAL PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    public_url TEXT,
    kind TEXT NOT NULL,
    size_bytes BIGINT,
    mime_type TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT files_kind_check CHECK (kind IN ('upload', 'narration', 'summary', 'other'))
);

-- Utterances table (ASR transcription segments)
CREATE TABLE IF NOT EXISTS utterances (
    id BIGSERIAL PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    speaker TEXT NOT NULL,
    start_seconds DOUBLE PRECISION NOT NULL,
    end_seconds DOUBLE PRECISION NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Chunks table (text segments with embeddings for RAG)
CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    speaker TEXT,
    start_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    end_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
    topic TEXT,
    text TEXT NOT NULL,
    embedding vector(3072),  -- 3072 for text-embedding-3-large
    source TEXT DEFAULT 'transcript',  -- ⭐ ADDED: transcript, multimodal, summary
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT chunks_source_check CHECK (source IN ('transcript', 'multimodal', 'summary'))
);

-- Summaries table (structured meeting summaries)
CREATE TABLE IF NOT EXISTS summaries (
    meeting_id UUID PRIMARY KEY REFERENCES meetings(id) ON DELETE CASCADE,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- ASR Jobs table (tracks ASR processing jobs)
CREATE TABLE IF NOT EXISTS asr_jobs (
    id TEXT PRIMARY KEY,  -- Provider job ID
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    callback_url TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    error TEXT,
    raw JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT asr_jobs_status_check CHECK (status IN ('queued', 'processing', 'completed', 'error'))
);

-- ============================================================================
-- 3. Create Indexes for Performance
-- ============================================================================

-- Meetings indexes
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meetings(status);
CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meetings(created_at DESC);

-- Files indexes
CREATE INDEX IF NOT EXISTS idx_files_meeting_id ON files(meeting_id);
CREATE INDEX IF NOT EXISTS idx_files_kind ON files(kind);

-- Utterances indexes
CREATE INDEX IF NOT EXISTS idx_utterances_meeting_id ON utterances(meeting_id);
CREATE INDEX IF NOT EXISTS idx_utterances_meeting_start ON utterances(meeting_id, start_seconds);

-- Chunks indexes
CREATE INDEX IF NOT EXISTS idx_chunks_meeting_id ON chunks(meeting_id);
CREATE INDEX IF NOT EXISTS idx_chunks_meeting_start ON chunks(meeting_id, start_seconds);
CREATE INDEX IF NOT EXISTS idx_chunks_topic ON chunks(topic);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);  -- ⭐ ADDED

-- ASR Jobs indexes
CREATE INDEX IF NOT EXISTS idx_asr_jobs_meeting_id ON asr_jobs(meeting_id);
CREATE INDEX IF NOT EXISTS idx_asr_jobs_status ON asr_jobs(status);
CREATE INDEX IF NOT EXISTS idx_asr_jobs_provider ON asr_jobs(provider);

-- ============================================================================
-- 4. Create Vector Index for Semantic Search (⭐ ADDED)
-- ============================================================================

-- IVFFlat index for approximate nearest neighbor search
-- Note: This works best with at least 1000 rows
-- For small datasets during development, Postgres will use sequential scan anyway

CREATE INDEX IF NOT EXISTS idx_chunks_embedding_cosine 
ON chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- If you have Supabase with HNSW support (better performance):
-- CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
-- ON chunks 
-- USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
-- 5. Create Triggers for Auto-updating timestamps
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for meetings table
DROP TRIGGER IF EXISTS update_meetings_updated_at ON meetings;
CREATE TRIGGER update_meetings_updated_at
    BEFORE UPDATE ON meetings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for summaries table
DROP TRIGGER IF EXISTS update_summaries_updated_at ON summaries;
CREATE TRIGGER update_summaries_updated_at
    BEFORE UPDATE ON summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for asr_jobs table
DROP TRIGGER IF EXISTS update_asr_jobs_updated_at ON asr_jobs;
CREATE TRIGGER update_asr_jobs_updated_at
    BEFORE UPDATE ON asr_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. Create Functions for Semantic Search (⭐ UPDATED)
-- ============================================================================

-- Function to search chunks by similarity (for a specific meeting)
CREATE OR REPLACE FUNCTION match_chunks(
  query_embedding vector(3072),
  p_meeting_id uuid,
  match_count int DEFAULT 5,
  similarity_threshold double precision DEFAULT 0.5
)
RETURNS TABLE (
  id bigint,
  meeting_id uuid,
  speaker text,
  start_seconds double precision,
  end_seconds double precision,
  topic text,
  text text,
  source text,  -- ⭐ ADDED
  similarity double precision
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    chunks.id,
    chunks.meeting_id,
    chunks.speaker,
    chunks.start_seconds,
    chunks.end_seconds,
    chunks.topic,
    chunks.text,
    chunks.source,  -- ⭐ ADDED
    1 - (chunks.embedding <=> query_embedding) AS similarity  -- Cosine similarity
  FROM chunks
  WHERE chunks.meeting_id = p_meeting_id
    AND chunks.embedding IS NOT NULL
    AND (1 - (chunks.embedding <=> query_embedding)) > similarity_threshold  -- Filter by threshold
  ORDER BY chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================================
-- 7. Create Helper Views (Optional but useful)
-- ============================================================================

-- View to see meeting overview with counts
CREATE OR REPLACE VIEW meeting_overview AS
SELECT 
    m.id,
    m.title,
    m.status,
    m.created_at,
    COUNT(DISTINCT u.id) as utterance_count,
    COUNT(DISTINCT c.id) as chunk_count,
    EXISTS(SELECT 1 FROM summaries s WHERE s.meeting_id = m.id) as has_summary
FROM meetings m
LEFT JOIN utterances u ON u.meeting_id = m.id
LEFT JOIN chunks c ON c.meeting_id = m.id
GROUP BY m.id, m.title, m.status, m.created_at
ORDER BY m.created_at DESC;

-- ============================================================================
-- Setup Complete!
-- ============================================================================

SELECT 'Setup completed successfully! ✅' as status;

-- Show all tables
SELECT 'Tables created:' as info;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Show all indexes
SELECT 'Indexes created:' as info;
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;