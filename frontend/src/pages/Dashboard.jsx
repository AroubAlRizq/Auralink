// src/pages/Dashboard.jsx
import { useState, useRef } from "react";
import { ingestByUrl, ingestFile, pollAAI, getSummary } from "../lib/api";
import { useMeeting } from "../context/MeetingContext";

function uuid() {
  try { if (crypto?.randomUUID) return crypto.randomUUID(); } catch {}
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0,
      v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
const VIDEO_EXT = /\.(mp4|webm|mov|mkv|m4v|mp3|wav|m4a)$/i;

export default function Dashboard() {
  const { setMeetingId, setMeetingTitle, setSummary } = useMeeting();

  const [videoUrl, setVideoUrl] = useState("");
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState(localStorage.getItem("meetingTitle") || "");
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
    setStatus(`Processing…`);
    const deadline = Date.now() + 5 * 60 * 1000;
    while (Date.now() < deadline) {
      try {
        const r = await pollAAI(jobId);
        if (r?.status === "completed") {
          setStatus("Generating summary…");
          return true;
        }
        if (r?.status === "error") {
          throw new Error(r?.error || "Failed to process file");
        }
      } catch {
        /* ignore transient poll errors */
      }
      await new Promise((res) => setTimeout(res, 3000));
    }
    throw new Error("Timed out waiting for processing.");
  }

  const startPipeline = async () => {
    if (busy) return;

    localStorage.removeItem("aaiJobId");
    localStorage.removeItem("summaryPreview");

    const mid = uuid();
    try {
      setBusy(true);
      setError("");
      setStatus("Preparing…");

      setMeetingId(mid);
      if (title) {
        setMeetingTitle(title);
        localStorage.setItem("meetingTitle", title);
      }

      let resp = null;
      if (file) {
        setStatus("Uploading…");
        resp = await ingestFile(mid, file);
      } else if (videoUrl.trim()) {
        setStatus("Starting from URL…");
        resp = await ingestByUrl(mid, videoUrl.trim());
      } else {
        setError("Please select a file or paste a link.");
        setStatus("");
        return;
      }

      const jobId = resp?.job_id || localStorage.getItem("aaiJobId");
      if (resp?.job_id) localStorage.setItem("aaiJobId", resp.job_id);

      if (jobId) await waitForTranscript(jobId);

      try {
        const s = await getSummary(mid);
        if (s) {
          setSummary(s);
          localStorage.setItem("summaryPreview", JSON.stringify(s));
          setStatus("Done! You can open the Timeline.");
        } else {
          setStatus("Summary will be ready soon.");
        }
      } catch {
        setStatus("Summary not available yet.");
      }
    } catch (e) {
      setError(e?.message || "Something went wrong.");
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
        {/* Header */}
        <div className="page-header text-center">
          <h2 className="page-header-title">Upload or Link a Meeting</h2>
          <p className="page-header-subtitle">
            Choose a local video/audio file or paste a direct link.
          </p>
        </div>

        {/* Upload card — consistent purple border */}
        <div className="mt-6 rounded-3xl border border-[#E0D6FA] bg-white p-6 shadow-sm hover:shadow-md transition">
          {/* URL input */}
          <input
            className="w-full rounded-2xl border border-[#E0D6FA] bg-white px-4 py-3 shadow-inner
                       placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#6D28D9] mb-3"
            placeholder="Public video/audio URL (https://…/file.mp4)"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
          />

          {/* Dropzone */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className="rounded-2xl border-2 border-dashed border-[#E0D6FA] bg-white py-12 text-center mb-4
                       hover:border-[#6D28D9] hover:shadow-md transition cursor-pointer"
          >
            <div className="text-[#1F1147] font-semibold text-lg">
              {file ? file.name : "Drag & drop or click to choose a file"}
            </div>
            <div className="text-[#7C6BD6] text-sm mt-2 tracking-wide">
              MP4, WEBM, MOV, MKV, MP3, WAV, M4A…
            </div>
          </div>

          <input
            ref={inputRef}
            type="file"
            accept="video/*,audio/*,.mp4,.webm,.mov,.mkv,.mp3,.wav,.m4a"
            className="hidden"
            onChange={onBrowse}
          />

          {/* Title input */}
          <input
            className="w-full rounded-2xl border border-[#E0D6FA] bg-white px-4 py-3 shadow-inner
                       placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#6D28D9] mb-4"
            placeholder="Title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          {/* Button */}
          <button
            className="btn btn--primary w-full disabled:opacity-60"
            disabled={busy || (!file && !videoUrl.trim())}
            onClick={startPipeline}
          >
            {busy ? "Processing…" : "Start Processing"}
          </button>

          {/* Status / Error */}
          {status && !error && <div className="mt-3 text-sm text-gray-700 text-center">{status}</div>}
          {error && <div className="mt-3 text-sm text-red-600 text-center">{error}</div>}
        </div>
      </div>
    </div>
  );
}