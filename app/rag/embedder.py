import os
import httpx
from typing import List

PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "openai")
MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-large")
API_KEY = os.getenv("EMBEDDINGS_API_KEY")

async def embed_texts(texts: List[str]) -> List[List[float]]:
    if PROVIDER == "openai":
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {API_KEY}"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json={"input": texts, "model": MODEL})
            resp.raise_for_status()
            data = resp.json()["data"]
            # Order is preserved
            return [d["embedding"] for d in data]
    # add elif blocks for voyage, jina, cohere as needed
    raise NotImplementedError(f"Provider {PROVIDER} not implemented")

