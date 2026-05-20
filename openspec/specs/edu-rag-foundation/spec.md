## Purpose

Define the baseline FastAPI project structure, shared schemas, configuration, health check, adapter boundaries, and offline test expectations for the education RAG backend.

## Requirements

### Requirement: Project skeleton

The system SHALL provide a Python FastAPI project skeleton for the education RAG backend with stable directories for API routers, core configuration, schemas, services, processors, utilities, frontend assets, and tests.

#### Scenario: Required directories exist

- **WHEN** the foundation change is implemented
- **THEN** the repository contains `api/`, `core/`, `schema/`, `services/`, `processor/`, `utils/`, `front/`, and `tests/`

#### Scenario: Application can start locally

- **WHEN** a developer runs the documented FastAPI entrypoint in a configured Python environment
- **THEN** the application starts without requiring live MongoDB, Milvus, MinIO, LLM, Embedding, or Reranker services

### Requirement: Health check

The system SHALL expose a health check endpoint that confirms the FastAPI application is running.

#### Scenario: Health endpoint returns running status

- **WHEN** a client requests the health check endpoint
- **THEN** the system returns a successful response containing an application status value

### Requirement: Environment configuration

The system SHALL provide `.env.example` and a configuration loader that covers application ports, default tenant, LLM, vision model, embedding, reranker, Milvus, MongoDB, MinIO, and DOCX parser settings.

#### Scenario: Example environment documents required settings

- **WHEN** a developer opens `.env.example`
- **THEN** it contains placeholders or defaults for LLM, Embedding, Reranker, Milvus, MongoDB, MinIO, application ports, default tenant, and DOCX parsing behavior

#### Scenario: Configuration loads with defaults

- **WHEN** the application imports the settings module without a local `.env`
- **THEN** required settings load with safe development defaults or empty secret placeholders

### Requirement: Core enums

The system SHALL define shared enums for content type, import task status, query intent, and source type.

#### Scenario: Import task status supports lifecycle tracking

- **WHEN** later import code creates or updates an import task
- **THEN** it can use shared task statuses for pending, processing, completed, failed, and canceled states

#### Scenario: Query intent supports education RAG routes

- **WHEN** later query code classifies a user request
- **THEN** it can use shared query intents for course introduction, course detail, document search, question search, project QA, video search, and general QA

### Requirement: Core schemas

The system SHALL define Pydantic schemas for `KnowledgeChunk`, `Question`, `ImportTask`, `QueryRequest`, `QueryResponse`, and reference source objects.

#### Scenario: Knowledge chunk preserves traceability

- **WHEN** code constructs a knowledge chunk
- **THEN** the schema supports content, content type, course, chapter, project, knowledge points, source file name, source path, tenant, version, content hash, active state, and timestamps

#### Scenario: Question preserves answer details

- **WHEN** code constructs a question object
- **THEN** the schema supports question id, code, bank name, type, stem, options, answer, analysis, difficulty, course, chapter, knowledge points, and tenant

#### Scenario: Query response includes references

- **WHEN** code constructs a query response
- **THEN** the schema supports answer text, session id, intent, references, and message metadata

### Requirement: External service adapters

The system SHALL provide utility modules that define adapter boundaries for LLM, Embedding, Reranker, MongoDB, Milvus, and MinIO integrations without requiring live external services during application startup, and those adapter boundaries SHALL expose the operations needed by the content import pipeline.

#### Scenario: Adapter modules can be imported offline

- **WHEN** a developer imports utility modules for external services in a local environment
- **THEN** the imports succeed without attempting network connections or requiring credentials

#### Scenario: Unimplemented external operations fail clearly

- **WHEN** code calls an external operation that is only a placeholder in this foundation phase
- **THEN** the system raises a clear not-implemented or configuration error instead of failing silently

#### Scenario: Import pipeline can depend on adapter contracts

- **WHEN** import service code needs to store task metadata, persist original files, generate embeddings, or write vector records
- **THEN** it can call explicit MongoDB, MinIO, Embedding, and Milvus adapter methods without importing concrete vendor clients in the service layer

#### Scenario: Import adapters support offline replacements

- **WHEN** import pipeline tests run without configured external services
- **THEN** the same adapter contracts can be satisfied by in-memory replacements without changing API or service code

### Requirement: Foundation tests

The system SHALL include unit tests for configuration loading, health check behavior, and core schema construction.

#### Scenario: Foundation tests pass locally

- **WHEN** a developer runs the project test command
- **THEN** tests for configuration loading, health check behavior, and core schema construction pass without requiring external services
