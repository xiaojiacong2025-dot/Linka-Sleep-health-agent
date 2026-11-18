from __future__ import annotations

from datetime import datetime
import os

import httpx
import pandas as pd
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Linka Sleep Health Agent", layout="wide")
st.title("Linka Sleep Health Agent")
st.caption("模拟数据工程演示；不用于医疗诊断。")


def api_get(path: str, params: dict | None = None):
    with httpx.Client(timeout=15) as client:
        response = client.get(f"{API_URL}{path}", params=params)
        response.raise_for_status()
        return response.json()


try:
    health = api_get("/health")
    st.sidebar.success(f"API: {health['status']} · {health['mode']}")
    sessions = api_get("/sessions")["items"]
except Exception as exc:
    st.error(f"无法连接 API：{type(exc).__name__}。请先启动 uvicorn。")
    st.stop()

tab_signal, tab_metrics, tab_chat = st.tabs(["信号查看", "指标趋势", "智能问答"])
with tab_signal:
    waveform_sessions = [s for s in sessions if s["source_kind"] == "waveform_derived"]
    if waveform_sessions:
        session_id = st.selectbox("波形会话", [s["session_id"] for s in waveform_sessions])
        start_s = st.slider("起始秒", 0, 780, 0, 10)
        data = api_get(f"/sessions/{session_id}/signal", {"start_s": start_s, "end_s": start_s + 30})
        frame = pd.DataFrame({"时间 (s)": data["time_s"], "原始 ECG": data["raw_ecg_mv"],
                              "滤波 ECG": data["filtered_ecg_mv"]}).set_index("时间 (s)")
        st.line_chart(frame)
        st.caption(f"本区间检测到 {len(data['r_peaks_s'])} 个 R 峰；图表仅为降采样显示。")
    else:
        st.info("尚无波形会话，请运行 prepare_demo.py。")

with tab_metrics:
    session = st.selectbox("指标会话", sessions, format_func=lambda s: f"{s['session_id']} · {s['source_kind']}")
    metric = st.radio("指标", ["heart_rate", "rmssd"], horizontal=True)
    items = api_get("/metrics", {"metric": metric, "start_time": session["start_time"],
                                  "end_time": session["end_time"]})["items"]
    if items:
        frame = pd.DataFrame(items)
        frame["start_time"] = pd.to_datetime(frame["start_time"])
        st.line_chart(frame.set_index("start_time")["value"])
        st.dataframe(frame[["start_time", "value", "quality_status", "coverage"]], use_container_width=True)
        st.caption("多夜 direct_simulation 指标为直接模拟；waveform_derived 指标由模拟 ECG 提取。")
    else:
        st.info("该时段没有指标。")

with tab_chat:
    st.write("示例：‘最近一晚的 RMSSD 与历史基线相比如何？’、‘RMSSD 是什么？’")
    question = st.text_input("问题")
    if st.button("发送", disabled=not question):
        with httpx.Client(timeout=60) as client:
            response = client.post(f"{API_URL}/chat", json={"message": question, "conversation_id": "streamlit-demo"})
            response.raise_for_status()
            result = response.json()
        st.write(result["answer"])
        if result["limitations"]:
            st.warning("；".join(result["limitations"]))
        if result["data_evidence"]:
            with st.expander("数据依据"):
                st.json(result["data_evidence"])
        if result["knowledge_citations"]:
            st.subheader("知识来源")
            for citation in result["knowledge_citations"]:
                st.markdown(f"- [{citation['source_title']}]({citation['source_url']})")
