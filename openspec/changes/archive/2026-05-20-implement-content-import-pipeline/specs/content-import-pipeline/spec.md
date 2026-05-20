## ADDED Requirements

### Requirement: Import task submission
The system SHALL provide an API and service entrypoint for submitting an education content import task with source file information, content type, tenant, course metadata, chapter metadata, project metadata, and optional knowledge points.

#### Scenario: Submit import task successfully
- **WHEN** a client submits a valid import request with supported content metadata
- **THEN** the system creates an import task with `pending` status, a stable task identifier, zero progress, source metadata, and creation timestamps

#### Scenario: Reject unsupported import content
- **WHEN** a client submits an import request with an unsupported file type or missing required source metadata
- **THEN** the system rejects the request with a clear validation error and does not create a runnable import task

### Requirement: Import task status tracking
The system SHALL track each import task through `pending`, `processing`, `completed`, `failed`, and `canceled` lifecycle states with progress, current stage message, error details, and update timestamps.

#### Scenario: Task completes successfully
- **WHEN** an import task finishes parsing, chunking, vectorization, and storage
- **THEN** the system marks the task as `completed`, sets progress to 100, records imported item counts, and clears fatal error details

#### Scenario: Task fails with clear error
- **WHEN** parsing, embedding, object storage, metadata storage, or vector indexing fails
- **THEN** the system marks the task as `failed`, records a user-readable error message, preserves the last completed stage, and updates the task timestamp

#### Scenario: Query task status
- **WHEN** a client queries an existing import task by task identifier
- **THEN** the system returns the task status, progress, message, error details, source metadata, and timestamps

### Requirement: Original content persistence
The system SHALL persist or register the original source asset for each import task before downstream parsing and indexing begins.

#### Scenario: Store source file before parsing
- **WHEN** an import task starts processing a file-backed source
- **THEN** the system stores the original file through the object storage adapter and records the storage path on the task or imported metadata

#### Scenario: Source storage unavailable
- **WHEN** the object storage adapter cannot store the original source
- **THEN** the system fails the task before parsing and records the storage failure reason

### Requirement: Document parsing
The system SHALL parse supported education documents into normalized text sections that preserve source file name, source path, heading hierarchy, paragraph order, table text, and parser warnings.

#### Scenario: Parse DOCX content
- **WHEN** the import pipeline receives a supported `.docx` document
- **THEN** the system extracts headings, paragraphs, numbered lists, and table text into ordered normalized sections with source location metadata

#### Scenario: Parse Markdown or plain text content
- **WHEN** the import pipeline receives supported Markdown or plain text content
- **THEN** the system converts the content into ordered normalized sections while preserving headings and source metadata

#### Scenario: Preserve parser warnings
- **WHEN** a document contains unsupported images, formulas, or complex layout elements
- **THEN** the system records parser warnings without blocking import of the remaining supported text content

### Requirement: Question bank parsing
The system SHALL parse supported structured question bank input into question records containing stem, options, answer, analysis, type, difficulty, course, chapter, knowledge points, tenant, and source metadata.

#### Scenario: Parse structured question bank
- **WHEN** the import pipeline receives supported structured question bank data
- **THEN** the system creates validated question records with answer details and traceable source metadata

#### Scenario: Reject invalid question record
- **WHEN** a question record lacks required stem, answer, type, or source metadata
- **THEN** the system reports the invalid record and fails or skips it according to the import request policy

### Requirement: Knowledge chunking
The system SHALL split parsed document sections into knowledge chunks with stable identifiers, content hashes, content type, source traceability, tenant, course, chapter, project, and knowledge point metadata.

#### Scenario: Chunk parsed document sections
- **WHEN** parsed document sections are available for import
- **THEN** the system creates non-empty knowledge chunks that respect configured chunk size and overlap limits

#### Scenario: Preserve chunk traceability
- **WHEN** the system creates a knowledge chunk
- **THEN** the chunk includes source file name, source path, tenant, course metadata, optional chapter and project metadata, knowledge points, content hash, and active state

### Requirement: Embedding and vector indexing
The system SHALL generate embeddings for imported knowledge chunks and write the vectors with corresponding metadata identifiers to the vector index.

#### Scenario: Index chunk vectors
- **WHEN** knowledge chunks are ready and the embedding adapter returns vectors for all chunk texts
- **THEN** the system writes each vector and its chunk identifier to the vector index and records successful indexing progress

#### Scenario: Embedding count mismatch
- **WHEN** the embedding adapter returns a vector count different from the number of input chunks
- **THEN** the system fails the task with a clear embedding consistency error and does not mark the task as completed

### Requirement: Metadata persistence
The system SHALL persist import tasks, knowledge chunk metadata, parser warnings, and parsed question records through the metadata storage adapter.

#### Scenario: Persist document import metadata
- **WHEN** document chunks have been created and indexed
- **THEN** the system stores chunk metadata and import task summary records that can later support retrieval, references, and administration

#### Scenario: Persist question import metadata
- **WHEN** structured question records pass validation
- **THEN** the system stores the question records with answer details, course metadata, tenant, source metadata, and import task identifier

### Requirement: Idempotent import handling
The system SHALL use source hashes and content hashes to avoid duplicate active records for the same tenant and source unless the request explicitly forces reimport or version replacement.

#### Scenario: Duplicate source without force reimport
- **WHEN** a client imports a source whose hash already exists for the same tenant and source path
- **THEN** the system does not create duplicate active chunks and reports the existing import relationship or skipped status

#### Scenario: Forced reimport
- **WHEN** a client imports an existing source with force reimport enabled
- **THEN** the system creates a new version or replaces active records according to the configured import policy while preserving traceability

### Requirement: Offline testability
The system SHALL allow import pipeline tests to run without real MongoDB, Milvus, MinIO, embedding model, or network access by using in-memory adapters.

#### Scenario: Run import unit tests offline
- **WHEN** the project test suite runs in a local environment without external services
- **THEN** import pipeline unit tests can validate task submission, parsing, chunking, status transitions, vector indexing calls, and failure handling with in-memory adapters
