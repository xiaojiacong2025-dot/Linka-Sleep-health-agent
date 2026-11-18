from __future__ import annotations

from datetime import datetime
from typing import Callable

from pydantic import BaseModel, Field, ValidationError, field_validator

from sleep_agent.rag.retriever import retrieve
from sleep_agent.schemas import ToolResult
from sleep_agent.settings import Settings
from sleep_agent.storage.repository import Repository


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timezone is required")
    return value


class GetMetricsArgs(BaseModel):
    metric: str
    start_time: datetime
    end_time: datetime
    limit: int = Field(default=200, ge=1, le=500)
    _a = field_validator("start_time", "end_time")(_aware)


class CompareArgs(BaseModel):
    metric: str
    target_start: datetime
    target_end: datetime
    baseline_start: datetime
    baseline_end: datetime
    _a = field_validator("target_start", "target_end", "baseline_start", "baseline_end")(_aware)


class RetrieveArgs(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=4, ge=1, le=8)


TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "get_metrics", "description": "查询当前用户指定时段的心率或RMSSD",
     "parameters": {"type": "object", "properties": {
         "metric": {"type": "string", "enum": ["heart_rate", "rmssd"]},
         "start_time": {"type": "string", "format": "date-time"},
         "end_time": {"type": "string", "format": "date-time"},
         "limit": {"type": "integer", "minimum": 1, "maximum": 500}},
         "required": ["metric", "start_time", "end_time"]}}},
    {"type": "function", "function": {"name": "compare_baseline", "description": "比较目标时段和历史基线",
     "parameters": {"type": "object", "properties": {
         "metric": {"type": "string", "enum": ["heart_rate", "rmssd"]},
         "target_start": {"type": "string", "format": "date-time"},
         "target_end": {"type": "string", "format": "date-time"},
         "baseline_start": {"type": "string", "format": "date-time"},
         "baseline_end": {"type": "string", "format": "date-time"}},
         "required": ["metric", "target_start", "target_end", "baseline_start", "baseline_end"]}}},
    {"type": "function", "function": {"name": "retrieve_sleep_knowledge", "description": "检索睡眠、HRV和信号质量知识",
     "parameters": {"type": "object", "properties": {
         "query": {"type": "string"}, "top_k": {"type": "integer", "minimum": 1, "maximum": 8}},
         "required": ["query"]}}},
]


class AgentTools:
    def __init__(self, settings: Settings, repository: Repository, user_id: str):
        self.settings = settings
        self.repository = repository
        self.user_id = user_id

    def get_metrics(self, **kwargs) -> ToolResult:
        args = GetMetricsArgs.model_validate(kwargs)
        if args.end_time <= args.start_time or (args.end_time - args.start_time).days > 31:
            return ToolResult(status="error", limitations=["时间范围无效或超过31天"])
        rows = self.repository.query_metrics(self.user_id, args.start_time, args.end_time,
                                             args.metric, args.limit)
        usable = [row for row in rows if row["value"] is not None]
        if not usable:
            return ToolResult(status="no_data", data=[], limitations=["指定时段没有可用指标"])
        unit = "bpm" if args.metric == "heart_rate" else "ms"
        return ToolResult(status="ok", data={"metric": args.metric, "unit": unit, "windows": usable},
                          evidence=[{"id": r["window_id"], "value": r["value"], "unit": unit,
                                     "start_time": r["start_time"]} for r in usable])

    def compare_baseline(self, **kwargs) -> ToolResult:
        args = CompareArgs.model_validate(kwargs)
        result = self.repository.compare_periods(
            self.user_id, args.metric, args.target_start, args.target_end,
            args.baseline_start, args.baseline_end,
        )
        status = "ok" if result.status == "ok" else (
            "incomparable" if result.status == "incomparable" else "insufficient_data")
        evidence = [{"id": item} for item in result.target_evidence_ids + result.baseline_evidence_ids]
        return ToolResult(status=status, data=result.model_dump(mode="json"), evidence=evidence,
                          limitations=result.limitations)

    def retrieve_sleep_knowledge(self, **kwargs) -> ToolResult:
        args = RetrieveArgs.model_validate(kwargs)
        chunks = retrieve(self.settings.database_path, args.query, args.top_k)
        if not chunks:
            return ToolResult(status="no_data", data=[], limitations=["知识库没有相关内容"])
        return ToolResult(status="ok", data=[c.model_dump(mode="json") for c in chunks],
                          evidence=[{"id": c.chunk_id, "source_title": c.source_title,
                                     "source_url": c.source_url} for c in chunks])

    def call(self, name: str, arguments: dict) -> ToolResult:
        functions: dict[str, Callable] = {
            "get_metrics": self.get_metrics,
            "compare_baseline": self.compare_baseline,
            "retrieve_sleep_knowledge": self.retrieve_sleep_knowledge,
        }
        if name not in functions:
            return ToolResult(status="error", limitations=["未知工具"])
        try:
            return functions[name](**arguments)
        except (ValidationError, ValueError) as exc:
            return ToolResult(status="error", limitations=[f"工具参数无效: {exc}"])

