# API Contracts

This document defines the planned API surface for the RepoLens MVP. The handlers are scaffolded in the backend, but implementation is intentionally deferred in this slice.

## Endpoints

### `POST /api/repositories/profile`

Build a compact repository profile from a public GitHub repository URL.

Request:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World"
}
```

Response:

```json
{
  "profile": {
    "repository_url": "https://github.com/octocat/Hello-World",
    "repository_name": "Hello-World",
    "owner": "octocat",
    "default_branch": "main",
    "short_summary": "Compact repository profile placeholder.",
    "architecture_notes": [
      "Architecture details will be added after repository profiling is implemented."
    ],
    "key_technologies": [
      "FastAPI",
      "React"
    ],
    "interview_focus_areas": [
      "repository architecture",
      "contributor workflows"
    ],
    "classification_tool": "github-linguist",
    "stats": {
      "file_count": 42,
      "directory_count": 8,
      "primary_languages": {
        "Python": 0.54,
        "TypeScript": 0.46
      }
    }
  }
}
```

### `POST /api/interviews/start`

Start a new interview session for a repository.

Request:

```json
{
  "repository_url": "https://github.com/octocat/Hello-World",
  "user_id": "user_123"
}
```

Response:

```json
{
  "session": {
    "session_id": "session_demo_001",
    "repository_url": "https://github.com/octocat/Hello-World",
    "user_id": "user_123",
    "status": "pending",
    "turns": [],
    "study_plan": null,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}
```

### `POST /api/interviews/{session_id}/answer`

Submit an answer for the current turn and receive evaluation data.

Request:

```json
{
  "answer": "I would inspect the repository boundaries before proposing changes."
}
```

Response:

```json
{
  "turn": {
    "turn_index": 1,
    "question": {
      "prompt": "How would you describe the repository architecture to a new teammate?",
      "focus_area": "architecture",
      "rationale": "Tests whether the user can summarize the repository structure clearly.",
      "difficulty": "medium"
    },
    "answer": "I would inspect the repository boundaries before proposing changes.",
    "evaluation": {
      "summary": "Good structure-first instinct.",
      "strengths": [
        "Starts with discovery"
      ],
      "gaps": [
        "Needs more concrete examples"
      ],
      "follow_up_required": true,
      "confidence": 0.62
    },
    "follow_up_question": "Which repository signals would you inspect first?"
  },
  "session": {
    "session_id": "session_demo_001",
    "repository_url": "https://github.com/octocat/Hello-World",
    "user_id": "user_123",
    "status": "in_progress",
    "turns": [],
    "study_plan": null,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}
```

### `GET /api/interviews/{session_id}`

Fetch the current session snapshot, including prior turns once implemented.

### `POST /api/interviews/{session_id}/study-plan`

Create a study plan from the interview transcript and evaluation history.

Request:

```json
{
  "include_score": false
}
```

Response:

```json
{
  "study_plan": {
    "summary": "Focus on architecture communication and concrete repository trade-offs.",
    "items": [
      {
        "title": "Explain module boundaries",
        "reason": "Architecture explanations were high-level but not specific.",
        "recommended_actions": [
          "Summarize each major module in two sentences",
          "Practice mapping routes to services"
        ],
        "priority": "high"
      }
    ],
    "overall_score": null
  }
}
```

## Notes

- Repository input is GitHub URL only in the MVP.
- Session ownership is designed to attach to Firebase Auth email-link identities.
- The repository profiling step must stay compact and token-aware.
- Full repository contents must not be sent to Gemini.

