# 面试知识清单

[返回总览](./README.md) · [第 1 轮计划](./rounds/001.md)

优先级是备考建议，不是面试题频率统计。掌握分三层：能解释原理、能独立实现、能用结果验证；仅看过教程不算完成。复盘时记录对应证据，不预先勾选。

## P0：必须能解释并实现

| 知识点 | 突击范围 | 自测／验收 |
|--------|----------|-----------|
| LLM API 与结构化输出 | messages、system prompt、token、context window、streaming、JSON Schema；JSON mode 与 schema 约束 | 解释合法 JSON 为什么不等于合法业务输入；temperature=0 为什么不保证完全确定性 |
| Agent Loop | 模型调用、工具请求、程序执行、结果回填、再次调用、终止与预算 | 不用 Agent 框架实现多轮循环；正确关联 tool call ID 与结果 |
| Tool Calling | 工具描述、参数 schema、校验、注册与分发、错误处理、独立工具并行 | 模型提出调用，程序执行；未知工具、非法参数、越权操作不能直接执行 |
| Prompt／Context Engineering | 指令与数据分离、few-shot、按需检索、摘要、裁剪、工具结果截断 | 缩减上下文时保留目标、约束与未完成动作；外部文本不升级为系统指令 |
| RAG | chunking、embedding、BM25、向量／混合检索、reranking、metadata filter、引用、拒答 | 分清检索遗漏、排序错误、上下文不足与生成不遵循证据 |
| Evals | 成功标准、任务集、最终状态、执行轨迹、代码评分、LLM judge、人工校准、回归 | “已创建工单”必须用实际数据库状态验证；比较模型／prompt 改动前后 |
| 可靠性与状态 | 超时、限流、退避、幂等、checkpoint、恢复、取消、执行与业务状态 | 写操作超时不能盲目重试；恢复后不能重复写入或误报成功 |
| 安全 | prompt injection、最小权限、白名单、沙箱、凭据隔离、审批、租户隔离 | 权限在程序边界强制执行，不依赖模型遵守 prompt |

## P1：能解释取舍，选重点实践

| 知识点 | 突击范围 | 自测问题 |
|--------|----------|----------|
| Workflow vs. Agent | 固定流程与动态决策；routing、chaining、orchestrator-workers | 什么步骤应该写成确定性代码？为什么不是所有任务都需要自主 Agent？ |
| 一个编排框架 | 默认选 LangGraph 的 state、node、edge、checkpoint、interrupt；按 JD 可换 Agents SDK | 框架比手写 loop 提供什么？哪些复杂性仍由业务代码负责？ |
| Memory | 会话历史、工作状态、长期记忆；写入、召回、过期与删除 | Memory 与 RAG 的用途有何不同？如何纠正错误记忆和隔离用户？ |
| MCP | host／client／server、tools／resources／prompts、stdio／Streamable HTTP、权限 | MCP 是工具与上下文接入协议，不是规划器；如何与 function calling 配合？ |
| 多 Agent | delegation、handoff、共享状态、上下文隔离、并行与汇总 | 拆分的收益能否覆盖成本、延迟和协调错误？ |
| 可观测性与成本 | trace／span、工具耗时、失败分类、token、单任务成本、P50／P95、缓存、模型路由 | 如何定位变慢或变差？如何测量优化，而不是凭感觉？ |

## P2：除非 JD 要求，暂不深挖

- Transformer 数学推导、从零训练、分布式训练。
- LoRA／RLHF／GRPO 的完整实现。
- 同时学习多个 Agent 框架。
- 大规模多 Agent 群体协作与复杂向量数据库运维。

普通工程能力仍需准备：Python 或 TypeScript、JSON、HTTP、异步并发、异常处理、事务、测试。优先使用最熟悉的语言。

## 评估概念

- **Outcome**：最终环境／业务状态。例如工单是否真的落库。
- **Trajectory**：执行轨迹。例如用了哪些工具、参数、重试和审批。
- **pass@k**：k 次尝试中至少成功一次的概率。
- **pass^k**：k 次尝试全部成功的概率。一次演示成功不能证明稳定可靠。
- 能客观校验的结果优先用代码评分；开放式质量使用有明确 rubric 的 LLM judge，并通过人工抽查校准。
- 不强制唯一工具路径，除非业务／安全要求该顺序；评价合法结果，而不是惩罚有效替代方案。
- 每次评估隔离初始状态，避免残留数据污染结果；记录样本数、重复次数、模型和配置。

## 脱稿自测题

1. 不用框架如何实现 Agent？
2. Tool calling 的完整生命周期是什么？结果如何对应调用？
3. 为什么选择 Agent，而不是固定 workflow 或普通 RAG？
4. 如何设计工具，让模型更容易选对、传对参数？
5. 如何防止无限循环和成本失控？
6. RAG 回答错误如何逐层定位？
7. 长对话压缩时哪些信息不能丢？
8. 如何证明任务真的完成，而不是只说完成？
9. 写工具超时如何恢复，为什么不能盲目重试？
10. 如何处理 prompt injection 和越权操作？
11. 什么场景值得用多 Agent？
12. 模型／prompt 更新后如何证明质量、成本、延迟变化？

系统设计表达顺序：业务目标与成功标准 → 是否需要 Agent → 工具与权限 → 状态与恢复 → 上下文与检索 → 评估 → 成本与延迟。

## 调研来源

调研日期：2026-10-07。以下是资料入口，不是已完成的学习记录。

| 平台 | 来源 | 使用重点 |
|------|------|----------|
| GitHub | [Agentic AI Engineering](https://github.com/agenticloops-ai/agentic-ai-engineering) | Foundations、tool use、agent loop、Testing & Evaluation；部分后续章节标注 coming soon，不当作已可用教程 |
| GitHub | [12-Factor Agents](https://github.com/humanlayer/12-factor-agents) | 控制 prompt、context、control flow；统一状态、暂停恢复、人工介入 |
| GitHub | [LangGraph](https://github.com/langchain-ai/langgraph) | 有状态编排、持久执行、人工介入 |
| GitHub | [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) | 按目标 JD 选择的另一框架入口，不要求同时学习 |
| X | [Anthropic：Agent Evals](https://x.com/AnthropicAI/status/2009696515061911674) | 评估复杂性；技术内容通过下面的官方文章核对 |
| Reddit | [Agent coding interview](https://www.reddit.com/r/Anthropic/comments/1wy1bd7/agent_coding_interview/) | 发帖者描述的工具实现、prompt 调整与现有 loop 优化练习；是个人经验，不是官方题库 |
| Reddit | [AI Engineering Agents Interview Prep](https://www.reddit.com/r/cscareerquestionsuk/comments/1qmybi3/ai_engineering_agents_interview_prep/) | 架构、工具、失败恢复、上下文、成本与系统设计讨论 |
| 官方文章 | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | outcome／trajectory、grader、pass@k／pass^k、隔离评估环境 |

证据边界：GitHub 相关仓库和官方评估文章已在本次调研中读取；X 与部分 Reddit 页面直接访问受限，相关内容来自搜索索引。社区经验不用于推断所有公司的考核标准。
