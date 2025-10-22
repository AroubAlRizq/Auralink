from typing import List, Dict
import re

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def _split_text(text: str, max_chars: int) -> List[str]:
    """
    Split long utterance text into sentence-ish pieces; if any piece
    still exceeds max_chars, hard-wrap it.
    """
    text = (text or "").strip()
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)

    out: List[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) <= max_chars:
            out.append(p)
        else:
            # hard-wrap long sentence
            i = 0
            while i < len(p):
                out.append(p[i : i + max_chars].strip())
                i += max_chars
    return out

def chunk_utterances(
    utterances: List[Dict],
    max_chars: int = 500,               # lowered from 900
    time_cap_seconds: float = 20.0,     # new: force new chunk if span exceeds this
    break_on_speaker_change: bool = True,
) -> List[Dict]:
    """
    Input utterances: [{"speaker":..., "start_seconds":..., "end_seconds":..., "text":...}, ...]
    Output chunks: [{"text":..., "speaker":..., "start_seconds":..., "end_seconds":..., "topic": None}]
    Rules:
      - keep chunks <= max_chars (approx),
      - never let a chunk cover > time_cap_seconds,
      - optionally break when speaker changes.
    """
    chunks: List[Dict] = []
    buf = ""
    start = end = None
    spk = None

    def _flush():
        nonlocal buf, start, end, spk
        if buf:
            chunks.append({
                "text": buf.strip(),
                "speaker": spk or "SPEAKER",
                "start_seconds": float(start if start is not None else 0.0),
                "end_seconds": float(end if end is not None else 0.0),
                "topic": None
            })
        buf = ""
        spk = None
        start = end = None

    for u in utterances:
        u_text = (u.get("text") or "").strip()
        if not u_text:
            continue

        u_speaker = u.get("speaker") or "SPEAKER"
        u_start = float(u.get("start_seconds", 0.0))
        u_end = float(u.get("end_seconds", u_start))

        # If speaker changes and we have content, flush chunk
        if break_on_speaker_change and buf and spk is not None and u_speaker != spk:
            _flush()

        # Ensure chunk has an initial speaker and start time
        if not buf:
            spk = u_speaker
            start = u_start
            end = u_end

        # Split the utterance text into manageable pieces
        segments = _split_text(u_text, max_chars)

        for seg in segments:
            # If adding seg would exceed char cap or time cap, flush first
            would_len = (len(buf) + (1 if buf else 0) + len(seg))
            would_end = max(end if end is not None else u_end, u_end)
            would_span = (would_end - (start if start is not None else u_start))

            if buf and (would_len > max_chars or would_span > time_cap_seconds):
                _flush()
                spk = u_speaker
                start = u_start
                end = u_end

            # Start new or append
            if not buf:
                buf = seg
                spk = u_speaker
                start = u_start
                end = u_end
            else:
                buf = f"{buf} {seg}"
                end = max(end, u_end)

            # If after appending we exceed time cap, flush immediately
            if (end - start) > time_cap_seconds:
                _flush()

    _flush()
    return [c for c in chunks if c["text"]]

def chunk_summary(summary: dict) -> List[Dict]:
    """Index summary bullets as separate chunks (great for retrieval)."""
    out: List[Dict] = []
    for bullet in summary.get("executive_summary", []):
        out.append({
            "text": bullet,
            "speaker": "SUMMARY",
            "start_seconds": 0.0,
            "end_seconds": 0.0,
            "topic": "executive_summary"
        })
    for d in summary.get("decisions", []):
        out.append({
            "text": d.get("text", ""),
            "speaker": "SUMMARY",
            "start_seconds": float(d.get("timestamp", 0.0)),
            "end_seconds": float(d.get("timestamp", 0.0)),
            "topic": "decisions"
        })
    for a in summary.get("action_items", []):
        out.append({
            "text": f'{a.get("owner","")} : {a.get("task","")}' + (f' (due {a.get("due")})' if a.get("due") else ""),
            "speaker": "SUMMARY",
            "start_seconds": float(a.get("timestamp", 0.0)),
            "end_seconds": float(a.get("timestamp", 0.0)),
            "topic": "action_items"
        })
    return out
