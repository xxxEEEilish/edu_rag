# 教育知识库 OpenSpec 开发顺序规划

> 来源文档：`01_教育知识库需求分析.md`、`02_教育知识库方案设计.md`  
> 工作流：每个阶段按 `propose -> apply -> archive` 闭环推进。  
> 目标：先完成一期最小可用闭环，再按风险和依赖顺序扩展后台、增量、权限、学习路径、视频和多模态能力。

---

## 1. OpenSpec 使用约定

本项目使用 OpenSpec 管理需求、设计、任务和归档。

在 Codex 对话中不需要输入真实的 `/opsx:*` 终端命令，直接使用以下表达即可：

| 目标 | 对话指令 | 实际动作 |
|------|----------|----------|
| 提出一个变更 | `propose <功能名>` 或 `规划 <功能名>` | 创建 `openspec/changes/<change-name>/`，生成 proposal、design、tasks |
| 执行一个变更 | `apply <change-name>` 或 `实现 <change-name>` | 按 tasks 写代码，并勾选任务 |
| 归档一个变更 | `archive <change-name>` 或 `归档 <change-name>` | 检查任务完成度，归档到 `openspec/changes/archive/` |

每个变更必须遵循：

1. 先 `propose`，明确范围、验收标准和任务。
2. 再 `apply`，只实现当前变更范围。
3. 完成后 `archive`，避免多个未完成变更长期混在一起。
4. 后续阶段依赖前置阶段的已归档结果。

---

## 2. 总体阶段顺序

推荐分成 8 个 OpenSpec 变更闭环：

| 顺序 | OpenSpec 变更名 | 阶段目标 | 依赖 | 归档条件 |
|------|------------------|----------|------|----------|
| 1 | `bootstrap-edu-rag-foundation` | 搭建项目骨架、配置、基础模型和工具层 | 无 | 项目可启动，配置可加载，核心目录存在 |
| 2 | `implement-content-import-pipeline` | 实现 PDF/Markdown/DOCX/题库导入链路 | 阶段 1 | 文件可上传、解析、切片、记录任务状态 |
| 3 | `implement-storage-and-indexing` | 实现 MongoDB、Milvus、MinIO 入库和索引 | 阶段 1、2 | 文档片段和题目可入库并可按元数据追溯 |
| 4 | `implement-retrieval-query-pipeline` | 实现课程、文档、题库和 RAG 查询链路 | 阶段 1、3 | 可检索、重排、生成答案并返回引用 |
| 5 | `implement-chat-history-and-streaming` | 实现多轮历史、SSE 流式输出和会话记录 | 阶段 4 | 问答可流式返回，历史可保存和查询 |
| 6 | `implement-minimal-front-pages` | 实现导入页和聊天页，完成一期联调 | 阶段 2、4、5 | 页面可完成上传、查状态、问答和查看引用 |
| 7 | `harden-mvp-acceptance-tests` | 补齐一期验收测试、示例数据和错误处理 | 阶段 2-6 | 覆盖典型课程、文档、题库、项目问答场景 |
| 8 | `prepare-phase-two-extension-points` | 预留后台、增量、权限、视频、多模态扩展点 | 阶段 7 | 数据模型和接口预留字段清晰，不阻塞后续分期 |

---

## 3. 一期 MVP 推荐执行顺序

### 阶段 1：基础工程骨架

OpenSpec 变更名：`bootstrap-edu-rag-foundation`

目标：
- 建立方案设计中的目录结构。
- 创建 FastAPI 应用入口。
- 创建 `core/config.py`、`core/enums.py`、`core/paths.py`。
- 创建 `.env.example`。
- 定义基础 Pydantic schema。
- 封装 LLM、Embedding、Reranker、MongoDB、Milvus、MinIO 的接口占位或适配层。

建议任务：
- 创建 `api/`、`core/`、`schema/`、`services/`、`processor/`、`utils/`、`front/`、`tests/`。
- 定义内容类型、任务状态、查询意图、来源类型枚举。
- 定义 `KnowledgeChunk`、`Question`、`ImportTask`、`QueryRequest`、`QueryResponse`。
- 提供健康检查接口。
- 写基础配置加载测试。

