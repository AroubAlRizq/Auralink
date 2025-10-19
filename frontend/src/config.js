// Set API base here or via .env (VITE_API_BASE)
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const ENDPOINTS = {
  ingest: `${API_BASE}/api/ingest`,     // POST form-data: file, title?
  index: `${API_BASE}/api/index`,       // POST JSON: { meeting_id }
  summarize: `${API_BASE}/api/summarize`, // GET ?meeting_id=...
  chat: `${API_BASE}/api/chat`,         // POST JSON: { meeting_id, query }
};