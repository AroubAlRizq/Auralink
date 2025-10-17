import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || "http://localhost:8000/api",
  timeout: 600000,
});

export const ingest = (file, title) => {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  return api.post("/ingest", form).then(r => r.data);
};

export const buildIndex    = (meeting_id) => api.post("/index", { meeting_id }).then(r => r.data);
export const summarize     = (meeting_id) => api.post("/summarize", { meeting_id }).then(r => r.data);
export const getSummary    = (meeting_id) => api.get("/summary", { params: { meeting_id } }).then(r => r.data);
export const getUtterances = (meeting_id) => api.get("/utterances", { params: { meeting_id } }).then(r => r.data?.items || []);

export const askChat = ({ meeting_id, query, k=12, speaker, time_end, rerank=true }) =>
  api.post("/chat", {
    meeting_id, query, k,
    filters: { speaker: speaker || null, time_start: null, time_end: time_end ? Number(time_end) : null },
    rerank
  }).then(r => r.data);

export default api;
