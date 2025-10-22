# app/utils/persist_utterances.py
from __future__ import annotations

from typing import List, Dict, Any, Iterable
from sqlalchemy import text as sqltext
from app.utils.db import DB


def _to_seconds(v: float | int | None) -> float:
    """
    Normalize timestamps into seconds.
    - If value is None -> 0.0
    - If value looks like milliseconds (>= 1000) -> convert to seconds
    - Otherwise assume already seconds.
    """
    if v is None:
        return 0.0
    try:
        x = float(v)
    except Exception:
        return 0.0
    # Heuristic: ms if >= 1000
    return x / 1000.0 if x >= 1000.0 else x


def _normalize_segments(
    segments: Iterable[Dict[str, Any]],
    speaker_default: str = "Speaker",
) -> List[Dict[str, Any]]:
    """
    Normalize any provider's segment dicts into the canonical shape:
        {"speaker": str, "start": float(sec), "end": float(sec), "text": str}
    Accepts keys like start/end (sec or ms), or "start_ms"/"end_ms".
    """
    out: List[Dict[str, Any]] = []
    for s in segments or []:
        # Try common keys
        start = (
            s.get("start_seconds")
            or s.get("start_sec")
            or s.get("start")
            or s.get("start_ms")
            or 0
        )
        end = (
            s.get("end_seconds")
            or s.get("end_sec")
            or s.get("end")
            or s.get("end_ms")
            or 0
        )
        spk = s.get("speaker") or s.get("speaker_label") or speaker_default
        txt = s.get("text") or ""

        # Support AssemblyAI: its "utterances" are in ms
        # If keys "start" / "end" exist but look like ms, _to_seconds handles it.
        start_s = _to_seconds(start)
        end_s = _to_seconds(end)

        # Guard against inverted/invalid times
        if end_s < start_s:
            start_s, end_s = end_s, start_s
        out.append({"speaker": str(spk), "start": float(start_s), "end": float(end_s), "text": str(txt)})
    return out


def persist_utterances(
    meeting_id: str,
    segments: Iterable[Dict[str, Any]],
    *,
    replace_existing: bool = True,
) -> int:
    """
    Persist utterances into the DB.

    Parameters
    ----------
    meeting_id : str
        The meeting id to attach rows to.
    segments : iterable of dict
        Each item should describe one utterance. Keys accepted:
          - speaker / speaker_label
          - start_seconds / start_sec / start / start_ms
          - end_seconds / end_sec / end / end_ms
          - text
        Units can be seconds or milliseconds; they’ll be normalized to seconds.
    replace_existing : bool
        If True, delete any existing utterances for this meeting before insert
        (helps avoid duplicates if poll/webhook fires multiple times).

    Returns
    -------
    int : count of rows inserted.
    """
    rows = _normalize_segments(segments)
    if not rows:
        return 0

    db = DB()
    inserted = 0
    with db.engine.begin() as con:
        if replace_existing:
            con.execute(sqltext("DELETE FROM utterances WHERE meeting_id = :m"), {"m": meeting_id})

        for r in rows:
            con.execute(sqltext(
                """
                INSERT INTO utterances (meeting_id, speaker, start_seconds, end_seconds, text)
                VALUES (:m, :speaker, :start, :end, :text)
                """
            ), {
                "m": meeting_id,
                "speaker": r["speaker"],
                "start": r["start"],
                "end": r["end"],
                "text": r["text"],
            })
            inserted += 1

        # Mark meeting status
        con.execute(sqltext(
            "UPDATE meetings SET status='asr_completed' WHERE id=:m"
        ), {"m": meeting_id})

    return inserted


# ----------------------------
# Provider-specific adapters
# ----------------------------

def segments_from_assemblyai(transcript_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert AssemblyAI response (with 'utterances') into generic segments.
    AssemblyAI 'utterances' items typically have:
        {'start': 1234, 'end': 4567, 'text': '...', 'speaker': 'A'}  # times in ms
    """
    utterances = transcript_json.get("utterances") or []
    segments: List[Dict[str, Any]] = []
    for u in utterances:
        segments.append({
            "speaker": u.get("speaker") or "Speaker",
            "start": u.get("start"),     # ms
            "end": u.get("end"),         # ms
            "text": u.get("text") or ""
        })
    return segments