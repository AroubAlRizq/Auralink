# app/rag/indexer_service.py
from typing import List, Dict
from app.rag.chunking import chunk_utterances, chunk_summary
from app.rag.embedder import embed_texts
from app.utils.database import DatabaseManager

async def index_transcript(meeting_id: str, utterances: List[Dict]) -> int:
    """Chunk utterances -> embed -> insert into chunks with source='transcript'."""
    if not utterances:
        print("⚠️  No utterances to index")
        return 0
    
    print(f"📝 Chunking {len(utterances)} utterances...")
    chunks = chunk_utterances(utterances, max_chars=900)
    if not chunks:
        print("⚠️  No chunks created")
        return 0
    
    print(f"✂️  Created {len(chunks)} chunks")
    
    # Get embeddings for all chunks
    print(f"🔢 Generating embeddings for {len(chunks)} chunks...")
    embeds = await embed_texts([c["text"] for c in chunks])
    print(f"✅ Generated {len(embeds)} embeddings")
    
    # Insert chunks into database
    db = DatabaseManager()
    
    print(f"💾 Inserting {len(chunks)} chunks into database...")
    inserted_count = 0
    
    try:
        for i, chunk in enumerate(chunks):
            # Convert embedding to PostgreSQL array format
            embed_str = "[" + ",".join(map(str, embeds[i])) + "]"
            
            query = """
                INSERT INTO chunks
                  (meeting_id, speaker, start_seconds, end_seconds, text, topic, source, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, 'transcript', %s::vector)
            """
            
            try:
                db.client.execute_query(
                    query,
                    (
                        meeting_id,
                        chunk["speaker"],
                        chunk["start_seconds"],
                        chunk["end_seconds"],
                        chunk["text"],
                        chunk.get("topic"),
                        embed_str
                    )
                )
                inserted_count += 1
                if (i + 1) % 10 == 0:
                    print(f"   Inserted {i + 1}/{len(chunks)} chunks...")
            except Exception as e:
                print(f"❌ Failed to insert chunk {i}: {e}")
                # Continue with next chunk instead of failing completely
                continue
        
        print(f"✅ Successfully inserted {inserted_count}/{len(chunks)} transcript chunks")
    except Exception as e:
        print(f"❌ Error during indexing transcript: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return inserted_count

async def index_summary(meeting_id: str, summary_json: Dict) -> int:
    """Chunk summary bullets -> embed -> insert into chunks with source='summary'."""
    if not summary_json:
        print("⚠️  No summary to index")
        return 0
    
    print(f"📋 Chunking summary...")
    chunks = chunk_summary(summary_json)
    if not chunks:
        print("⚠️  No summary chunks created")
        return 0
    
    print(f"✂️  Created {len(chunks)} summary chunks")
    
    # Get embeddings for all chunks
    print(f"🔢 Generating embeddings for {len(chunks)} summary chunks...")
    embeds = await embed_texts([c["text"] for c in chunks])
    print(f"✅ Generated {len(embeds)} embeddings")
    
    # Insert chunks into database
    db = DatabaseManager()
    
    print(f"💾 Inserting {len(chunks)} summary chunks into database...")
    inserted_count = 0
    
    try:
        for i, chunk in enumerate(chunks):
            # Convert embedding to PostgreSQL array format
            embed_str = "[" + ",".join(map(str, embeds[i])) + "]"
            
            query = """
                INSERT INTO chunks
                  (meeting_id, speaker, start_seconds, end_seconds, text, topic, source, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, 'summary', %s::vector)
            """
            
            try:
                db.client.execute_query(
                    query,
                    (
                        meeting_id,
                        chunk["speaker"],
                        chunk["start_seconds"],
                        chunk["end_seconds"],
                        chunk["text"],
                        chunk.get("topic"),
                        embed_str
                    )
                )
                inserted_count += 1
            except Exception as e:
                print(f"❌ Failed to insert summary chunk {i}: {e}")
                continue
        
        print(f"✅ Successfully inserted {inserted_count}/{len(chunks)} summary chunks")
    except Exception as e:
        print(f"❌ Error during indexing summary: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    return inserted_count