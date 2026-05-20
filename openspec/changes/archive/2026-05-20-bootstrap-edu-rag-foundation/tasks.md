## 1. Project Skeleton

- [x] 1.1 Create the Python project directories: `api/`, `core/`, `schema/`, `services/`, `processor/`, `utils/`, `front/`, and `tests/`
- [x] 1.2 Add Python package markers and lightweight placeholders where needed so imports are stable
- [x] 1.3 Add dependency and run documentation files for the foundation application

## 2. FastAPI Application

- [x] 2.1 Implement the FastAPI application entrypoint
- [x] 2.2 Add a health check endpoint that returns application status
- [x] 2.3 Ensure application startup does not require live MongoDB, Milvus, MinIO, LLM, Embedding, or Reranker services

## 3. Configuration

- [x] 3.1 Add `.env.example` with application, LLM, vision model, embedding, reranker, Milvus, MongoDB, MinIO, and DOCX parser settings
- [x] 3.2 Implement `core/config.py` with a reusable settings object and safe development defaults
- [x] 3.3 Implement `core/paths.py` for repository and runtime path helpers

## 4. Core Contracts

- [x] 4.1 Implement `core/enums.py` with content type, import task status, query intent, and source type enums
- [x] 4.2 Implement knowledge chunk and reference source schemas
- [x] 4.3 Implement question schemas
- [x] 4.4 Implement import task schemas
- [x] 4.5 Implement query request and query response schemas

## 5. External Adapter Boundaries

- [x] 5.1 Add LLM utility adapter placeholders with clear unsupported-operation errors
- [x] 5.2 Add embedding and reranker utility adapter placeholders with clear unsupported-operation errors
- [x] 5.3 Add MongoDB, Milvus, and MinIO utility adapter placeholders that can be imported offline

## 6. Validation

- [x] 6.1 Add tests for configuration loading
- [x] 6.2 Add tests for the health check endpoint
- [x] 6.3 Add tests for core schema construction and traceability fields
- [x] 6.4 Run the project test command and confirm foundation tests pass
