import { apiBaseUrl } from "../api/client";
import { initialAuthState } from "../state/auth";

export function HomePage() {
  return (
    <>
      <section className="hero">
        <h1>RepoLens</h1>
        <p>
          Foundation scaffold for an AI interview coach that understands GitHub
          repositories through compact profiles, then runs a personalized
          interview loop powered by Gemini.
        </p>
      </section>

      <section className="card-grid">
        <article className="card">
          <h2>Current Slice</h2>
          <p>
            The repository structure, typed contracts, prompts inventory, and
            deployment docs are in place. Live repository scanning and interview
            orchestration are the next steps.
          </p>
        </article>

        <article className="card">
          <h2>Planned API</h2>
          <ul>
            <li>{apiBaseUrl}/repositories/profile</li>
            <li>{apiBaseUrl}/interviews/start</li>
            <li>{apiBaseUrl}/interviews/{`{session_id}`}/answer</li>
            <li>{apiBaseUrl}/interviews/{`{session_id}`}</li>
            <li>{apiBaseUrl}/interviews/{`{session_id}`}/study-plan</li>
          </ul>
        </article>

        <article className="card">
          <h2>Auth Direction</h2>
          <p>
            Planned frontend auth model: {initialAuthState.mode}. The production
            interview flow will attach session ownership to Firebase Auth
            email-link identities.
          </p>
        </article>
      </section>
    </>
  );
}

