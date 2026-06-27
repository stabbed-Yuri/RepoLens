# RepoLens Build Skill

## Purpose

Use this repository as the source of truth for building a compact, modular AI interview coach for GitHub repositories.

## Competition Focus

When trade-offs appear, prioritize:
1. Demo reliability
2. Cloud architecture quality
3. Clear Codex process artifacts (`AGENTS.md`, `SKILL.md`)

## Working Rules

- Start from the product goal: personalized interview Q and A for a pasted GitHub repository URL.
- Preserve the modular split between API contracts, services, prompts, and UI state.
- Prefer small vertical additions that keep the scaffold coherent.
- Treat `docs/prompts.md` as the current prompt inventory until dedicated runtime prompt loaders are added.
- Keep Google Cloud deployment assumptions aligned with:
  - Cloud Run
  - Firebase Hosting
  - Firestore
  - Secret Manager
  - Artifact Registry
  - Cloud Build
- Keep deployment assets reproducible and committed (`backend/Dockerfile`, `cloudbuild.backend.yaml`, `cloudbuild.frontend.yaml`, `firebase.json`).

## Future Implementation Priorities

1. Firestore-backed session/report persistence
2. Provider-mode polish (OpenAI default + Gemini documented capability path)
3. Cloud deployment hardening (IAM, monitoring, scaling controls)
4. Demo narrative + presentation support

## Guardrails

- Do not couple Gemini logic directly to route handlers.
- Do not add custom language detection when established tooling can be integrated.
- Do not expand prompt files into oversized static banks.
- Do not widen scope into enterprise features before the core interview loop works well.
- Do not ship cloud deployments with unmanaged secrets or undocumented runtime config.
