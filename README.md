# Felix Agent Journey

AI Agent 工程师面试准备与工程实践。

以 **7 天为一轮**滚动准备，不预设总轮数。先完成当前轮，再根据实际复盘、目标 JD 和面试反馈追加下一轮；不提前安排固定 30 天或 90 天路线。

创建日期：2026-10-07。目标默认是 AI Agent 应用开发工程师，而非模型训练／算法研究岗。

## 实战环境

Python 3.13＋uv，已实现原生 Agent Loop、中文／英文 BM25 检索、SQLite 工单、终端审批、幂等与 JSONL 运行记录。先使用原生 SDK，LangGraph 和 MCP 保留为首轮后续学习任务，不预先代做。

### 安装与本地启动

在仓库根目录执行；需要安装 [uv](https://docs.astral.sh/uv/)：

```bash
uv sync --locked
uv run felix-agent doctor
uv run felix-agent init
uv run felix-agent search '忘记密码怎么办'
uv run felix-agent tickets
```

`init` 默认索引 `knowledge/` 中的示例 Markdown；可用 `init --docs /你的文档目录` 重建索引。重建不会删除工单，读取失败、空目录或越界符号链接会保留旧索引。示例内容是练习产品规则，不代表真实公司政策。

### 配置真实模型

本机已有未填写凭据的 `.env`；新克隆的仓库先复制配置样例：

```bash
cp .env.example .env
```

已有 `.env` 时不要覆盖。填写 `OPENAI_API_KEY`、`OPENAI_MODEL`；默认 `OPENAI_BASE_URL=https://api.openai.com/v1`，可改为支持 **Chat Completions、tools 和 max_completion_tokens** 的兼容接口。仅支持 Responses 或 Anthropic Messages 的接口不能直接使用。环境变量优先于 `.env`，应用从当前工作目录读取 `.env`。

```bash
uv run felix-agent run '忘记密码后收不到重置邮件，应该如何排查？'
uv run felix-agent run '昨天开始收不到重置邮件，已检查邮箱拼写和垃圾邮件。请创建工单。' \
  --request-id password-mail-001
```

创建前终端会展示完整工单，必须输入 `APPROVE`；其他输入、EOF 或非交互终端均拒绝写入。聊天里说“同意”不能绕过终端审批，没有自动批准开关。

模型调用缺配置时明确退出，不使用模拟模型或固定答案。不同提供方的工具行为和检索回答质量需用真实模型评估；文档引用、拒答与“只有落库才报告成功”目前由系统指令引导，不是语义正确性的保证。

### 不使用模型也能练习审批与持久化

```bash
uv run felix-agent create --title '密码邮件未送达' \
  --description '昨天开始收不到重置邮件，已检查邮箱拼写和垃圾邮件。' \
  --request-id password-mail-001
uv run felix-agent tickets
uv run felix-agent tickets 1
```

同一 `request_id` 和相同内容重复提交返回原工单；同一 ID 对应不同内容则拒绝。一个 ID 对应一个工单，重试需复用 ID；省略时自动生成新 ID，不提供跨 ID 去重。每次写请求仍需人工确认。

### 代码与运行数据

- `src/felix_agent/agent.py`：模型调用、工具结果回填、终止与失败状态。
- `src/felix_agent/tools.py`：三个工具的 schema、严格参数校验和审批边界。
- `src/felix_agent/retrieval.py`：文档分块与 BM25；中文二元组分词，适合小语料。
- `src/felix_agent/storage.py`：SQLite 事务、唯一键、索引与工单持久化。
- `src/felix_agent/cli.py`：本地命令与终端交互。
- `.data/workspace.sqlite3`：本地数据库；`.data/traces/*.jsonl`：模型响应、工具参数／结果、耗时和 token usage。提供方不返回 usage 时总 token 为 null；不虚构成本。

可用全局参数 `--data-dir` 隔离练习，例如 `uv run felix-agent --data-dir .data/day-1 init`。不要将不同练习数据混用。默认每次任务最多 8 次模型调用，每次输出上限 1024 tokens，每次 HTTP 请求超时 30 秒，SDK 自动重试关闭；可用 `run --max-steps`、`--max-output-tokens`、`--timeout` 调整。输出预算不限制输入 token，HTTP 超时不限制人工审批等待时间。

步数耗尽后不再执行待处理工具。JSONL 是运行记录，不是 checkpoint；重启后不会恢复对话，已落库工单依靠 request_id 防重复。工具按序执行，当前不提供并行工具、向量检索、长期记忆、多租户或外部工单系统。

**数据边界：**模型提供方会收到问题和检索结果；日志可能包含工单和文档内容。仅使用非敏感练习数据。`.env`、`.venv/`、`.data/` 已被 Git 忽略；自定义数据目录放在 `.data/` 下或自行加入忽略规则。

### 验证

```bash
uv run ruff check src tests
uv run pytest tests/test_tools.py tests/test_agent.py -q
```

针对性测试覆盖审批拒绝、非法／越权参数、跨重启与并发幂等、索引安全、无证据检索、步数耗尽禁止写入、输出截断与模型失败后的状态。API 测试使用隔离 HTTP transport，不建立真实模型质量结论；真实终端审批、落库与重试已在本地验证。Day 6 仍需建立业务任务集并跑真实模型 evals。

## 从这里开始

1. 阅读[知识清单](./knowledge-checklist.md)，识别自己能解释、能实现、能验证的内容。
2. 执行[第 1 轮：基础闭环与可展示项目](./rounds/001.md)，从实际开始日期计算 Day 1–7。
3. 每天记录实际产出、证据与卡点；没有完成的条目保持未完成，不把计划写成成果。
4. 第 7 天复盘后，决定下一轮的主题，再新增 7 天。

## 轮次索引

| 轮次 | 主题 | 状态 | 实际日期 |
|------|------|------|----------|
| [第 1 轮](./rounds/001.md) | Agent 基础闭环、业务项目、评估与面试表达 | 待开始 | 开始后填写 |

## 追加下一轮的约定

- 文件依次使用 `rounds/002.md`、`rounds/003.md`，每次只新增一轮 7 天。
- 保留旧轮计划和复盘，不覆盖历史，不预先创建空轮次文件。
- 新轮开头写清：上一轮证据、尚未解决的缺口、本轮目标、验收标准。
- 每天包含学习／实现任务、具体产出与自测问题；结尾包含实际记录和复盘。
- 下一轮优先处理影响求职的缺口：基础未闭环就补基础；已有闭环就按 JD 或面试反馈深化。
- 未完成项可带入下一轮，但要重新排序，不机械复制所有任务。
- 创建新轮时更新本页索引，轮次状态使用“待开始／进行中／已复盘”。

## 时间与范围

- 完整计划按每天约 6–8 小时设计：约 60% 实践、25% 阅读、15% 口述复盘。
- 每天只有 2–3 小时时，优先保住原生 Agent Loop、工具、安全边界与评估闭环；框架迁移、MCP 实现降为概念准备，并如实记录未实践范围。
- 一轮只围绕一个项目推进，不同时学习多个框架，不把阅读数量当作能力证明。
- 七天结束不等于准备完成；以独立实现、行为证据和面试表达判断进展。

## 与已有资料的关系

原博客仓库 `felix-ai-blog/practice/ai-agent-goat/` 已有长期路线、项目规格与面试地图。本仓库专门记录滚动七天冲刺，不替换原资料，也不复制其长期路线。

以下资料保留在原博客仓库，不是本仓库运行或阅读的前置依赖：

- `practice/ai-agent-goat/interview-map.md`：面试地图。
- `practice/ai-agent-goat/jd-mapping.md`：岗位映射。
- `practice/ai-agent-goat/portfolio.md`：作品集表达。

## 资料使用原则

知识清单保留本次 GitHub、X、Reddit 调研入口。官方仓库与工程文章用于核对技术；社区帖子用于了解经验，不当作公司官方题库。后续轮次仅追加实际使用过的资料与结论。
