// src/pages/Timeline.jsx
import { useEffect, useState } from "react";
import { getSummary, listUtterances } from "../lib/api";

export default function Timeline() {
  const [summary, setSummary] = useState(null);
  const [utterances, setUtterances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [raw, setRaw] = useState(null); // debug

  useEffect(() => {
    const meetingId = localStorage.getItem("meetingId");
    const cached = localStorage.getItem("summaryPreview");
    if (cached) { try { setSummary(JSON.parse(cached)); } catch {} }

    if (!meetingId) {
      setErr("No meeting selected. Upload a meeting on the Dashboard.");
      setLoading(false);
      return;
    }

    (async () => {
      try {
        const s = await getSummary(meetingId);
        setRaw(s);
        let normalized = s || {};
        if (!("overview" in normalized || "key_points" in normalized || "decisions" in normalized || "action_items" in normalized)) {
          const exec = Array.isArray(s?.executive_summary) ? s.executive_summary.join(" ") : (s?.executive_summary || s?.overview || s?.raw_summary_text || "");
          const kp = Array.isArray(s?.key_points) ? s.key_points : (Array.isArray(s?.key_events) ? s.key_events : []);
          normalized = {
            overview: exec,
            key_points: kp,
            decisions: Array.isArray(s?.decisions) ? s.decisions : [],
            action_items: Array.isArray(s?.action_items) ? s.action_items : [],
          };
        }

        // NEW: if still empty, drop the cache so we don't keep blank state
        const isEmpty =
          !normalized.overview &&
          (!normalized.key_points?.length) &&
          (!normalized.decisions?.length) &&
          (!normalized.action_items?.length);

        if (isEmpty) {
          localStorage.removeItem("summaryPreview");
        } else {
          setSummary(normalized);
          localStorage.setItem("summaryPreview", JSON.stringify(normalized));
        }

        // also fetch utterances for context
        try {
          const u = await listUtterances(meetingId);
          setUtterances(Array.isArray(u?.utterances) ? u.utterances : []);
        } catch {}
      } catch (e) {
        // NEW: friendly message for the 409 we return server-side
        const msg = String(e?.message || "");
        if (msg.includes("No utterances found")) {
          setErr("No transcript yet for this meeting. Please upload/ingest and wait for transcription to finish, then try again.");
        } else {
          setErr(msg || "Failed to load summary");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="max-w-6xl mx-auto py-10 px-6">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
        <h2 className="text-2xl font-semibold text-[#4C2E91] mb-4">Conversation Timeline</h2>

        <div className="min-h-[360px] rounded-md border border-gray-200 bg-white p-4 text-gray-800 leading-relaxed space-y-4">
          {loading && <div className="text-gray-500">Loading…</div>}
          {err && <div className="text-red-600 text-sm">{err}</div>}

          {!loading && !err && summary && (
            <>
              {summary.overview && (
                <section>
                  <div className="font-semibold text-gray-700 mb-1">Overview</div>
                  <p>{summary.overview}</p>
                </section>
              )}

              {Array.isArray(summary.key_points) && summary.key_points.length > 0 && (
                <section>
                  <div className="font-semibold text-gray-700 mb-1">Key Points</div>
                  <ul className="list-disc ml-5">
                    {summary.key_points.map((p, i) => <li key={i}>{String(p)}</li>)}
                  </ul>
                </section>
              )}

              {Array.isArray(summary.decisions) && summary.decisions.length > 0 && (
                <section>
                  <div className="font-semibold text-gray-700 mb-1">Decisions</div>
                  <ul className="list-disc ml-5">
                    {summary.decisions.map((d, i) => <li key={i}>{String(d)}</li>)}
                  </ul>
                </section>
              )}

              {Array.isArray(summary.action_items) && summary.action_items.length > 0 && (
                <section>
                  <div className="font-semibold text-gray-700 mb-1">Action Items</div>
                  <ul className="list-disc ml-5">
                    {summary.action_items.map((a, i) => <li key={i}>{String(a?.task || a)}</li>)}
                  </ul>
                </section>
              )}

              <details className="mt-4">
                <summary className="cursor-pointer text-sm text-gray-500">Debug: raw summary JSON</summary>
                <pre className="text-xs bg-gray-50 p-2 rounded border overflow-auto max-h-64">
                  {JSON.stringify(raw ?? summary, null, 2)}
                </pre>
                {utterances?.length ? (
                  <div className="text-xs text-gray-600 mt-2">Utterances saved: {utterances.length}</div>
                ) : (
                  <div className="text-xs text-gray-600 mt-2">No utterances found (summary may be language-model inferred).</div>
                )}
              </details>
            </>
          )}

          {!loading && !err && !summary && (
            <div className="text-gray-500">No summary yet — upload a meeting on the Dashboard.</div>
          )}
        </div>
      </div>
    </div>
  );
}