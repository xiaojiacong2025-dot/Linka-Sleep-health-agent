# Linka Sleep Health Agent

一个基于灵络SE睡眠穿戴设备数据的工程演示：生成 ECG、体动与接触状态，完成离线滤波、R 峰检测、心率/RMSSD 和质量门控，再通过受限工具、知识检索和 Agent 回答问题。

因为保护公司数据，此demo使用经处理过的模拟数据，不可代表任何真实设备规格，也不用于医疗诊断。

## 当前功能

- 提供了可复现的 15 分钟模拟 ECG，包含基线漂移、噪声、丢包、体动和接触不良
- 连续有效片段的离线带通滤波与演示用 R 峰检测
- 5 分钟窗口、1 分钟步长的心率和 RMSSD
- 直接模拟的多夜指标，用于历史比较演示
- SQLite 会话、指标和 FTS5 知识索引
- `get_metrics`、`compare_baseline`、`retrieve_sleep_knowledge` 三个工具
- LangGraph 单 Agent 入口、FastAPI 和 Streamlit 页面
- 无 LLM 密钥时明确运行离线演示路由

## 数据流

```text
模拟 ECG -> 分段滤波 -> R 峰 -> RR 质量检查 -> HR/RMSSD -> SQLite
公开资料 -> Markdown 切分 -> 中文字符二元索引 ---------> SQLite
用户问题 -> Agent 工具 -> 数据与知识证据 -> 回答
```

详细设计见 `docs/architecture.md`，字段和统计口径见 `docs/data_dictionary.md`。

## Windows 快速开始

要求 Python 3.11。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts\prepare_demo.py
.\.venv\Scripts\python.exe scripts\build_knowledge.py
.\.venv\Scripts\python.exe -m pytest
```

启动 API：

```powershell
.\.venv\Scripts\python.exe -m uvicorn sleep_agent.api.main:app --reload
```

另开终端启动页面：

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend\app.py
```

默认页面地址为 `http://localhost:8501`，API 文档为 `http://127.0.0.1:8000/docs`。

## 配置真实 LLM

复制 `.env.example` 为 `.env`，填写 OpenAI-compatible Chat Completions 服务：

```dotenv
LLM_API_KEY=your-key
LLM_BASE_URL=https://your-provider.example/v1
LLM_MODEL=your-tool-calling-model
```
---此处请填写你自己的api_key哦
未填写密钥时，`/health` 返回 `offline_demo`。此模式用确定性规则演示工具和证据链，回答会明确写出“演示模式”。填写密钥后，Agent 才会进行真实模型工具调用。

## 示例问题

- 最近一次使用的心率是多少？
- 今晚的 RMSSD 与过去七晚相比如何？
- RMSSD 是什么？
- 哪些窗口因为质量问题没有输出指标？

## API

- `GET /health`
- `GET /sessions`
- `GET /sessions/{session_id}/signal`
- `GET /metrics`
- `POST /chat`

波形接口只允许最多 120 秒，并对展示数据降采样；后台指标计算使用原始采样数据。演示身份固定为 `demo_user`，当前版本没有生产级登录系统。

## 测试与评估

```powershell
python -m pytest
python evaluation\run_eval.py
```
-------------------
没有 LLM 配置时，评估脚本会把模型检查报告为 `skipped`，不会伪报通过。
-------------------------------

## 须知注意
这是我们放出来的一个demo，提供给大家参考，没有放置真实数据，不可作为医疗认证等领域。
- ECG 形态、阈值和质量规则都是演示参数。
- 简单峰检测只针对模拟信号调参。
- 多夜指标是直接模拟值，与波形提取结果明确分开。
- FTS5 使用字符二元词法检索，不包含语义向量和重排模型。
- 自然语言中的复杂日期解析依赖模型；离线演示只处理有限意图。
- 引用 ID 和数值证据经过结构校验，但不能保证所有自然语言结论都正确。

