# 发现记录

## 文档结论

- 项目定位是面向教育培训行业的智能教育知识库与学习辅助系统。
- 一期必须优先形成最小可用闭环：内容导入、课程查询、文档检索、题库检索、RAG 问答、流式输出、历史记录和来源追溯。
- DOCX 是一期正式支持格式，不能只支持 PDF/Markdown。
- 技术方案建议使用 FastAPI、LangGraph、Milvus、MongoDB、MinIO、BGE-M3、BGE-Reranker、Qwen 系列模型。
- 后续能力包括后台管理、增量更新、权限多租户、学习路径、能力测评、视频检索、多模态检索。

## OpenSpec 结论

- 仓库已有 `openspec/` 目录和 `.github/prompts/opsx-*.prompt.md`。
- 当前没有活跃 OpenSpec change。
- `/opsx:*` 是聊天快捷命令风格，不是 PowerShell 终端命令；在本项目中可用 `propose/apply/archive` 对话指令代替。

