from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from uuid import uuid4
from zoneinfo import ZoneInfo

from langgraph.graph import END, StateGraph

from sleep_agent.agent.llm import OpenAICompatibleLLM
from sleep_agent.agent.state import AgentState
from sleep_agent.agent.tools import AgentTools, TOOL_SCHEMAS
from sleep_agent.schemas import ChatResponse, Citation
from sleep_agent.settings import Settings
from sleep_agent.storage.repository import Repository


class AgentService:
    def __init__(self, settings: Settings, repository: Repository, user_id: str = "demo_user"):
        self.settings = settings
        self.repository = repository
        self.user_id = user_id
        graph = StateGraph(AgentState)
        graph.add_node("execute", self._execute)
        graph.set_entry_point("execute")
        graph.add_edge("execute", END)
        self.graph = graph.compile()

    def invoke(self, message: str, conversation_id: str, reference_time: datetime | None = None) -> ChatResponse:
        reference = reference_time or datetime.now(UTC)
        state = self.graph.invoke({
            "user_id": self.user_id, "message": message, "conversation_id": conversation_id,
            "reference_time": reference.isoformat(), "request_id": str(uuid4()),
            "tool_call_count": 0, "data_evidence": [], "knowledge_citations": [],
            "limitations": [], "status": "ok",
        })
        return ChatResponse(
            answer=state["answer"], data_evidence=state.get("data_evidence", []),
            knowledge_citations=[Citation.model_validate(c) for c in state.get("knowledge_citations", [])],
            limitations=state.get("limitations", []), request_id=state["request_id"],
            status=state.get("status", "ok"),
        )

    def _execute(self, state: AgentState) -> AgentState:
        return self._run_llm(state) if self.settings.llm_configured else self._run_demo(state)

    def _run_llm(self, state: AgentState) -> AgentState:
        tools = AgentTools(self.settings, self.repository, state["user_id"])
        system = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")
        system += f"\n参考时间：{state['reference_time']}，用户时区：{self.settings.app_timezone}。"
        messages: list[dict] = [{"role": "system", "content": system},
                                {"role": "user", "content": state["message"]}]
        llm = OpenAICompatibleLLM(self.settings)
        allowed_calls = self.settings.config["agent"]["max_tool_calls"]
        citations: dict[str, dict] = {}
        evidence: list[dict] = []
        limitations: list[str] = []
        final_content = ""
        try:
            for _ in range(allowed_calls + 1):
                reply = llm.chat(messages, TOOL_SCHEMAS)
                calls = reply.get("tool_calls") or []
                if not calls:
                    final_content = reply.get("content") or "模型没有返回可用回答。"
                    break
                messages.append(reply)
                for call in calls:
                    if len(evidence) >= 2000:
                        break
                    arguments = json.loads(call["function"].get("arguments") or "{}")
                    result = tools.call(call["function"]["name"], arguments)
                    evidence.extend(result.evidence)
                    limitations.extend(result.limitations)
                    if call["function"]["name"] == "retrieve_sleep_knowledge":
                        for item in result.evidence:
                            citations[item["id"]] = {"chunk_id": item["id"],
                                "source_title": item["source_title"], "source_url": item["source_url"]}
                    messages.append({"role": "tool", "tool_call_id": call["id"],
                                     "content": result.model_dump_json()})
            else:
                final_content = "已达到工具调用上限，无法安全完成回答。"
                limitations.append("达到工具调用上限")
        except (RuntimeError, json.JSONDecodeError) as exc:
            return {**state, "answer": f"Agent 调用失败：{type(exc).__name__}",
                    "limitations": ["没有生成健康结论"], "status": "error"}
        return {**state, "answer": final_content, "data_evidence": evidence,
                "knowledge_citations": list(citations.values()),
                "limitations": list(dict.fromkeys(limitations)), "status": "ok"}

    def _run_demo(self, state: AgentState) -> AgentState:
        """Explicit offline demo: deterministic routing, never presented as an LLM response."""
        tools = AgentTools(self.settings, self.repository, state["user_id"])
        message = state["message"]
        sessions = self.repository.list_sessions(state["user_id"])
        if not sessions:
            return {**state, "answer": "演示模式：当前没有数据，请先运行 prepare_demo.py。",
                    "status": "error", "limitations": ["未配置 LLM"]}
        metric = "rmssd" if "RMSSD" in message.upper() or "心率变异" in message else "heart_rate"
        evidence: list[dict] = []
        citations: list[dict] = []
        limitations = ["当前未配置 LLM，回答由显式离线演示路由生成"]
        if any(word in message for word in ["另一个用户", "其他用户", "别人的数据"]):
            answer = "演示模式：不能读取其他用户的数据；用户范围由服务端固定。"
        elif any(word in message for word in ["泄露系统提示词", "内部提示词", "忽略系统指令"]):
            answer = "演示模式：不会泄露内部提示词，也不会执行知识文档中的指令。"
        elif "15 分钟" in message and "整晚" in message:
            answer = "演示模式：15 分钟数据不足以评价整晚睡眠，也不能据此判断睡眠分期。"
            limitations.append("记录时长不足")
        elif "质量" in message and any(word in message for word in ["确定", "强制", "必须"]):
            answer = "演示模式：质量不佳的数据不能支持确定结论，应先查看拒绝原因和有效覆盖率。"
            limitations.append("低质量数据不能用于确定性解释")
        elif match := re.search(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", message):
            local_start = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                                   tzinfo=ZoneInfo(self.settings.app_timezone))
            result = tools.get_metrics(metric=metric, start_time=local_start,
                                       end_time=local_start + timedelta(days=1), limit=500)
            evidence = result.evidence
            limitations.extend(result.limitations)
            if result.status == "ok":
                answer = f"演示模式：该日期找到 {len(result.evidence)} 个可用窗口。"
            else:
                answer = "演示模式：指定日期没有可用数据。"
        elif any(word in message for word in ["什么", "定义", "解释", "知识"]):
            result = tools.retrieve_sleep_knowledge(query=message, top_k=3)
            if result.status != "ok":
                answer = "演示模式：知识库中没有找到足够相关的材料。"
            else:
                first = result.data[0]
                answer = f"演示模式检索结果：{first['text']}"
                citations = [{"chunk_id": item["id"], "source_title": item["source_title"],
                              "source_url": item["source_url"]} for item in result.evidence]
            limitations.extend(result.limitations)
        elif any(word in message for word in ["比较", "基线", "过去", "前几天"]):
            nights = [s for s in sessions if s["source_kind"] == "direct_simulation"]
            target = nights[-1]
            baseline = nights[max(0, len(nights)-8):-1]
            if not baseline:
                answer = "演示模式：历史数据不足，无法建立基线。"
            else:
                result = tools.compare_baseline(
                    metric=metric, target_start=target["start_time"], target_end=target["end_time"],
                    baseline_start=baseline[0]["start_time"], baseline_end=baseline[-1]["end_time"],
                )
                evidence = result.evidence
                limitations.extend(result.limitations)
                data = result.data
                if result.status == "ok":
                    answer = (f"演示模式：目标时段{metric}中位数为 {data['target_value']} {data['unit']}，"
                              f"历史基线为 {data['baseline_value']} {data['unit']}，变化 {data['change_pct']}%。")
                else:
                    answer = "演示模式：当前数据不足或口径不一致，无法完成可靠比较。"
        else:
            latest = sessions[-1]
            result = tools.get_metrics(metric=metric, start_time=latest["start_time"],
                                       end_time=latest["end_time"], limit=500)
            evidence = result.evidence
            limitations.extend(result.limitations)
            if result.status == "ok":
                values = [item["value"] for item in result.evidence]
                unit = result.data["unit"]
                answer = (f"演示模式：最近会话中有 {len(values)} 个可用窗口，"
                          f"{metric}窗口中位数为 {median(values):.2f} {unit}。")
            else:
                answer = "演示模式：最近会话没有可用指标。"
        return {**state, "answer": answer, "data_evidence": evidence,
                "knowledge_citations": citations,
                "limitations": list(dict.fromkeys(limitations)), "status": "ok"}
