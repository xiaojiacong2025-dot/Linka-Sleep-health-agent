from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    user_id: str
    message: str
    conversation_id: str
    reference_time: str
    request_id: str
    tool_call_count: int
    data_evidence: list[dict[str, Any]]
    knowledge_citations: list[dict[str, str]]
    limitations: list[str]
    answer: str
    status: str

