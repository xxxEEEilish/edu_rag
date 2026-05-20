# edu_rag

Foundation for an education-focused RAG service.

## Setup

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

## Run

```powershell
uvicorn main:app --reload --port 8000
```

Health check:

```text
GET /health
```

## Import Content

Submit a JSON import task. The first implementation runs synchronously with offline
in-memory adapters, so local development does not require MongoDB, Milvus, MinIO,
or an embedding service.

```text
POST /imports
GET /imports/{task_id}
```

Supported `input_format` values:

- `text`
- `markdown`
- `docx`
- `question_json`

Example request:

```json
{
  "file_name": "lesson.md",
  "input_format": "markdown",
  "content_type": "document",
  "source_text": "# Python\n\nFunctions use def.",
  "metadata": {
    "tenant_id": "default",
    "course_name": "Python Intro",
    "chapter_name": "Functions",
    "knowledge_points": ["function"]
  }
}
```

## Test

```powershell
pytest
```
