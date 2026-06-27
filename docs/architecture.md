# RepoLens Architecture

## System Overview

RepoLens converts a GitHub repository URL into a compact knowledge context and a dynamic interview loop.

1. Frontend submits repository URL and renders analyze/interview chat experiences.
2. Backend clones/scans repository, builds `RepositoryProfile`, then builds `KnowledgePack`.
3. Interview service uses prompts + LLM provider (OpenAI default) to generate/evaluate each turn.
4. Retrieval layer provides token-efficient context chunks for interview prompts.

## Core Flow

```text
Frontend (React/Vite)
  -> FastAPI routes
  -> Scanner + ProfileBuilder (language-agnostic)
  -> Retrieval (chunk + embedding + top-k)
  -> KnowledgePack
  -> InterviewService (OpenAI default, fallback safe paths)
  -> Chat UI next turn rendering
```

## Backend Boundaries

- `backend/routes/*`: HTTP endpoints only
- `backend/models.py`: Pydantic request/response + domain models
- `backend/services/scanner.py`: repository clone + classification + extraction
- `backend/services/profile_builder.py`: compact profile and repo-type summary
- `backend/services/retrieval.py`: chunking/embedding/search abstractions (`openai|hash|gemini`)
- `backend/services/knowledge_pack.py`: profile + retrieval output assembly
- `backend/services/interview.py`: question/evaluation orchestration and fallback semantics
- `backend/services/openai.py`: OpenAI generation + embeddings client
- `backend/services/gemini.py`: optional Gemini embedding compatibility path
- `backend/config.py`: env-driven settings and defaults

## Frontend Boundaries

- `frontend/src/pages/AnalyzePage.tsx`: repository analyze + knowledge pack preview
- `frontend/src/pages/InterviewPage.tsx`: chat-style interview thread + retry UX
- `frontend/src/api/client.ts`: typed API wrappers
- `frontend/src/types/contracts.ts`: frontend contract shapes

## Reliability Semantics

- Interview answer responses standardize `next_action`:
  - `continue_interview`
  - `study_plan_ready`
  - `retry_later`
- Repeated follow-up prompts are deduped server-side.
- Provider failures return explicit fallback evaluations instead of placeholder stubs.

## Deployment Shape (Target)

- Frontend: Firebase Hosting
- Backend: Cloud Run
- Firestore: session/report/cache persistence (later slice)
- Secret Manager: API keys
- Artifact Registry + Cloud Build: build/deploy pipeline
