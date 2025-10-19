# app/utils/db.py
import os
import asyncpg
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv("DATABASE_URL")

class DB:
    """Database connection manager using asyncpg"""
    
    def __init__(self):
        self.pool = None
    
    async def get_pool(self):
        """Get or create connection pool"""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=DATABASE_URL,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
        return self.pool
    
    @asynccontextmanager
    async def acquire(self):
        """Context manager for acquiring a connection"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            yield conn
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

# Global instance
db = DB()

# Helper functions matching your current interface
async def create_meeting(title: str, consent: bool) -> str:
    """Create a new meeting and return its ID"""
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO meetings (title, consent) VALUES ($1, $2) RETURNING id",
            title, consent
        )
        return str(row['id'])

async def update_meeting_status(meeting_id: str, status: str):
    """Update meeting status"""
    async with db.acquire() as conn:
        await conn.execute(
            "UPDATE meetings SET status = $1 WHERE id = $2",
            status, meeting_id
        )

async def bulk_insert_utterances(meeting_id: str, utterances: list):
    """Bulk insert utterances for a meeting"""
    async with db.acquire() as conn:
        await conn.executemany(
            """INSERT INTO utterances 
               (meeting_id, speaker, start_seconds, end_seconds, text)
               VALUES ($1, $2, $3, $4, $5)""",
            [(meeting_id, u['speaker'], u['start_seconds'], 
              u['end_seconds'], u['text']) for u in utterances]
        )