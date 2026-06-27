# RepoLens

RepoLens is an AI-powered interview coach for GitHub repositories. A user submits a GitHub repository URL, RepoLens builds a compact `RepositoryProfile`, uses Gemini to understand the project, then runs a personalized interview one question at a time with follow-up questions, answer evaluation, and a study plan.

This repository currently contains the foundation slice only. The codebase defines the project structure, typed contracts, placeholder backend and frontend modules, prompt inventory, and Google Cloud setup docs that the next implementation pass will build on.

## Product Constraints

- Backend: Python + FastAPI
- Frontend: React + Vite
- Repository analysis: language-agnostic, with GitHub Linguist or equivalent established classification tooling
- LLM: Gemini for repository understanding, question generation, answer evaluation, follow-up generation, and study plan generation
- Deployment target:
  - Cloud Run for the backend
  - Firebase Hosting for the frontend
  - Firestore for session and report storage
  - Secret Manager for API keys
  - Artifact Registry and Cloud Build for image build and deploy workflows
- Prompt assets must live outside inline code paths, under `backend/prompts/` or `docs/prompts.md`

## Repository Layout

```text
backend/
  app/
    api/
    core/
    models/
    prompts/
    services/
  tests/
frontend/
  src/
docs/
AGENTS.md
SKILL.md
README.md
```

## Planned API Surface

- `POST /api/repositories/profile`
- `POST /api/interviews/start`
- `POST /api/interviews/{session_id}/answer`
- `GET /api/interviews/{session_id}`
- `POST /api/interviews/{session_id}/study-plan`

The route handlers currently return `501 Not Implemented` while the schema contracts and service boundaries are established.

## Current Deliverables

- Backend package skeleton with typed Pydantic models
- Placeholder FastAPI routers and service interfaces
- Frontend React + Vite scaffold with typed client-side contracts
- Prompt inventory in [docs/prompts.md](/C:/Users/GIGABYTE/Documents/RepoLens/docs/prompts.md)
- Architecture and deployment docs in [docs/architecture.md](/C:/Users/GIGABYTE/Documents/RepoLens/docs/architecture.md), [docs/api-contracts.md](/C:/Users/GIGABYTE/Documents/RepoLens/docs/api-contracts.md), and [docs/gcp-setup.md](/C:/Users/GIGABYTE/Documents/RepoLens/docs/gcp-setup.md)
- Critical-path backend tests for settings, schema round-trips, and prompt coverage

## Local Verification

Backend tests can be run with:

```bash
python -m unittest discover backend/tests
```

The frontend is scaffolded for Vite but dependencies are not installed in this slice.

## Next Implementation Slice

1. Implement GitHub repository fetch and compact profiling.
2. Integrate GitHub Linguist or equivalent repository classification tooling.
3. Add Gemini-backed repository understanding.
4. Implement interview session orchestration and Firestore persistence.
5. Connect the frontend to live backend endpoints and Firebase Auth email-link flows.