归档标准：
- 应用可本地启动。
- `.env.example` 覆盖 LLM、Embedding、Milvus、MongoDB、MinIO、端口和 DOCX 解析配置。
- 核心 schema 可通过单元测试。

---

### 阶段 2：内容导入链路

OpenSpec 变更名：`implement-content-import-pipeline`

目标：
- 实现课程资料、项目文档、教学讲义、DOCX、题库的基础导入。
- 形成 `entry -> save_raw_file -> file_parse -> metadata_extract -> split/question_parse -> embedding-ready` 的导入流程。

建议任务：
- 实现 `POST /upload`。
- 实现导入任务创建、状态查询和失败记录。
- 实现 Markdown 解析。
- 实现 DOCX 段落、标题、列表、表格解析。
- 预留 PDF 转 Markdown 节点。
- 实现题库 CSV/JSON 基础解析。
- 实现文档切片策略：优先按标题、章节、段落，控制片段长度并保留来源。

归档标准：
- 上传文件能生成任务。
- DOCX 表格和标题不会被直接丢弃。
- 解析结果保留 `source_file_name`、`source_path`、`course_name`、`chapter_name` 等来源字段。

---

### 阶段 3：存储与索引

OpenSpec 变更名：`implement-storage-and-indexing`

目标：
- 将导入链路产物写入 MongoDB、Milvus、MinIO。
- 保证文档片段、题目、原始文件和任务状态可追溯。

建议任务：
- 实现 `utils/mongo_utils.py`。
- 实现 `utils/milvus_utils.py`。
- 实现 `utils/minio_utils.py`。
- 实现 `utils/embedding_utils.py`。
- 建立 `edu_kb_chunks`、`edu_questions`、`edu_course_names` 集合约定。
- 写入 `documents`、`chunks`、`questions`、`import_tasks` 元数据。
- 为后续增量更新预留 `content_hash`、`version`、`is_active`。

归档标准：
- 文档片段和题目可以入库。
- 可按课程、章节、文件名追溯来源。
- 单个文件失败不会影响其他任务记录。

---

### 阶段 4：检索与问答链路

OpenSpec 变更名：`implement-retrieval-query-pipeline`

目标：
- 实现课程检索、文档检索、题库检索、项目问答和知识问答。
- 输出可追溯答案。

建议任务：
- 实现 `POST /query`。
- 实现查询意图识别：课程介绍、课程详情、文档检索、题库检索、项目问答、通用问答。
- 实现问题改写。
- 实现元数据过滤条件生成。
- 实现向量检索、HyDE 检索、题库专项检索。
- 实现 RRF 融合、Rerank、动态截断。
- 实现答案生成和引用来源格式化。
- 对低置信度场景明确返回无法确认提示。

归档标准：
- 能回答课程、文档、题库、项目步骤类问题。
- 每个答案尽量返回课程、章节、文件、题目或片段来源。
- 不允许无依据编造答案。

---

### 阶段 5：会话历史与流式输出

OpenSpec 变更名：`implement-chat-history-and-streaming`

目标：
- 支持单轮问答、多轮对话、SSE 流式输出和历史记录。

建议任务：
- 实现 `chat_history` 存储。
- 实现 `session_id` 管理。
- 实现 `GET /stream/{session_id}` 或等价 SSE 输出。
- 记录用户原始问题、改写问题、召回摘要、最终答案、引用来源、时间戳。
- 支持清空或查询历史。

归档标准：
- 页面或接口可接收流式答案。
- 多轮追问可以读取同一会话上下文。
- 历史记录可按 session 查询。

---

### 阶段 6：一期最小页面与联调

OpenSpec 变更名：`implement-minimal-front-pages`

目标：
- 完成一期可演示闭环：上传资料、查看导入状态、聊天问答、查看引用。

