// src/lib/api.js
const RAW_BASE = (import.meta?.env?.VITE_API_BASE || "http://127.0.0.1:8000").trim();
export const API_BASE = RAW_BASE.replace(/\/+$/, "");

async function j(path, opts = {}) {
  const url = `${API_BASE}${path}`;

  let body = opts.body;
  const isPlainObject = body && typeof body === "object" && !(body instanceof FormData) && !(body instanceof Blob);
  if (isPlainObject) body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(url, {
      ...opts,
      body,
      headers: {
        ...(opts.headers || {}),
        ...(body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      },
    });
  } catch (e) {
    throw new Error(`Cannot reach API at ${API_BASE}. ${e?.message || e}`);
  }

  const text = await res.text().catch(() => "");
  if (!res.ok) {
    try {
      const j = text ? JSON.parse(text) : null;
      const detail = j?.detail ? (typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail)) : text;
      throw new Error(detail || `${res.status} ${res.statusText}`);
    } catch {
      throw new Error(text || `${res.status} ${res.statusText}`);
    }
  }
  try { return text ? JSON.parse(text) : {}; } catch { return {}; }
}

export async function ingestByUrl(meetingId, videoUrl) {
  return j("/api/ingest", { method: "POST", body: { meeting_id: meetingId, video_url: videoUrl } });
}
export async function ingestFile(meetingId, file) {
  const fd = new FormData();
  fd.append("meeting_id", meetingId);
  fd.append("video_file", file);
  return j("/api/ingest_file", { method: "POST", body: fd });
}
export async function buildIndex(meetingId) {
  return j("/api/index", { method: "POST", body: { meeting_id: meetingId } });
}
export async function getSummary(meetingId) {
  return j(`/api/summarize?mode=text&meeting_id=${encodeURIComponent(meetingId)}`, { method: "POST" });
}
export async function chat(meetingId, question, top_k = 6) {
  return j("/api/chat", { method: "POST", body: { meeting_id: meetingId, question, top_k } });
}
export async function pollAAI(jobId) {
  if (!jobId) throw new Error("Job ID missing in pollAAI()");
  return j("/api/aai/poll", { method: "POST", body: { job_id: jobId } });
}
export async function listUtterances(meetingId) {
  return j(`/api/utterances?meeting_id=${encodeURIComponent(meetingId)}`);
}
export async function health() {
  return j("/api/health");
}

export async function getJobForMeeting(meetingId) {
  return j(`/api/asr/job_for_meeting?meeting_id=${encodeURIComponent(meetingId)}`);
}