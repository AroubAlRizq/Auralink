import { ENDPOINTS } from "../config";

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  try { return await res.json(); } catch { return {}; }
}

// == Upload & Ingest ==
// DB person: backend /api/ingest must return: { meeting_id: "uuid" }
export async function ingestFile(file, title = "") {
  const fd = new FormData();
  fd.append("file", file);
  if (title) fd.append("title", title);
  return request(ENDPOINTS.ingest, { method: "POST", body: fd });
}

// == Build vector index ==
// RAG person: backend /api/index to build embeddings + pgvector
export async function buildIndex(meetingId) {
  return request(ENDPOINTS.index, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ meeting_id: meetingId }),
  });
}

// == Summary ==
// DB person: backend /api/summarize should return JSON like:
// { overview, key_points[], decisions[], action_items[] }
export async function getSummary(meetingId) {
  return request(`${ENDPOINTS.summarize}?meeting_id=${encodeURIComponent(meetingId)}`);
}

// == Chat (RAG) ==
// RAG person: backend /api/chat should return:
// { answer: string, citations?: [{start,end,text}] }
export async function chat(meetingId, query) {
  return request(ENDPOINTS.chat, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ meeting_id: meetingId, query }),
  });
}