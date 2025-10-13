from typing import List, Dict

def chunk_utterances(utterances: List[Dict], max_chars: int = 900) -> List[Dict]:
    """
    Input utterances: [{"speaker":..., "start_seconds":..., "end_seconds":..., "text":...}, ...]
    Output chunks: [{"text":..., "speaker":..., "start_seconds":..., "end_seconds":..., "topic": None}]
    """
    chunks, buf, start, end, spk = [], "", None, None, None
    for u in utterances:
        t = (u["text"] or "").strip()
        if not t: continue
        cur = len(buf)
        if cur == 0:
            buf = t; start = u["start_seconds"]; end = u["end_seconds"]; spk = u["speaker"]
        elif cur + 1 + len(t) <= max_chars:
            buf += " " + t; end = u["end_seconds"]
        else:
            chunks.append({"text": buf, "speaker": spk, "start_seconds": start, "end_seconds": end, "topic": None})
            buf = t; start = u["start_seconds"]; end = u["end_seconds"]; spk = u["speaker"]
    if buf:
        chunks.append({"text": buf, "speaker": spk, "start_seconds": start, "end_seconds": end, "topic": None})
    return chunks

def chunk_summary(summary: dict) -> List[Dict]:
    """Optionally index summary bullets as separate chunks (great for retrieval)."""
    out = []
    mid = summary["meeting_id"]
    for bullet in summary.get("executive_summary", []):
        out.append({"text": bullet, "speaker": "SUMMARY", "start_seconds": 0.0, "end_seconds": 0.0, "topic": "executive_summary"})
    for d in summary.get("decisions", []):
        out.append({"text": d["text"], "speaker": "SUMMARY", "start_seconds": d.get("timestamp", 0.0), "end_seconds": d.get("timestamp", 0.0), "topic": "decisions"})
    for a in summary.get("action_items", []):
        out.append({"text": f'{a["owner"]}: {a["task"]} (due {a.get("due","n/a")})', "speaker": "SUMMARY",
                    "start_seconds": a.get("timestamp", 0.0), "end_seconds": a.get("timestamp", 0.0), "topic": "action_items"})
    return out

