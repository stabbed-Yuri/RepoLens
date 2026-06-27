# AGENTS.md

## Mission

Build RepoLens as a polished hackathon MVP for repository-specific interview practice. Keep the product language-agnostic, token-efficient, and centered on dynamic question generation instead of static question banks.

## Award Track Alignment

Prioritize decisions that improve judging outcomes:
- **Best Use of Gemini API**: preserve and document Gemini capability paths even when another provider is default.
- **Best App Deployed on Google Cloud**: emphasize cloud architecture quality (Cloud Run + Firebase Hosting + Firestore + Secret Manager + Cloud Build + Artifact Registry), not just ad-hoc deploy.
- **Best Usage of Codex**: keep this file and `SKILL.md` accurate, implementation-specific, and actively used.

## Non-Negotiables

- Never send the entire repository to Gemini.
- Always build and pass a compact `RepositoryProfile`.
- Use Python + FastAPI for backend work.
- Use React + Vite for frontend work.
- Prefer GitHub Linguist or equivalent established tooling for repository classification.
- Keep prompts in dedicated prompt files, not inline string blobs inside service code.
- Keep modules small and responsibility-focused.
- Never put API keys in code or frontend bundles; use Secret Manager.
- Keep runtime deployment artifacts (`Dockerfile`, `cloudbuild*.yaml`, `firebase.json`) aligned with docs.

## Engineering Style

- Use type hints everywhere practical.
- Use Pydantic models for API contracts and core typed data.
- Separate services by concern:
  - GitHub access
  - Repository profiling
  - Gemini orchestration
  - Session persistence
  - Auth/session coordination
- Add tests for critical paths before broadening the implementation surface.
- Do not refactor unrelated files when delivering a scoped task.
- For deployment work, prefer reproducible pipelines over one-off manual shell steps.

## MVP Boundary

The target product flow is:

1. Accept a GitHub repository URL.
2. Build a compact repository profile.
3. Use Gemini to understand the project and drive interview behavior.
4. Ask one dynamic question at a time.
5. Evaluate answers and optionally ask follow-up questions.
6. Produce a study plan at the end.

## Deployment Expectations

- Backend deploy target: Cloud Run from Artifact Registry images via Cloud Build.
- Frontend deploy target: Firebase Hosting with SPA rewrites.
- Secrets: Secret Manager with IAM-based runtime access.
- Persistence target: Firestore collections for sessions/reports/cache.

Keep these as the canonical architecture even if local development shortcuts exist.
