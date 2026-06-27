export function HomePage() {
  return (
    <>
      <section className="hero">
        <h1>RepoLens</h1>
        <p>
          AI-powered repository interview coach. Analyze a GitHub repo, build a
          compact knowledge pack, then run a dynamic Gemini-driven interview.
        </p>
      </section>

      <section className="card-grid">
        <article className="card">
          <h2>Analyze</h2>
          <p>
            Use the Analyze page to fetch a repository profile and knowledge pack.
          </p>
        </article>

        <article className="card">
          <h2>Interview</h2>
          <p>
            Use the Interview page to start a question session and submit answers
            for evaluation and follow-ups.
          </p>
        </article>

        <article className="card">
          <h2>Backend Endpoints</h2>
          <ul>
            <li>POST /analyze</li>
            <li>POST /analyze/knowledge-pack</li>
            <li>POST /interview/start</li>
            <li>POST /interview/answer</li>
          </ul>
        </article>
      </section>
    </>
  );
}
