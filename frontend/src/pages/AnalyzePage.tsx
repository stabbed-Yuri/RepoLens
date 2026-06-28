import { FormEvent, useState } from "react";

import { analyzeRepository, buildKnowledgePack } from "../api/client";
import type { KnowledgePack, RepositoryProfile } from "../types/contracts";

type AnalyzePageProps = {
  initialUrl?: string;
  onUseForInterview: (repositoryUrl: string) => void;
};

export function AnalyzePage({ initialUrl = "", onUseForInterview }: AnalyzePageProps) {
  const [repositoryUrl, setRepositoryUrl] = useState(initialUrl);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<RepositoryProfile | null>(null);
  const [pack, setPack] = useState<KnowledgePack | null>(null);

  async function onAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setProfile(null);
    setPack(null);

    try {
      const payload = { repository_url: repositoryUrl.trim() };
      const [nextProfile, nextPack] = await Promise.all([
        analyzeRepository(payload),
        buildKnowledgePack(payload),
      ]);
      setProfile(nextProfile);
      setPack(nextPack);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to analyze repository.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Analyze Repository</h2>
          <p className="muted">
            Paste a public GitHub URL to build a compact profile and knowledge pack.
          </p>
        </div>
      </div>

      <form className="stack" onSubmit={onAnalyze}>
        <input
          type="url"
          required
          placeholder="https://github.com/owner/repo"
          value={repositoryUrl}
          onChange={(event) => setRepositoryUrl(event.target.value)}
        />
        <div className="row">
          <button type="submit" disabled={loading}>
            {loading ? "Analyzing..." : "Analyze"}
          </button>
          <button
            type="button"
            className="ghost"
            disabled={!profile}
            onClick={() => onUseForInterview(repositoryUrl)}
          >
            Use In Interview
          </button>
        </div>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {profile ? (
        <article className="result result--spaced">
          <h2>{profile.repo_name}</h2>
          <p className="muted">
            {profile.repo_type_summary ?? "Repository summary unavailable"}
          </p>
          <p className="muted">
            Primary language: {profile.primary_language ?? "unknown"} | Frameworks:{" "}
            {profile.frameworks.join(", ") || "none detected"}
          </p>
          <p className="muted">
            Files: {profile.statistics.file_count} | Tests:{" "}
            {profile.statistics.test_file_count} | Entry points:{" "}
            {profile.statistics.entry_point_count}
          </p>
          <p className="label">Important files</p>
          <ul>
            {profile.important_files.slice(0, 8).map((filePath) => (
              <li key={filePath}>{filePath}</li>
            ))}
          </ul>
        </article>
      ) : null}

      {pack ? (
        <article className="result result--spaced">
          <h2>Knowledge Pack</h2>
          <p className="muted">
            SHA: {pack.repo_sha} | Chunks: {pack.stats.chunk_count} | Embedded:{" "}
            {pack.stats.embedded_chunk_count}
          </p>
          <p className="label">Top chunks</p>
          <ul>
            {pack.key_chunks.slice(0, 5).map((chunk) => (
              <li key={chunk.chunk_id}>{chunk.source_path}</li>
            ))}
          </ul>
        </article>
      ) : null}
    </section>
  );
}
