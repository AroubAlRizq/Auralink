import { useEffect, useRef, useState } from "react";

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: "ai", text: "Ask about decisions, action items, or topics from your meeting." }
  ]);
  const [q, setQ] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = () => {
    if (!q.trim()) return;
    setMessages(m => [...m, { role: "user", text: q }]);
    // placeholder reply — replace with /api/chat call later
    setTimeout(() => {
      setMessages(m => [...m, { role: "ai", text: "This is a placeholder answer (connect /api/chat)." }]);
    }, 300);
    setQ("");
  };

  return (
    <div className="max-w-6xl mx-auto py-10 px-6">
      <div className="card flex flex-col">
        <h2 className="text-2xl font-semibold text-[#4C2E91] mb-2">Auralink Chat</h2>

        {/* Chat area sized similar to Timeline content */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-3 mb-4 min-h-[360px] max-h-[60vh] border border-gray-200 rounded-md p-4 bg-white"
        >
          {messages.map((m, i) => (
            <div
              key={i}
              className={`rounded-2xl px-4 py-2 max-w-[75%] ${
                m.role === "user" ? "ml-auto" : "mr-auto"
              } ${m.role === "user" ? "bg-[#4C2E91] text-white" : "bg-gray-100 text-gray-900"}`}
            >
              <div className="whitespace-pre-wrap text-sm">{m.text}</div>
            </div>
          ))}
        </div>

        {/* Composer */}
        <div className="flex gap-2 items-center">
          <input
            className="input focus-ring-teal flex-1"
            placeholder="Ask about this meeting…"
            value={q}
            onChange={(e)=>setQ(e.target.value)}
            onKeyDown={(e)=>e.key==="Enter" && send()}
          />
          <button className="btn btn--primary" onClick={send}>Send</button>
        </div>
      </div>
    </div>
  );
}