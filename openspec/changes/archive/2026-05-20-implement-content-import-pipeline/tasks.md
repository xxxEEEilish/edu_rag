## 1. Schemas and Contracts

- [x] 1.1 Extend import request, task detail, task summary, parser warning, parsed document, parsed section, and import result schemas.
- [x] 1.2 Add question bank import schemas or extend existing question schemas for structured import validation.
- [x] 1.3 Define adapter contracts for task metadata storage, source object storage, embedding generation, and vector index writes.
- [x] 1.4 Add in-memory adapter implementations for unit tests and local offline execution.

## 2. Parsing and Chunking

- [x] 2.1 Implement parser registry that selects parser by declared content type or file extension.
- [x] 2.2 Implement Markdown and plain text parser preserving heading and source metadata.
- [x] 2.3 Implement DOCX parser preserving heading hierarchy, paragraph order, list text, table text, and unsupported-content warnings.
- [x] 2.4 Implement structured question bank parser with validation for stem, type, answer, options, analysis, difficulty, and metadata.
- [x] 2.5 Implement document chunker with configured chunk size, overlap, stable chunk identifiers, content hashes, and source traceability.

## 3. Import Service

- [x] 3.1 Implement import task creation with validation, tenant defaults, metadata normalization, and initial `pending` status.
- [x] 3.2 Implement source persistence step that stores or registers original files before parsing.
- [x] 3.3 Implement pipeline execution from `processing` through parsing, chunking, embedding, vector indexing, and metadata persistence.
- [x] 3.4 Implement idempotency checks using source hash, content hash, tenant, source path, and force reimport policy.
- [x] 3.5 Implement failure handling that records stage, progress, user-readable error, and updated timestamp.
- [x] 3.6 Implement task status retrieval and not-found handling.

## 4. API Integration

- [x] 4.1 Add FastAPI import router with task submission endpoint.
- [x] 4.2 Add task status query endpoint.
- [x] 4.3 Wire import router into application startup without requiring live external services.
- [x] 4.4 Document import endpoints and supported formats in README or project docs.

## 5. Tests

- [x] 5.1 Add schema tests for import requests, task status responses, parser warnings, parsed sections, and import results.
- [x] 5.2 Add parser tests for Markdown/plain text, DOCX, and structured question bank inputs.
- [x] 5.3 Add chunker tests for chunk size, overlap, hashes, identifiers, and metadata propagation.
- [x] 5.4 Add import service tests for successful document import using in-memory adapters.
- [x] 5.5 Add import service tests for embedding mismatch, parser failure, storage failure, duplicate import, and forced reimport.
- [x] 5.6 Add API tests for task submission, validation failure, and status query.
- [x] 5.7 Run the full test suite and fix regressions.
