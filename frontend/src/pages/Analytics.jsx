// src/pages/Analytics.jsx
import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  LabelList,
} from "recharts";

/* ------------------- Colors & helpers ------------------- */
const COLORS = ["#6D28D9", "#8B5CF6", "#5B21B6", "#A78BFA", "#7C3AED", "#C4B5FD", "#E0D6FA"];

const STOP = new Set([
  "the","a","an","and","or","of","to","in","on","for","at","as","is","are","was","were",
  "be","been","by","with","that","this","it","its","from","we","you","they","i","our",
  "their","but","so","not","if","then","than","about","over","into","out","up","down",
  "your","my","me","us","them","he","she","his","her","him","there","here","also","just",
  "what","when","how","why","which","who","whom"
]);

const cleanText = (t) => (t || "").replace(/\s+/g, " ").trim();
const words = (str) =>
  (str || "")
    .toLowerCase()
    .split(/[^a-z0-9]+/g)
    .filter((w) => w && !STOP.has(w) && w.length >= 3);

/* ------------------- UI helpers ------------------- */
function Card({ title, children, className = "" }) {
  return (
    <div
      className={`rounded-3xl border border-[#E0D6FA] bg-white shadow-sm hover:shadow-md transition p-5 ${className}`}
    >
      {title ? <div className="font-semibold text-[#4C2E91] mb-3">{title}</div> : null}
      {children}
    </div>
  );
}

const PieTip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0];
  return (
    <div className="rounded-xl border border-[#E0D6FA] bg-white px-3 py-2 text-sm shadow">
      <div className="font-semibold text-[#4C2E91]">{p?.name ?? "Section"}</div>
      <div className="text-gray-600">
        {Number(p?.value ?? 0)} items
        {typeof p?.percent === "number" ? ` • ${Math.round(p.percent * 100)}%` : ""}
      </div>
    </div>
  );
};

const BarTip = ({ active, payload }) => {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0];
  return (
    <div className="rounded-xl border border-[#E0D6FA] bg-white px-3 py-2 text-sm shadow">
      <div className="font-semibold text-[#4C2E91]">{p?.payload?.name ?? "Section"}</div>
      <div className="text-gray-600">{Number(p?.value ?? 0)} words avg.</div>
    </div>
  );
};

