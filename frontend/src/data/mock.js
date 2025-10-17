export const mockSummary = {
  overview:
    "Weekly product sync covering ASR quality, RAG retrieval precision, and dashboard UX. Agreed to ship MVP with transcript search and action items.",
  key_points: [
    "ASR WER improved from 13.2% → 10.7% using better diarization",
    "RAG: reranker lifted top-1 precision by +9%",
    "Timeline view accepted for MVP; analytics v1 shows speaking share",
  ],
  decisions: [
    "Adopt pgvector with 1536-dim embeddings",
    "Present polished React demo to supervisor",
    "Use AssemblyAI for ASR in MVP; explore Whisper Large v3 next",
  ],
  action_items: [
    { owner: "Sara", task: "Finalize FastAPI endpoints", due: "Oct 20", timestamp: 0 },
    { owner: "Omar", task: "Implement reranker + eval", due: "Oct 22", timestamp: 0 },
    { owner: "Hashem", task: "Polish React UI & charts", due: "Oct 23", timestamp: 0 },
  ],
};

export const mockUtterances = [
  { speaker: "Speaker A", start_seconds: 0, end_seconds: 25, text: "Welcome and agenda." },
  { speaker: "Speaker B", start_seconds: 25, end_seconds: 60, text: "ASR update and metrics." },
  { speaker: "Speaker A", start_seconds: 60, end_seconds: 120, text: "RAG experiments summary." },
  { speaker: "Speaker C", start_seconds: 120, end_seconds: 160, text: "Dashboard UX and filters." },
  { speaker: "Speaker B", start_seconds: 160, end_seconds: 210, text: "Next steps and owners." },
];

export const mockChat = [
  { role: "user", text: "What were the key decisions?" },
  { role: "ai", text: "1) Use pgvector; 2) Present React demo; 3) AssemblyAI for MVP.", citations: [
    { start: 60, end: 120, text: "We decided to adopt pgvector…" },
    { start: 120, end: 160, text: "We will present the React demo…" },
  ]},
];

export const roles = [
  { name: "Project Lead (Hashem)", duties: [
    "Define scope, milestones, and success metrics",
    "Coordinate team & reviews; final demo owner",
    "Own UI polish and cross-page experience",
  ]},
  { name: "Backend & APIs (Sara)", duties: [
    "FastAPI endpoints: /ingest, /index, /summarize, /chat",
    "DB models & migrations; storage and presigned URLs",
    "Auth placeholder (future)",
  ]},
  { name: "RAG & Retrieval (Omar)", duties: [
    "Chunking, embeddings, pgvector schema",
    "Retriever + reranker; evaluation & metrics",
    "Citations & provenance",
  ]},
  { name: "ASR & Diarization (Yousef)", duties: [
    "AssemblyAI / Whisper pipeline, timestamps & speakers",
    "Quality tracking (WER) and language support",
    "Error handling & retries",
  ]},
  { name: "Summarization & JSON (Lama)", duties: [
    "Structured meeting summary (overview, decisions, actions)",
    "Strict JSON validation; LoRA (optional)",
    "Timeline alignment of action item timestamps",
  ]},
];

export const roadmap = [
  { date: "Week 1", items: ["Repo setup & schema", "Basic ASR ingest", "Mock UI pages"] },
  { date: "Week 2", items: ["Indexing + pgvector", "RAG queries + citations", "React timeline"] },
  { date: "Week 3", items: ["Summarizer JSON v1", "Analytics & filters", "Design polish"] },
  { date: "Week 4", items: ["MVP demo", "Bug fixes", "Docs & handoff"] },
];

export const architectureBullets = [
  "Upload/video → audio (ffmpeg) → ASR + diarization",
  "Utterances chunking → embeddings → pgvector",
  "Retriever (kNN) → reranker → grounded context",
  "LLM summary → strict JSON (overview, key points, decisions, actions)",
  "Dashboard: timeline, analytics, RAG chat with citations",
];