建议任务：
- 实现 `front/import.html`。
- 实现 `front/chat.html`。
- 联调 `/upload`、`/status/{task_id}`、`/query`、SSE。
- 展示引用来源列表。
- 展示导入失败原因。

归档标准：
- 学员能通过聊天页提问并查看引用。
- 助教能上传资料并查看导入状态。
- 题库查询能返回题干、选项、答案和解析。

---

### 阶段 7：一期验收与加固

OpenSpec 变更名：`harden-mvp-acceptance-tests`

目标：
- 用需求文档中的典型场景验收一期。
- 修复稳定性、错误处理和测试覆盖。

建议任务：
- 准备课程介绍类测试问题。
- 准备课程详情类测试问题。
- 准备文档检索类测试问题。
- 准备题库解析类测试问题。
- 准备项目步骤类测试问题。
- 准备无答案/低置信度测试问题。
- 补充单元测试和集成测试。
- 记录已知限制。

归档标准：
- 一期验收问题可稳定通过。
- 导入失败、模型失败、检索无结果都有清晰提示。
- 测试覆盖核心解析、切片、检索、引用格式化。

---

### 阶段 8：二期扩展点预留

OpenSpec 变更名：`prepare-phase-two-extension-points`

目标：
- 在不扩大一期范围的前提下，为后台、增量、权限、视频、多模态预留清晰扩展点。

建议任务：
- 预留 `admin_router.py`、`admin_service.py`、`admin_schema.py`。
- 预留 `tenant_id`、`user_id`、`role`、`version`、`content_hash` 字段。
- 预留 `video_segments`、`edu_video_segments` 数据模型。
- 预留 `content_type` 支持 document、question、course、project、video、image。
- 预留增量更新接口设计文档。

归档标准：
- 后续二期不需要推翻一期数据模型。
- 权限、多租户、视频、多模态都有明确接入位置。
- 一期功能不因预留扩展点变复杂。

---

## 4. 二期到六期推荐路线

| 分期 | OpenSpec 变更组 | 主要能力 | 开始条件 |
|------|------------------|----------|----------|
| 二期 | `implement-admin-console`、`implement-incremental-update` | 后台管理、知识库管理、文档增量更新、版本管理 | 一期验收完成 |
| 三期 | `implement-auth-and-multitenancy` | 登录、角色、租户隔离、课程可见范围、审计日志 | 二期后台和元数据稳定 |
| 四期 | `implement-learning-path-and-assessment` | 知识点体系、能力测评、学习路径推荐、错题分析 | 课程、题目、历史数据积累稳定 |
| 五期 | `implement-video-segment-search` | 字幕/讲稿导入、视频片段检索、时间轴引用 | 文档检索和引用机制成熟 |
| 六期 | `implement-multimodal-search` | OCR、图片理解、关键帧抽取、图文联合检索 | 视频和对象存储链路成熟 |

---

## 5. 推荐当前第一步

当前仓库已有 OpenSpec 初始化目录，但没有活跃变更。建议第一个正式变更从基础工程开始：

```text
propose bootstrap-edu-rag-foundation
```

生成 proposal、design、tasks 后，再执行：

```text
apply bootstrap-edu-rag-foundation
```

完成并验收后：

```text
archive bootstrap-edu-rag-foundation
```

---

## 6. 风险与控制

| 风险 | 控制方式 |
|------|----------|
| 一期范围过大 | 严格按 8 个变更闭环推进，每次只实现一个 OpenSpec change |
| DOCX 解析复杂 | 一期先保证段落、标题、表格文本和占位警告，不强求复杂版式还原 |
| 检索效果不稳定 | 混合检索、HyDE、RRF、Rerank 分阶段实现，验收测试覆盖典型问题 |
| 来源追溯缺失 | 导入阶段强制保存 source、course、chapter、file、position 元数据 |
| 后期权限改造成本高 | 一期数据模型预留 tenant_id、user_id、role、is_active |
| 多模态过早拖慢一期 | 一期只预留字段和目录，五期/六期再实现视频和多模态 |

