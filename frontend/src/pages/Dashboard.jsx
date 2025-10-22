// src/pages/Dashboard.jsx
import { useState, useRef } from "react";
import { ingestByUrl, ingestFile, pollAAI, getSummary } from "../lib/api";

function uuid() {
  try { if (crypto?.randomUUID) return crypto.randomUUID(); } catch {}
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
    const r = (Math.random()*16)|0, v = c === "x" ? r : (r&0x3)|0x8; return v.toString(16);
  });
}
const VIDEO_EXT = /\.(mp4|webm|mov|mkv|m4v|mp3|wav|m4a)$/i;

export default function Dashboard() {
  const [videoUrl, setVideoUrl] = useState("");
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const onDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (!f) return;
    if (!(f.type?.startsWith("video/") || f.type?.startsWith("audio/") || VIDEO_EXT.test(f.name))) {
      setError("Please select a video/audio file.");
      return;
    }
    setError("");
    setFile(f);
  };
  const onBrowse = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!(f.type?.startsWith("video/") || f.type?.startsWith("audio/") || VIDEO_EXT.test(f.name))) {
      setError("Please select a video/audio file.");
      return;
    }
    setError("");
    setFile(f);
  };

  async function waitForTranscript(jobId) {
    setStatus(`Transcribing… [${jobId || "pending"}]`);
    const deadline = Date.now() + 5 * 60 * 1000; // 5 minutes
    while (Date.now() < deadline) {
      try {
        const r = await pollAAI(jobId);
        if (r?.status === "completed") {
          setStatus("Transcription done. Summarizing…");
          return true;
        }
        if (r?.status === "error") {
          throw new Error(r?.error || "Transcription failed");
        }
      } catch (e) {
        console.warn("poll error:", e);
      }
      await new Promise(res => setTimeout(res, 3000));
    }
    throw new Error("Timed out waiting for transcription.");
  }

  const startPipeline = async () => {
    if (busy) return;
    const meetingId = uuid();

    try {
      setBusy(true);
      setError("");
      setStatus("Preparing…");

      // store meeting context early (used by other pages)
      localStorage.setItem("meetingId", meetingId);
      if (title) localStorage.setItem("meetingTitle", title);

      let resp = null;

      if (file) {
        setStatus("Uploading & starting ASR…");
        resp = await ingestFile(meetingId, file); // { job_id, ... }
      } else if (videoUrl.trim()) {
        setStatus("Starting ASR from URL…");
        resp = await ingestByUrl(meetingId, videoUrl.trim()); // { job_id, ... }
      } else {
        setError("Pick a file or paste a public URL.");
        setStatus("");
        return;
      }

      const jobId = resp?.job_id || localStorage.getItem("aaiJobId");
      if (resp?.job_id) {
        localStorage.setItem("aaiJobId", resp.job_id);
      }

      if (jobId) {
        await waitForTranscript(jobId);
      } else {
        setStatus("Transcription started (no job id). You may need to try summary again shortly.");
      }

      // Try summarizing (text mode uses stored utterances)
      try {
        const s = await getSummary(meetingId);
        if (s) {
          localStorage.setItem("summaryPreview", JSON.stringify(s));
          setStatus("Done! Open the Timeline.");
        } else {
          setStatus("No summary yet. Try the Timeline in a moment.");
        }
      } catch (e) {
        console.error(e);
        setStatus("Transcript saved, but summarize is not ready yet.");
      }
    } catch (e) {
      console.error(e);
      setError(e?.message || "Request failed.");
      setStatus("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="w-full">
      {/* Hero */}
      <div className="w-full">
        <img
          src="/hero-auralink.webp"
          alt="Auralink hero"
          className="w-full h-[320px] md:h-[400px] object-cover"
        />
      </div>

      <div className="max-w-2xl mx-auto py-8 px-6">
        <div className="card">
          <h2 className="text-2xl font-semibold text-[#4C2E91] mb-2">Upload or Link a Meeting</h2>
          <p className="text-gray-600 mb-6">Choose a local video/audio file or paste a direct public URL.</p>

          {/* URL input */}
          <input
            className="input focus-ring-teal mb-3"
            placeholder="Public video/audio URL (https://…/file.mp4)"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
          />

          {/* Dropzone / File picker */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className="rounded-lg border-2 border-dashed border-gray-300 py-12 text-center mb-4 hover:border-gray-400 transition cursor-pointer"
          >
            <div className="text-gray-700 font-medium">
              {file ? file.name : "Drag & drop or click to choose a file"}
            </div>
            <div className="text-gray-400 text-sm mt-1">MP4, WEBM, MOV, MKV, MP3, WAV, M4A…</div>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="video/*,audio/*,.mp4,.webm,.mov,.mkv,.mp3,.wav,.m4a"
            className="hidden"
            onChange={onBrowse}
          />

          {/* Optional title */}
          <input
            className="input focus-ring-teal mb-4"
            placeholder="Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          <button
            className="btn btn--primary w-full disabled:opacity-60"
            disabled={busy || (!file && !videoUrl.trim())}
            onClick={startPipeline}
          >
            {busy ? "Processing…" : "Start Processing"}
          </button>

          {status && !error && <div className="mt-3 text-sm text-gray-700">{status}</div>}
          {error && <div className="mt-3 text-sm text-red-600">{error}</div>}
        </div>
      </div>
    </div>
  );
}