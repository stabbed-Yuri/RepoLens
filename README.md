# RepoLens

RepoLens is an AI-powered interview coach for GitHub repositories. A user submits a repository URL, RepoLens builds a compact `RepositoryProfile` + `KnowledgePack`, then runs dynamic interview Q&A one turn at a time.

Current intelligence defaults:
- Interview generation/evaluation: OpenAI (`gpt-4.1-mini`)
- Embeddings/retrieval: OpenAI (`text-embedding-3-small`) with deterministic hash fallback

## Runtime API

- `GET /health`
- `POST /analyze`
- `POST /analyze/knowledge-pack`
- `POST /interview/start`
- `POST /interview/answer`
- `POST /interview/stop`

These routes are active in [backend/app.py](/C:/Users/GIGABYTE/Documents/RepoLens/backend/app.py) and consumed by the React frontend.

## Current Capabilities

- Language-agnostic repository scan + profile construction
- Knowledge-pack builder with chunking, embeddings, and topic hits
- Chat-style dynamic interview flow with standardized `next_action` semantics:
  - `continue_interview`
  - `study_plan_ready`
  - `retry_later`
- Rate-limit/provider-failure fallback messaging for demo reliability

## Local Run

Backend:
```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Environment

Use `backend/.env`:

```env
OPENAI_API_KEY=...
REPOLENS_OPENAI_MODEL=gpt-4.1-mini
REPOLENS_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
REPOLENS_EMBEDDING_PROVIDER=openai
```

Optional embedding providers:
- `REPOLENS_EMBEDDING_PROVIDER=hash`
- `REPOLENS_EMBEDDING_PROVIDER=gemini` (requires Gemini key/model config)

## Deployed URLs

Set these once you deploy:

- Frontend (Vercel): `https://<your-frontend>.vercel.app`
- Backend (Render): `https://<your-backend>.onrender.com`
- Health check: `https://<your-backend>.onrender.com/health`

Deployment wiring:

- In Vercel env vars: `VITE_API_BASE_URL=https://<your-backend>.onrender.com`
- In Render env vars: `REPOLENS_CORS_ORIGINS=https://<your-frontend>.vercel.app,http://localhost:5173`

## Testing

Backend:
```bash
python -m unittest discover backend/tests
```

Frontend:
```bash
cd frontend
npm run test
```

## Notes

- Prompt assets are maintained in [backend/prompts/](/C:/Users/GIGABYTE/Documents/RepoLens/backend/prompts/) and [docs/prompts.md](/C:/Users/GIGABYTE/Documents/RepoLens/docs/prompts.md).
- The legacy scaffold under `backend/app/*` is non-runtime reference structure for now.
