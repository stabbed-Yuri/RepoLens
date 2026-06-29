# RepoLens
**Intelligent repository-specific interview practice and codebase exploration.**
<p align="center">
  <img src="./docs/Screenshot 2026-06-28 224855.png" alt="RepoLens analyzing a GitHub repository and running a technical interview" />
</p>
<p align="center">
  <img src="./docs/Screenshot 2026-06-28 224925.png" alt="RepoLens summarizing the interview" />
</p>



 [Live Deployment](https://repo-lens-flax.vercel.app/)

## About RepoLens

RepoLens is an AI-powered tool designed to help fresh graduates prepare for technical interviews based on their own projects. Instead of relying on generic, static question banks, RepoLens ingests a GitHub repository, analyzes its structure and dependencies, and conducts a dynamic, context-aware interview tailored specifically to the provided codebase.

To achieve this, RepoLens scans the repository, identifies important source files, documentation, and project metadata, and intelligently chunks the content into manageable sections. These chunks are converted into semantic embeddings, enabling efficient retrieval of the most relevant context for every interview question and evaluation. This retrieval-augmented workflow ensures that the AI focuses on the most meaningful parts of the repository rather than relying on a limited snapshot of the codebase.

This allows graduates to practice defending their technical decisions, explaining their architecture, discussing implementation details, and demonstrating a deep understanding of their own code—skills that are critical in real-world software engineering interviews.

---

## Deployment Status

### Current Status

| Component | Platform | Status |
|-----------|----------|--------|
| Frontend | Vercel | ✅ Live |
| Backend | Render | ✅ Live |

**Live Frontend:** https://repo-lens-flax.vercel.app/

### Google Cloud Deployment

RepoLens was originally architected to be deployed on **Google Cloud Run** (backend), **Firebase Hosting** (frontend), and **Firestore** for persistent storage.

Due to the limited duration of the hackathon and the requirement to enable Google Cloud billing before using Cloud Run, the planned production deployment on Google Cloud could not be completed.

> **Note:** Google Cloud requires a valid credit/debit card to activate billing, even when operating within the free tier. Since such a payment method was not available during the hackathon, billing could not be enabled, preventing deployment to Google Cloud.

As an alternative deployment strategy, the frontend has been successfully deployed on **Vercel**, while the backend is deployed on **Render**

---
## How It Works

1.  **Repository Ingestion**: The user provides a public GitHub URL.
2.  **Context Packing**: The backend clones the repository, scans it using heuristics to identify key entry points, manifests, and documentation, and builds a token-efficient `KnowledgePack`.
3.  **Intelligent Questioning**: The `KnowledgePack` and selected provider (Gemini or OpenAI) generate a targeted, medium-to-hard interview question focused on architecture, data flow, or implementation details in the repository.
4.  **Dynamic Evaluation**: The user submits their answer. The active provider evaluates the response, assigns a score, gives feedback, and proposes the next follow-up question.
5.  **Graceful Fallback**: The `ProviderRouter` falls back to the alternate LLM provider if the preferred one hits rate limits or quota errors, and uses deterministic local logic (including hash embeddings) when API providers are unavailable—keeping the demo usable even under tight free-tier limits.

---

### Technologies Used

* **Backend**: Python, FastAPI
* **Frontend**: React, Vite, TypeScript
* **AI/LLMs**: Google Gemini API (`gemini-3.1-flash-lite`), OpenAI API (`gpt-4.1-mini`)
* **Embeddings**: Gemini, OpenAI
* **Codebase Analysis**: Git, AST, Regex, Chunking
* **Deployment**: Vercel, Render

### Gemini API Integration Details

The Gemini API is deeply integrated into the core workflow:
*   **Direct REST Integration**: The backend `GeminiService` communicates directly with `generativelanguage.googleapis.com`.
*   **Context-Aware Prompts**: We construct highly specific system prompts that instruct Gemini to act as a senior engineering interviewer. We feed it the `KnowledgePack` (containing repository stats, language breakdown, and key code chunks) so it has full context of the project before asking a question.
*   **Structured JSON Output**: We utilize JSON schema constraints in the prompt to ensure Gemini returns easily parsable evaluation data (score, feedback, next action).

---


## Getting Started (Local Development)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Setup
1. Navigate to the `backend` directory.
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file inside `backend/`:

   ```env
   # Required
   GEMINI_API_KEY=your_gemini_api_key

   # Optional (only if using OpenAI)
   OPENAI_API_KEY=your_openai_api_key

   # Configuration
   REPOLENS_CORS_ORIGINS=http://localhost:5173
   REPOLENS_EMBEDDING_PROVIDER=gemini

   # Gemini Models
   REPOLENS_GEMINI_MODEL=gemini-3.1-flash-lite

   # OpenAI Models (only if using OpenAI)
   REPOLENS_OPENAI_MODEL=gpt-5-mini
   REPOLENS_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   ```
4. Run the server: `python -m uvicorn backend.app:app --reload`

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`
4. Open `http://localhost:5173` in your browser.
