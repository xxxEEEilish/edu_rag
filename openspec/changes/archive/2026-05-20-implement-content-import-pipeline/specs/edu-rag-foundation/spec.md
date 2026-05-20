## MODIFIED Requirements

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
