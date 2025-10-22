import { useEffect, useRef, useState } from "react";
import { chat } from "../lib/api";

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: "ai", text: "Ask about decisions, action items, or topics from your meeting." }
  ]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [meetingId, setMeetingId] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    setMeetingId(localStorage.getItem("meetingId") || "");
  }, []);
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!q.trim() || busy) return;
    const userText = q; setQ("");
    setMessages(m => [...m, { role: "user", text: userText }]);

    if (!meetingId) {
      setMessages(m => [...m, { role: "ai", text: "No meeting yet — upload on the Dashboard first." }]);
      return;
    }
    try {
      setBusy(true);
      const { answer, citations } = await chat(meetingId, userText);
      setMessages(m => [...m, { role: "ai", text: answer || "(no answer)", citations }]);
    } catch (e) {
      setMessages(m => [...m, { role: "ai", text: `Error: ${e.message}` }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="max-w-6xl mx-auto py-10 px-6">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6 flex flex-col">
        <h2 className="text-2xl font-semibold text-[#4C2E91] mb-2">Auralink Chat</h2>
        <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-[360px] max-h-[60vh] border border-gray-200 rounded-md p-4 bg-white">
          {messages.map((m, i) => (
            <div key={i}
              className={`rounded-2xl px-4 py-2 max-w-[75%] ${m.role === "user" ? "ml-auto bg-[#4C2E91] text-white" : "mr-auto bg-gray-100 text-gray-900"}`}>
              <div className="whitespace-pre-wrap text-sm">{m.text}</div>
              {m.citations?.length > 0 && (
                <div className="text-xs text-gray-500 mt-2 space-y-1">
                  {m.citations.map((c, j) => (<div key={j}>• {c.start ?? "?"}–{c.end ?? "?"}s — {c.text || "citation"}</div>))}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="flex gap-2 items-center">
          <input className="w-full border border-gray-300 rounded-md px-3 py-2"
                 placeholder="Ask about this meeting…" value={q}
                 onChange={(e)=>setQ(e.target.value)} onKeyDown={(e)=>e.key==="Enter" && send()} />
          <button className="inline-flex items-center justify-center rounded-md bg-[#4C2E91] px-4 py-2 text-white hover:opacity-90 transition disabled:opacity-60"
                  disabled={busy} onClick={send}>
            {busy ? "Sending…" : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}