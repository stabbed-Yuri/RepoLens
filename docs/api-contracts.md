# API Contracts

This document defines the active runtime API for the current RepoLens MVP slice.

## Endpoints

### `GET /health`

Response:

```json
{
  "status": "ok",
  "timestamp": "2026-06-28T12:00:00Z"
}
```

### `POST /analyze`

Build a compact repository profile from a public GitHub URL.

Request:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World"
}
```

Response (trimmed):

```json
{
  "repo_name": "Hello-World",
  "repo_url": "https://github.com/octocat/Hello-World",
  "primary_language": "TypeScript",
  "frameworks": ["react"],
  "repo_type_summary": "TypeScript repository with react",
  "important_files": ["README.md", "src/main.tsx"],
  "statistics": {
    "file_count": 42,
    "directory_count": 8,
    "entry_point_count": 1
  }
}
```

### `POST /analyze/knowledge-pack`

Build repository knowledge context for interview prompting.

Request:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World"
}
```

Response (trimmed):

```json
{
  "repo_name": "Hello-World",
  "repo_sha": "abc123...",
  "profile": { "repo_name": "Hello-World" },
  "key_chunks": [
    {
      "chunk_id": "Hello-World:deadbeef",
      "source_path": "src/main.tsx",
      "chunk_type": "source",
      "start_line": 1,
      "end_line": 20,
      "text_excerpt": "..."
    }
  ],
  "stats": {
    "chunk_count": 20,
    "embedded_chunk_count": 20,
    "embedding_dimensions": 1536
  }
}
```

### `POST /interview/start`

Start an interview session for a repository.

Request:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World",
  "user_id": null
}
```

Response:

```json
{
  "session_id": "session_123abc",
  "status": "in_progress",
  "question": {
    "prompt": "What is the role of `src/main.tsx` in this repository?",
    "focus_area": "repository overview",
    "difficulty": "medium"
  }
}
```

### `POST /interview/answer`

Submit an answer and receive evaluation + next step.

Request:

```json
{
  "session_id": "session_123abc",
  "answer": "It boots the app and wires root providers."
}
```

Response:

```json
{
  "session_id": "session_123abc",
  "evaluation": "Good summary. Mention one trade-off in startup ordering.",
  "follow_up_question": "Which startup dependency is most brittle and why?",
  "next_action": "continue_interview"
}
```

`next_action` values:
- `continue_interview`
- `study_plan_ready`
- `retry_later`

## Notes

- Repository input is GitHub URL only.
- Scanner/profile must remain language-agnostic and compact.
- Full repository contents are not sent to model providers.
- Interview provider defaults to OpenAI; embeddings default to OpenAI with hash fallback.
