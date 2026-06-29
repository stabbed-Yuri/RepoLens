import { FormEvent, useState } from "react";
import { ArrowRight, BookOpen, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ModelProvider } from "@/types";

const DEMO_REPOS = [
  {
    label: "React web app",
    url: "https://github.com/gothinkster/react-redux-realworld-example-app",
  },
  {
    label: "Python framework",
    url: "https://github.com/pallets/flask",
  },
  {
    label: "Low-signal repo",
    url: "https://github.com/octocat/Hello-World",
  },
];

interface HeroSectionProps {
  onAnalyze: (url: string) => void;
  isLoading: boolean;
  modelProvider: ModelProvider;
  onModelProviderChange: (provider: ModelProvider) => void;
}

export function HeroSection({
  onAnalyze,
  isLoading,
  modelProvider,
  onModelProviderChange,
}: HeroSectionProps) {
  const [url, setUrl] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      return;
    }
    onAnalyze(trimmed);
  }

  return (
    <main className="min-h-svh bg-background text-foreground">
      <section className="mx-auto flex max-w-5xl flex-col gap-10 px-4 py-20 sm:px-6">
        <div className="inline-flex w-fit items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground">
          <BookOpen className="size-3.5" />
          RepoLens
        </div>

        <div className="space-y-5">
          <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl">
            Turn any GitHub repository into a focused interview session
          </h1>
          <p className="max-w-2xl text-pretty text-muted-foreground">
            Paste a repository URL, generate a compact knowledge pack, and practice repo-aware
            technical Q&A with instant feedback.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex max-w-2xl flex-col gap-3 sm:flex-row">
          <Input
            type="url"
            required
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://github.com/owner/repository"
            className="h-11"
          />
          <Button type="submit" disabled={isLoading || !url.trim()} className="h-11 gap-2">
            <Sparkles className="size-4" />
            {isLoading ? "Analyzing..." : "Analyze Repository"}
            <ArrowRight className="size-4" />
          </Button>
        </form>

        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
            Model
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={modelProvider === "openai" ? "default" : "outline"}
              size="sm"
              disabled={isLoading}
              onClick={() => onModelProviderChange("openai")}
              className="rounded-full text-xs"
            >
              OpenAI current
            </Button>
            <Button
              type="button"
              variant={modelProvider === "gemini" ? "default" : "outline"}
              size="sm"
              disabled={isLoading}
              onClick={() => onModelProviderChange("gemini")}
              className="rounded-full text-xs"
            >
              Gemini 3.1 Flash Lite
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted-foreground">
            Demo repos
          </p>
          <div className="flex flex-wrap gap-2">
            {DEMO_REPOS.map((repo) => (
              <Button
                key={repo.url}
                type="button"
                variant="outline"
                size="sm"
                disabled={isLoading}
                onClick={() => onAnalyze(repo.url)}
                className="rounded-full text-xs"
              >
                {repo.label}
              </Button>
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}
