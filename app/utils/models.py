from dataclasses import dataclass
from typing import Optional, Any, List
from datetime import datetime

@dataclass
class Meeting:
    id: Optional[int] = None
    title: str = ""
    consent: bool = False
    status: str = "pending"
    video_url: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass
class Utterance:
    id: Optional[int] = None
    meeting_id: int = 0
    speaker: str = ""
    start_seconds: float = 0.0
    end_seconds: float = 0.0
    text: str = ""
    created_at: Optional[datetime] = None

@dataclass
class ASRJob:
    id: str = ""
    meeting_id: int = 0
    provider: str = ""
    status: str = ""
    callback_url: Optional[str] = None
    raw: Optional[Any] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None