/* ------------------- Page ------------------- */
export default function Analytics() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    try {
      const cached = localStorage.getItem("summaryPreview");
      if (cached) setSummary(JSON.parse(cached));
    } catch {}
  }, []);

  const title =
    (typeof window !== "undefined" && localStorage.getItem("meetingTitle")) ||
    "Meeting Insights";

  const { countsData, avgLenData, chips, totals } = useMemo(() => {
    const s = summary || {};
    const kp = Array.isArray(s.key_points) ? s.key_points : [];
    const dec = Array.isArray(s.decisions) ? s.decisions : [];
    const ai = Array.isArray(s.action_items) ? s.action_items : [];

    const totalWords = cleanText(s.overview).split(/\s+/).filter(Boolean).length;
    const totalBullets = kp.length + dec.length + ai.length;
    const sectionsCovered = ["key_points", "decisions", "action_items"].filter(
      (k) => Array.isArray(s?.[k]) && s[k].length > 0
    ).length;

    const countsData = [
      { name: "Key Points", value: kp.length, color: COLORS[1] },
      { name: "Decisions", value: dec.length, color: COLORS[2] },
      { name: "Action Items", value: ai.length, color: COLORS[3] },
    ];

    const avg = (arr) =>
      Array.isArray(arr) && arr.length
        ? Math.round(arr.join(" ").split(/\s+/).length / arr.length)
        : 0;

    const avgLenData = [
      { name: "Key Points", value: avg(kp), color: COLORS[1] },
      { name: "Decisions", value: avg(dec), color: COLORS[2] },
      { name: "Action Items", value: avg(ai), color: COLORS[3] },
    ];

    const allText = [
      cleanText(s.overview),
      cleanText(kp.join(" ")),
      cleanText(dec.join(" ")),
      cleanText(ai.map((x) => x?.task || x).join(" ")),
    ].join(" ");
    const freq = new Map();
    for (const w of words(allText)) freq.set(w, (freq.get(w) || 0) + 1);
    const chips = Array.from(freq.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([term, count]) => ({ term, count }));

    return {
      countsData,
      avgLenData,
      chips,
      totals: { totalWords, totalBullets, sectionsCovered },
    };
  }, [summary]);

  const safeCounts = Array.isArray(countsData) ? countsData : [];
  const safeBars = Array.isArray(avgLenData) ? avgLenData : [];
  const donutTotal = safeCounts.reduce((a, b) => a + (Number(b.value) || 0), 0) || 1;

  const barValues = safeBars.map((d) => Number(d.value || 0));
  const barMax = barValues.length ? Math.max(...barValues) : 0;
  const barAvg =
    barValues.length && barValues.some((v) => v > 0)
      ? Math.round(barValues.reduce((a, b) => a + b, 0) / barValues.length)
      : null;

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <h1 className="page-header-title">{title}</h1>
        <p className="page-header-subtitle">
          Visual analytics derived from the meeting summary.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <Card>
          <div className="text-gray-500 text-sm">Overview</div>
          <div className="text-2xl font-semibold text-[#4C2E91]">
            {totals?.totalWords ?? 0} words
          </div>
        </Card>
        <Card>
          <div className="text-gray-500 text-sm">Bullet Items</div>
          <div className="text-2xl font-semibold text-[#4C2E91]">
            {totals?.totalBullets ?? 0}
          </div>
        </Card>
        <Card>
          <div className="text-gray-500 text-sm">Sections Covered</div>
          <div className="text-2xl font-semibold text-[#4C2E91]">
            {totals?.sectionsCovered ?? 0} / 3
          </div>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Section Distribution">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={safeCounts}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={2}
                >
                  {safeCounts.map((e, i) => (
                    <Cell key={i} fill={e.color} />
                  ))}
                  <LabelList
                    dataKey="value"
                    position="inside"
                    style={{
                      fill: "#fff",
                      fontWeight: 700,
                      fontSize: 12,
                    }}
                  />
                </Pie>
                <Tooltip content={<PieTip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Average Bullet Length (words)">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={safeBars}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} />
                <Tooltip content={<BarTip />} />
                {typeof barAvg === "number" && !Number.isNaN(barAvg) ? (
                  <ReferenceLine y={barAvg} stroke="#C4B5FD" strokeDasharray="4 4" />
                ) : null}
                <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                  {safeBars.map((e, i) => (
                    <Cell key={i} fill={e.color} />
                  ))}
                  <LabelList
                    dataKey="value"
                    position="top"
                    style={{ fill: "#4C2E91", fontWeight: 600, fontSize: 12 }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {typeof barAvg === "number" && !Number.isNaN(barAvg) ? (
            <div className="mt-2 text-xs text-gray-500">
              Avg reference line:{" "}
              <span className="font-semibold text-[#4C2E91]">{barAvg}</span> words · Max:{" "}
              <span className="font-semibold text-[#4C2E91]">{barMax}</span>
            </div>
          ) : null}
        </Card>
      </div>

      {/* Keywords */}
      <Card title="Top Keywords" className="mt-6">
        {!chips?.length ? (
          <div className="text-gray-500 text-sm">No keywords detected.</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {chips.map(({ term, count }, i) => (
              <span
                key={i}
                className="px-3 py-1 rounded-full border border-[#E0D6FA] bg-[#F9F8FF] text-[#4C2E91] text-sm shadow-sm"
                title={`${count} mentions`}
              >
                {term} <span className="text-gray-400">· {count}</span>
              </span>
            ))}
          </div>
        )}
      </Card>

      {/* Footer */}
      <div className="text-center text-xs text-gray-400 pt-4">
        <hr className="mb-4 border-gray-200" />
        <p>
          © 2025 <span className="font-semibold text-[#5B21B6]">Auralink</span>. All rights reserved.
        </p>
      </div>
    </div>
  );
}