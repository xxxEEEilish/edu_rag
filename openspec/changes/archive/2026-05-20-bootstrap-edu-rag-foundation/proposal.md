## Why

教育知识库项目需要先具备可启动、可配置、可扩展的后端工程基础，后续导入、索引、检索问答和页面联调才能按 OpenSpec 分阶段推进。当前仓库只有需求、方案和 OpenSpec 工作流文档，缺少 FastAPI 应用骨架、基础配置、核心数据模型和外部服务适配层。

## What Changes

- 创建教育 RAG 后端的基础目录结构，包括 API、核心配置、Schema、Service、Processor、Utils、Front 和 Tests。
- 引入 FastAPI 应用入口与健康检查接口，保证项目可以本地启动并验证运行状态。
- 增加 `.env.example` 和配置加载模块，覆盖 LLM、Embedding、Reranker、Milvus、MongoDB、MinIO、端口和 DOCX 解析配置。
- 定义内容类型、任务状态、查询意图、来源类型等基础枚举。
- 定义一期后续链路需要复用的 Pydantic Schema，包括知识片段、题目、导入任务、查询请求和查询响应。
- 增加 LLM、Embedding、Reranker、MongoDB、Milvus、MinIO 的接口占位或适配层，为后续变更接入真实能力预留稳定边界。
- 增加基础配置和核心 Schema 的单元测试。

## Capabilities

### New Capabilities

- `edu-rag-foundation`: 教育 RAG 项目的基础工程骨架、配置加载、健康检查、核心枚举、核心 Schema 和外部依赖适配边界。

### Modified Capabilities

- 无。

## Impact

- 影响代码结构：新增 `api/`、`core/`、`schema/`、`services/`、`processor/`、`utils/`、`front/`、`tests/` 等目录。
- 影响运行方式：新增 FastAPI 应用入口、依赖文件和环境变量样例，项目可通过本地 Python 环境启动。
- 影响后续变更：导入链路、存储索引、检索问答、会话流式输出和前端页面将依赖本变更提供的配置、Schema 和适配层。
- 外部系统不在本阶段真实联通；MongoDB、Milvus、MinIO、LLM、Embedding 和 Reranker 仅建立配置与接口边界。
