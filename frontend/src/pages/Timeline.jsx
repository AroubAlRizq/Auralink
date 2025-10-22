// src/pages/Timeline.jsx
import { useEffect, useState } from "react";
import { getSummary } from "../lib/api";

const icons = {
  lightning: (
    <svg viewBox="0 0 24 24" className="w-5 h-5">
      <path fill="currentColor" d="M13 3L4 14h6l-1 7 9-11h-6l1-7Z" />
    </svg>
  ),
  list: (
    <svg viewBox="0 0 24 24" className="w-5 h-5">
      <path fill="currentColor" d="M4 6h16v2H4V6Zm0 5h16v2H4v-2Zm0 5h16v2H4v-2Z" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 24 24" className="w-5 h-5">
      <path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4Z" />
    </svg>
  ),
  flag: (
    <svg viewBox="0 0 24 24" className="w-5 h-5">
      <path fill="currentColor" d="M6 3v18H4V3h2Zm14 2-6 2-6-2v11l6 2 6-2V5Z" />
    </svg>
  ),
};

function SectionCard({ title, icon, items, badgeCount }) {
  const isEmpty =
    !items ||
    (Array.isArray(items) && items.length === 0) ||
    (typeof items === "string" && !items.trim());
  if (isEmpty) return null;

  return (
    <div className="rounded-3xl border border-[#E0D6FA] bg-white shadow-sm hover:shadow-md transition">
      {/* Header section */}
      <div className="flex justify-between items-center px-5 py-4 border-b border-[#E5DCFB]">
        <div className="flex items-center gap-2 text-[#4C2E91] font-semibold">
          <div className="bg-[#F3F0FF] rounded-xl p-2 shadow-sm">{icon}</div>
          {title}
        </div>
        {badgeCount > 0 && (
          <span className="bg-[#F3F0FF] text-[#4C2E91] text-xs px-3 py-1 rounded-full font-semibold shadow-sm">
            {badgeCount}
          </span>
        )}
      </div>

      {/* Content */}
      <div className="px-6 py-5">
        {title === "Overview" ? (
          <p className="text-gray-700 leading-7">{items}</p>
        ) : (
          <ul className="list-disc pl-5 space-y-2 text-gray-700">
            {items.map((x, i) => (
              <li key={i}>{x}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default function Timeline() {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    const cached = localStorage.getItem("summaryPreview");
    if (cached) {
      try {
        setSummary(JSON.parse(cached));
      } catch {}
    } else {
      const meetingId = localStorage.getItem("meetingId");
      if (meetingId) getSummary(meetingId).then(setSummary).catch(() => {});
    }
  }, []);

  const meetingTitle = localStorage.getItem("meetingTitle") || "Conversation Timeline";

  const counts = {
    kp: summary?.key_points?.length || 0,
    dc: summary?.decisions?.length || 0,
    ai: summary?.action_items?.length || 0,
  };
  const totalPoints = counts.kp + counts.dc + counts.ai;
  const subtitle = `${totalPoints} summary point${totalPoints === 1 ? "" : "s"}`;

  return (
    <div className="page">
      {/* Header */}
      <div className="page-header">
        <h1 className="page-header-title">{meetingTitle}</h1>
        <p className="page-header-subtitle">{subtitle}</p>
      </div>

      {/* Overview */}
      <SectionCard title="Overview" icon={icons.lightning} items={summary?.overview || ""} />

      {/* Details grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SectionCard
          title="Key Points"
          icon={icons.list}
          items={summary?.key_points || []}
          badgeCount={counts.kp}
        />
        {counts.dc > 0 && (
          <SectionCard
            title="Decisions"
            icon={icons.flag}
            items={summary?.decisions || []}
            badgeCount={counts.dc}
          />
        )}
        <SectionCard
          title="Action Items"
          icon={icons.check}
          items={(summary?.action_items || []).map((x) => x?.task ?? x)}
          badgeCount={counts.ai}
        />
      </div>

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