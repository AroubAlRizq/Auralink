-- Complete Supabase Setup SQL
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
    
    -- Status should be one of: uploaded, asr_started, asr_done, indexed, summarized, error
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
    
    -- Kind should be one of: upload, narration, summary, other
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
    start_seconds DOUBLE PRECISION NOT NULL,
    end_seconds DOUBLE PRECISION NOT NULL,
    topic TEXT,
    text TEXT NOT NULL,
    embedding vector(3072),  -- 3072 for text-embedding-3-large
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
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
    
    -- Status should be one of: queued, processing, completed, error
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

-- ASR Jobs indexes
CREATE INDEX IF NOT EXISTS idx_asr_jobs_meeting_id ON asr_jobs(meeting_id);
CREATE INDEX IF NOT EXISTS idx_asr_jobs_status ON asr_jobs(status);
CREATE INDEX IF NOT EXISTS idx_asr_jobs_provider ON asr_jobs(provider);

-- ============================================================================
-- 4. Create Triggers for Auto-updating timestamps
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
-- 5. Create Functions for Semantic Search
-- ============================================================================

-- Function to search chunks by similarity (for a specific meeting)
CREATE OR REPLACE FUNCTION match_chunks(
  query_embedding vector(3072),
  p_meeting_id uuid,
  match_count int DEFAULT 5
)
RETURNS TABLE (
  id bigint,
  meeting_id uuid,
  speaker text,
  start_seconds double precision,
  end_seconds double precision,
  topic text,
  text text,
  embedding vector(3072),
  created_at timestamp with time zone,
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
    chunks.embedding,
    chunks.created_at,
    1 - (chunks.embedding <=> query_embedding) AS similarity
  FROM chunks
  WHERE chunks.meeting_id = p_meeting_id
    AND chunks.embedding IS NOT NULL
  ORDER BY chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================================
-- Setup Complete!
-- ============================================================================

-- Show all tables
SELECT 'Setup completed successfully!' as status;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

