// src/pages/Chat.jsx
import { useState, useRef, useEffect } from "react";
import { chat as chatApi } from "../lib/api";
import { useMeeting } from "../context/MeetingContext";

export default function Chat() {
  const { meetingId, chatMessages, appendChat } = useMeeting();
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const chatRef = useRef(null);

  const send = async () => {
    if (!meetingId) {
      setErr("No meeting selected.");
      return;
    }
    if (!input.trim() || busy) return;

    setErr("");
    const content = input.trim();
    appendChat({ role: "user", content });
    setBusy(true);
    setInput("");

    try {
      const r = await chatApi(meetingId, content, 6);
      appendChat({
        role: "assistant",
        content: r?.answer || "(no answer)",
        sources: r?.sources || [],
      });
    } catch (e) {
      appendChat({
        role: "assistant",
        content: e?.message || "Request failed.",
      });
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [chatMessages]);

  return (
    <div className="page">
      {/* Header (shared) */}
      <div className="page-header">
        <h2 className="page-header-title">Chat</h2>
        <p className="page-header-subtitle">Ask about this meeting’s content.</p>
      </div>

      {/* Chat area */}
      <div
        ref={chatRef}
        className="rounded-3xl border border-[#E0D6FA] bg-white p-6 h-[64vh] overflow-y-auto shadow-sm hover:shadow-md transition"
      >
        {chatMessages.length === 0 ? (
          <div className="text-center text-gray-500 pt-32">
            Ask anything about this meeting.
          </div>
        ) : (
          chatMessages.map((m, i) => (
            <div
              key={i}
              className={`mb-5 ${m.role === "user" ? "text-right" : "text-left"}`}
            >
              <div
                className={`inline-block max-w-[85%] px-4 py-3 rounded-2xl shadow-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-[#5B21B6] text-white rounded-br-none"
                    : "bg-white border border-gray-100 text-gray-800 rounded-bl-none"
                }`}
              >
                {m.content}
              </div>

              {m.sources?.length > 0 && (
                <details className="mt-2 text-left">
                  <summary className="text-xs text-gray-500 cursor-pointer">Sources</summary>
                  <ul className="pl-5 list-disc text-xs text-gray-600">
                    {m.sources.map((s, idx) => (
                      <li key={idx}>
                        [{s.t}] {s.speaker}: {s.text.slice(0, 160)}
                        {s.text.length > 160 ? "…" : ""}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ))
        )}
      </div>

      {/* Input box — purple focus border */}
      <div className="flex items-center gap-3 rounded-3xl border border-[#E0D6FA] bg-white shadow-sm p-2 focus-within:border-[#6D28D9] transition">
        <textarea
          className="flex-1 resize-none border-none focus:ring-0 text-sm text-gray-800 placeholder-gray-400 rounded-2xl px-3 py-2 focus:outline-none"
          rows={1}
          placeholder="Type a question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button
          onClick={send}
          disabled={busy || !input.trim()}
          className={`px-5 py-2.5 text-sm font-semibold rounded-2xl text-white shadow-md transition ${
            busy || !input.trim()
              ? "bg-gray-300 cursor-not-allowed"
              : "bg-[#6D28D9] hover:bg-[#5B21B6]"
          }`}
        >
          {busy ? "Thinking…" : "Send"}
        </button>
      </div>

      {err && <div className="text-sm text-red-600 text-center">{err}</div>}

      <div className="text-center text-xs text-gray-400 pt-4">
        <hr className="mb-4 border-gray-200" />
        <p>
          © 2025 <span className="font-semibold text-[#5B21B6]">Auralink</span>. All rights reserved.
        </p>
      </div>
    </div>
  );
}