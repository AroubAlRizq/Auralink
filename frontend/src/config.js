export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export const ENDPOINTS = {
  ingest: "/api/ingest",
  index: "/api/index",
  summarize: "/api/summarize",
  chat: "/api/chat",
};