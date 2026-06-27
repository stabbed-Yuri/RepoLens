import { useState } from "react";

import { AppShell } from "./components/AppShell";
import { AnalyzePage } from "./pages/AnalyzePage";
import { HomePage } from "./pages/HomePage";
import { InterviewPage } from "./pages/InterviewPage";

type View = "home" | "analyze" | "interview";

export default function App() {
  const [view, setView] = useState<View>("home");
  const [selectedRepositoryUrl, setSelectedRepositoryUrl] = useState("");

  return (
    <AppShell>
      <nav className="nav">
        <button
          type="button"
          className={view === "home" ? "active" : ""}
          onClick={() => setView("home")}
        >
          Home
        </button>
        <button
          type="button"
          className={view === "analyze" ? "active" : ""}
          onClick={() => setView("analyze")}
        >
          Analyze
        </button>
        <button
          type="button"
          className={view === "interview" ? "active" : ""}
          onClick={() => setView("interview")}
        >
          Interview
        </button>
      </nav>

      {view === "home" ? <HomePage /> : null}
      {view === "analyze" ? (
        <AnalyzePage
          initialUrl={selectedRepositoryUrl}
          onUseForInterview={(repositoryUrl) => {
            setSelectedRepositoryUrl(repositoryUrl);
            setView("interview");
          }}
        />
      ) : null}
      {view === "interview" ? (
        <InterviewPage initialRepositoryUrl={selectedRepositoryUrl} />
      ) : null}
    </AppShell>
  );
}
