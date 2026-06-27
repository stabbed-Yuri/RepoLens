# RepoLens Architecture

## System Overview

RepoLens is designed as a small, modular system that converts a GitHub repository URL into a personalized interview workflow.

1. The frontend collects a repository URL and manages lightweight authenticated session state.
2. The backend fetches repository metadata, extracts a compact repository profile, and stores interview progress in Firestore.
3. Gemini consumes the compact repository profile, not the full repository, to produce:
   - repository understanding
   - dynamic interview questions
   - answer evaluations
   - follow-up questions
   - study plans

## Core Flow

```text
Frontend
  -> FastAPI API
  -> GitHub fetch + repository profiler
  -> RepositoryProfile
  -> Gemini orchestration
  -> Interview session persistence in Firestore
  -> Frontend renders each turn
```

## Backend Boundaries

- `api/`
  - HTTP routes and request/response handling only
- `models/`
  - Pydantic models for API contracts and typed domain data
- `services/github_client.py`
  - Repository metadata access and archive/content fetch planning
- `services/repository_profiler.py`
  - Compact, language-agnostic profiling and classification boundary
- `services/gemini_service.py`
  - Prompt selection, Gemini calls, and response parsing
- `services/session_store.py`
  - Firestore persistence for sessions, turns, reports, and caches
- `services/auth_service.py`
  - Session ownership coordination around Firebase Auth identities
- `core/settings.py`
  - Environment-driven configuration

## Frontend Boundaries

- `pages/`
  - Screen-level composition
- `components/`
  - Shared presentational shells
- `api/`
  - Backend client wrappers and request typing
- `types/`
  - Shared frontend contract shapes
- `state/`
  - Auth and session state placeholders

## Data Objects

- `RepositoryProfile`
  - compact repository summary
  - stack and architecture signals
  - interview focus areas
  - repository stats and classification hints
- `InterviewSession`
  - session metadata, turns, ownership, status
- `InterviewTurn`
  - generated question, submitted answer, evaluation, follow-up
- `StudyPlan`
  - prioritized learning actions derived from the interview

## Deployment Shape

- Frontend hosted on Firebase Hosting
- Backend container deployed to Cloud Run
- Firestore used for session/report storage and cacheable artifacts
- Secret Manager used for Gemini and Firebase-related secrets
- Artifact Registry stores backend container images
- Cloud Build builds and pushes deployable artifacts

