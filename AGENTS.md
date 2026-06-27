# AGENTS.md

## Mission

Build RepoLens as a polished hackathon MVP for repository-specific interview practice. Keep the product language-agnostic, token-efficient, and centered on dynamic question generation instead of static question banks.

## Non-Negotiables

- Never send the entire repository to Gemini.
- Always build and pass a compact `RepositoryProfile`.
- Use Python + FastAPI for backend work.
- Use React + Vite for frontend work.
- Prefer GitHub Linguist or equivalent established tooling for repository classification.
- Keep prompts in dedicated prompt files, not inline string blobs inside service code.
- Keep modules small and responsibility-focused.

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

## MVP Boundary

The target product flow is:

1. Accept a GitHub repository URL.
2. Build a compact repository profile.
3. Use Gemini to understand the project and drive interview behavior.
4. Ask one dynamic question at a time.
5. Evaluate answers and optionally ask follow-up questions.
6. Produce a study plan at the end.

This foundation slice intentionally stops before implementing live scanning, Gemini calls, or the interactive interview loop.

