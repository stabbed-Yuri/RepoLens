# RepoLens

**Intelligent repository-specific interview practice and codebase exploration.**

🚀 [Live Deployment](#) *(Deployment pending)*

## About RepoLens

RepoLens is an AI-powered tool designed to help fresh graduates prepare for technical interviews based on their own projects. Instead of relying on generic, static question banks, RepoLens ingests a GitHub repository, analyzes its structure and dependencies, and conducts a dynamic, context-aware interview tailored specifically to the codebase provided. 

This allows graduates to practice defending their technical decisions, explaining their architecture, and demonstrating deep understanding of their own code—skills that are critical in real-world engineering interviews.

---

## Hackathon Categories Addressed

RepoLens was built for the **Hack Days CUET** hackathon and is competing in the following tracks:

*   **Best Use of Gemini API**: RepoLens leverages the Gemini API as its core engine for generating intelligent, repository-specific questions, evaluating candidate answers in real-time, and generating dynamic follow-up questions based on the candidate's responses.
*   **Best usage of Codex**: The entire development lifecycle of RepoLens was guided by strictly enforced AI agent rules (`AGENTS.md`) and capability files (`SKILL.md`), ensuring high-quality architectural decisions, token-efficient context packing, and robust error handling.

*(Note regarding the **Best App Deployed on Google Cloud** track: While a full deployment utilizing Google Cloud Run, Firebase Hosting, and Firestore was planned and architected, it could not be fully deployed to production during the hackathon due to inaccessible payment method restrictions for Google Cloud billing.)*

---

## How It Works

1.  **Repository Ingestion**: The user provides a public GitHub URL.
2.  **Context Packing**: The backend clones the repository, scans it using heuristics to identify key entry points, manifests, and documentation, and builds a token-efficient `KnowledgePack`.
3.  **Intelligent Questioning**: The `KnowledgePack` is passed to the **Gemini 3.1 Flash Lite** model, which formulates a targeted, medium-to-hard difficulty interview question focusing on the architecture, data flow, or specific implementation details of the repository.
4.  **Dynamic Evaluation**: The user submits their answer. Gemini evaluates the response, assigns a score, provides constructive feedback, and determines the next logical follow-up question.
5.  **Graceful Fallback**: The system features a robust `ProviderRouter` that automatically falls back to secondary models or offline deterministic logic if rate limits or quota issues are encountered, ensuring a seamless user experience.

---

## Technical Architecture

### Technologies Used

*   **Backend**: Python, FastAPI
*   **Frontend**: React, Vite, TypeScript
*   **AI/LLMs**: Google Gemini API (`gemini-3.1-flash-lite`) via direct REST integration.
*   **Codebase Parsing**: Custom Python AST/Regex heuristics combined with Git for shallow cloning and chunking.

### Gemini API Integration Details

The Gemini API is deeply integrated into the core workflow:
*   **Direct REST Integration**: The backend `GeminiService` communicates directly with `generativelanguage.googleapis.com`.
*   **Context-Aware Prompts**: We construct highly specific system prompts that instruct Gemini to act as a senior engineering interviewer. We feed it the `KnowledgePack` (containing repository stats, language breakdown, and key code chunks) so it has full context of the project before asking a question.
*   **Structured JSON Output**: We utilize JSON schema constraints in the prompt to ensure Gemini returns easily parsable evaluation data (score, feedback, next action).

---

## Team

*   **Aadil Mubasshar** - Full Stack Developer & AI Engineer

---

## Getting Started (Local Development)

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Setup
1. Navigate to the `backend` directory.
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `backend/.env`:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   REPOLENS_GEMINI_MODEL=gemini-3.1-flash-lite
   REPOLENS_EMBEDDING_PROVIDER=gemini
   ```
4. Run the server: `python -m uvicorn backend.app:app --reload`

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies: `npm install`
3. Run the development server: `npm run dev`
4. Open `http://localhost:5173` in your browser.
