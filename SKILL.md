# RepoLens Build Skill

## Purpose

Use this repository as the source of truth for building a compact, modular AI interview coach for GitHub repositories.

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

## Future Implementation Priorities

1. Repository fetch and compact profile generation
2. Gemini-backed repository understanding
3. Interview session orchestration
4. Firestore-backed session persistence
5. Frontend interview experience and report rendering

## Guardrails

- Do not couple Gemini logic directly to route handlers.
- Do not add custom language detection when established tooling can be integrated.
- Do not expand prompt files into oversized static banks.
- Do not widen scope into enterprise features before the core interview loop works well.

