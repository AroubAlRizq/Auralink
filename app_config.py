# app/app_config.py
# FOR EMBEDDINGS AND RESPONSES
"""
Provider config used by the RAG pipeline:
- Embeddings: OpenAI (default) or local Sentence-Transformers
- LLM answerer: OpenAI Chat (grounded QA)

Env vars (.env):
  EMBEDDINGS_PROVIDER=openai|local
  OPENAI_API_KEY=...
  OPENAI_EMBED_MODEL=text-embedding-3-large
  OPENAI_MODEL=gpt-4o-mini
  PGVECTOR_DIM=3072           # must match the embedding model dimensionality
"""

import os
from typing import List

# ---------- Embeddings ----------
class BaseEmbedder:
    dim: int
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

class OpenAIEmbedder(BaseEmbedder):
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large")
        # Known dims (update if you switch models)
        self.dim = 3072 if "3-large" in self.model else 1536

    def embed(self, texts: List[str]) -> List[List[float]]:
        # OpenAI handles batching internally for small lists; for large, chunk yourself.
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]

class LocalSTEmbedder(BaseEmbedder):
    def __init__(self):
        # Multilingual, good default. Change if you prefer another.
        from sentence_transformers import SentenceTransformer
        model_id = os.getenv("LOCAL_EMBED_MODEL", "intfloat/multilingual-e5-large")
        self.model = SentenceTransformer(model_id)
        # Common dims: e5-large=1024, e5-base=768, bge-m3=1024 (pooled)
        self.dim = int(os.getenv("PGVECTOR_DIM", "1024"))

    def embed(self, texts: List[str]) -> List[List[float]]:
        # Tip: E5 expects "query: ..." / "passage: ..." prefixes; optional for quick start.
        return self.model.encode(texts, normalize_embeddings=True).tolist()

def _make_embedder() -> BaseEmbedder:
    provider = os.getenv("EMBEDDINGS_PROVIDER", "openai").lower()
    if provider == "openai":
        return OpenAIEmbedder()
    elif provider in {"local", "sentence-transformers", "st"}:
        return LocalSTEmbedder()
    else:
        raise ValueError(f"Unsupported EMBEDDINGS_PROVIDER: {provider}")

embed_model: BaseEmbedder = _make_embedder()

# Runtime sanity check so pgvector dim matches what we store
def embedding_dim() -> int:
    return getattr(embed_model, "dim", int(os.getenv("PGVECTOR_DIM", "3072")))

# ---------- Grounded answer LLM ----------
def llm_answer(question: str, context: str) -> str:
    """
    Compose a concise answer strictly from `context`.
    The caller builds `context` with numbered snippets (e.g., [1], [2]) + timestamps.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system = (
        "You are a helpful meeting assistant. Answer using ONLY the provided snippets. "
        "Cite snippet numbers like [1], [2]. If the answer is not in the snippets, say you don't know."
    )
    user = f"Snippets:\n{context}\n\nQuestion: {question}"
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0,
    )
    return resp.choices[0].message.content
