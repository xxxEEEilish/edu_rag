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

## Test

```powershell
pytest
```

