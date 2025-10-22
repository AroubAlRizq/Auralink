// src/context/MeetingContext.jsx
import { createContext, useContext, useEffect, useMemo, useState } from "react";

const MeetingCtx = createContext(null);

export function MeetingProvider({ children }) {
  const [meetingId, setMeetingId] = useState(() => localStorage.getItem("meetingId") || "");
  const [meetingTitle, setMeetingTitle] = useState(() => localStorage.getItem("meetingTitle") || "");
  const [summary, setSummary] = useState(() => {
    const cached = localStorage.getItem("summaryPreview");
    if (!cached) return null;
    try { return JSON.parse(cached); } catch { return null; }
  });
  const [utterances, setUtterances] = useState([]); // fill on demand
  // chat messages keyed by meeting (persisted in-memory until full reload)
  const [chatByMeeting, setChatByMeeting] = useState({});

  // keep mirrors in localStorage for page refresh (not required for chat)
  useEffect(() => {
    if (meetingId) localStorage.setItem("meetingId", meetingId);
  }, [meetingId]);
  useEffect(() => {
    if (meetingTitle) localStorage.setItem("meetingTitle", meetingTitle);
  }, [meetingTitle]);
  useEffect(() => {
    if (summary) localStorage.setItem("summaryPreview", JSON.stringify(summary));
  }, [summary]);

  const api = useMemo(() => ({
    meetingId, setMeetingId,
    meetingTitle, setMeetingTitle,
    summary, setSummary,
    utterances, setUtterances,
    chatMessages: chatByMeeting[meetingId] || [],
    appendChat: (m) => {
      setChatByMeeting(prev => {
        const arr = prev[meetingId] ? [...prev[meetingId]] : [];
        arr.push(m);
        return { ...prev, [meetingId]: arr };
      });
    },
    replaceChat: (arr) => {
      setChatByMeeting(prev => ({ ...prev, [meetingId]: [...arr] }));
    }
  }), [meetingId, meetingTitle, summary, utterances, chatByMeeting]);

  return <MeetingCtx.Provider value={api}>{children}</MeetingCtx.Provider>;
}

export function useMeeting() {
  const ctx = useContext(MeetingCtx);
  if (!ctx) throw new Error("useMeeting must be used inside <MeetingProvider>");
  return ctx;
}