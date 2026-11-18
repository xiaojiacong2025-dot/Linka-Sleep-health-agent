from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include timezone information")
    return value


class SessionMetadata(BaseModel):
    session_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    sampling_rate_hz: float | None = None
    signal_path: str | None = None
    source_kind: Literal["waveform_derived", "direct_simulation"]
    algorithm_version: str = "demo-0.1"

    _start_aware = field_validator("start_time")(_aware)
    _end_aware = field_validator("end_time")(_aware)


class SignalSegment(BaseModel):
    session_id: str
    start_offset_s: float
    end_offset_s: float
    time_s: list[float]
    raw_ecg_mv: list[float | None]
    filtered_ecg_mv: list[float | None]
    r_peaks_s: list[float]
    motion: list[bool]
    contact: list[bool]


class WindowMetrics(BaseModel):
    window_id: str
    session_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    heart_rate_bpm: float | None = None
    rmssd_ms: float | None = None
    coverage: float = Field(ge=0, le=1)
    contact_fraction: float = Field(ge=0, le=1)
    motion_fraction: float = Field(ge=0, le=1)
    quality_status: Literal["usable", "insufficient_quality"]
    quality_reasons: list[str] = []
    valid_rr_count: int = Field(ge=0)
    window_seconds: int
    sampling_rate_hz: float | None = None
    algorithm_version: str
    source_kind: Literal["waveform_derived", "direct_simulation"]

    _start_aware = field_validator("start_time")(_aware)
    _end_aware = field_validator("end_time")(_aware)


class MetricsQuery(BaseModel):
    metric: Literal["heart_rate", "rmssd"]
    start_time: datetime
    end_time: datetime
    limit: int = Field(default=500, ge=1, le=2000)

    _start_aware = field_validator("start_time")(_aware)
    _end_aware = field_validator("end_time")(_aware)


class BaselineComparison(BaseModel):
    status: Literal["ok", "insufficient_baseline", "incomparable", "no_target_data"]
    metric: str
    target_value: float | None = None
    baseline_value: float | None = None
    change_pct: float | None = None
    unit: str
    target_evidence_ids: list[str] = []
    baseline_evidence_ids: list[str] = []
    limitations: list[str] = []


class KnowledgeChunk(BaseModel):
    chunk_id: str
    text: str
    source_id: str
    source_title: str
    source_url: str
    section: str
    rank: float | None = None


class ToolResult(BaseModel):
    status: Literal["ok", "no_data", "error", "insufficient_data", "incomparable"]
    data: Any = None
    evidence: list[dict[str, Any]] = []
    limitations: list[str] = []


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str = Field(default="default", min_length=1, max_length=100)
    reference_time: datetime | None = None


class Citation(BaseModel):
    chunk_id: str
    source_title: str
    source_url: str


class ChatResponse(BaseModel):
    answer: str
    data_evidence: list[dict[str, Any]] = []
    knowledge_citations: list[Citation] = []
    limitations: list[str] = []
    request_id: str
    status: Literal["ok", "needs_clarification", "error"] = "ok"
