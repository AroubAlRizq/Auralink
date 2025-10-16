# app/app_config.py
# FOR EMBEDDINGS AND RESPONSES
"""
Provider config used by the RAG pipeline:
- Embeddings: OpenAI (default; reads OPENAI_* envs, or falls back to EMBEDDINGS_*)
- LLM answerer: OpenAI Chat (reads OPENAI_* envs, or falls back to LLM_*)

Option B: you can keep your generic .env names and add:
  OPENAI_API_KEY=${EMBEDDINGS_API_KEY}
  OPENAI_EMBED_MODEL=${EMBEDDINGS_MODEL}

Required envs (with Option B mapping):
  # Vectors / DB
  PGVECTOR_DIM=3072                 # must match embedding size

  # Embeddings (OpenAI)
  OPENAI_API_KEY=...                # or EMBEDDINGS_API_KEY
  OPENAI_EMBED_MODEL=text-embedding-3-large  # or EMBEDDINGS_MODEL

  # Answer LLM (OpenAI)
  OPENAI_MODEL=gpt-4o-mini          # or LLM_MODEL
"""

import os
from typing import List

# -------------------- Helpers to read envs with Option-B fallbacks -------------------- #

def _get_env(*names: str, default: str | None = None) -> str | None:
    """Return the first set environment variable among names, else default."""
    for n in names:
        v = os.getenv(n)
        if v not in (None, ""):
            return v
    return default

def _embedding_cfg():
    # Prefer OPENAI_*; fallback to generic EMBEDDINGS_*
    api_key = _get_env("OPENAI_API_KEY", "EMBEDDINGS_API_KEY")
    model   = _get_env("OPENAI_EMBED_MODEL", "EMBEDDINGS_MODEL", default="text-embedding-3-large")
    return api_key, model

def _llm_cfg():
    api_key = _get_env("OPENAI_API_KEY", "LLM_API_KEY")
    model   = _get_env("OPENAI_MODEL", "LLM_MODEL", default="gpt-4o-mini")
    return api_key, model

def _pgvector_dim() -> int:
    # PGVECTOR_DIM should match the actual embedding size
    dim = _get_env("PGVECTOR_DIM", default=None)
    if dim:
        return int(dim)
    # If not set, infer from model name (best effort)
    _, model = _embedding_cfg()
    if "text-embedding-3-large" in model:
        return 3072
    if "text-embedding-3-small" in model or "text-embedding-ada-002" in model:
        return 1536
    # Sensible default; change if you use a different provider
    return 3072

# -------------------- Embeddings (OpenAI) -------------------- #

class BaseEmbedder:
    dim: int
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise RuntimeError("OpenAI embeddings key missing. Set OPENAI_API_KEY (or EMBEDDINGS_API_KEY).")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        # Infer known dims; adjust if you switch models
        if "text-embedding-3-large" in model:
            self.dim = 3072
        elif "text-embedding-3-small" in model or "text-embedding-ada-002" in model:
            self.dim = 1536
        else:
            # fallback to PGVECTOR_DIM if provided, otherwise 3072
            self.dim = _pgvector_dim()

    def embed(self, texts: List[str]) -> List[List[float]]:
        # For large batches, you may want to split into chunks
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]

# Single embedder instance used by indexer/retriever
_openai_key, _openai_embed_model = _embedding_cfg()
embed_model: BaseEmbedder = OpenAIEmbedder(_openai_key, _openai_embed_model)

# -------------------- Grounded answer LLM (OpenAI) -------------------- #

def llm_answer(question: str, context: str) -> str:
    """
    Compose a concise answer strictly from `context`.
    The caller builds `context` with numbered snippets (e.g., [1], [2]) + timestamps.
    """
    api_key, chat_model = _llm_cfg()
    if not api_key:
        raise RuntimeError("OpenAI chat key missing. Set OPENAI_API_KEY (or LLM_API_KEY).")

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    system = (
        "You are a helpful meeting assistant. Answer using ONLY the provided snippets. "
        "Cite snippet numbers like [1], [2]. If the answer is not in the snippets, say you don't know."
    )
    user = f"Snippets:\n{context}\n\nQuestion: {question}"

    resp = client.chat.completions.create(
        model=chat_model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        temperature=0,
    )
    return resp.choices[0].message.content

# -------------------- Public helpers -------------------- #

def embedding_dim() -> int:
    """Expose the effective embedding dimension (for schema checks)."""
    return getattr(embed_model, "dim", _pgvector_dim())
