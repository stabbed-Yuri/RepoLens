import { useState } from "react"
import {
  BookOpen,
  GitBranch,
  ArrowRight,
  Loader2,
  Code2,
  FileText,
  Package,
  TestTube,
  FolderOpen,
  Zap,
  ExternalLink,
  ShieldAlert,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import type { KnowledgePack, ModelProvider } from "@/types"

interface AnalyzeViewProps {
  initialUrl: string
  knowledgePack: KnowledgePack | null
  isLoading: boolean
  error: string | null
  onAnalyze: (url: string) => void
  onStartInterview: () => void
  isStartingInterview: boolean
  modelProvider: ModelProvider
  onModelProviderChange: (provider: ModelProvider) => void
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-5 text-center">
      <div className="relative">
        <div className="size-16 rounded-full border-4 border-border" />
        <div className="absolute inset-0 size-16 rounded-full border-4 border-primary border-t-transparent animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <BookOpen className="size-5 text-primary" />
        </div>
      </div>
      <div>
        <p className="font-medium text-sm">Analyzing repository</p>
        <p className="text-xs text-muted-foreground mt-1">This may take 15-30 seconds for large repos.</p>
      </div>
    </div>
  )
}
function LoadingSkeleton() {
  return (
    <div className="space-y-6 py-8">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-96" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-20 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="h-32 rounded-xl" />
      </div>
    </div>
  )
}

function LanguageBar({ breakdown }: { breakdown: Record<string, number> }) {
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0)
  if (total === 0) return null

  const colors = [
    "bg-chart-1",
    "bg-chart-2",
    "bg-chart-3",
    "bg-chart-4",
    "bg-chart-5",
    "bg-primary",
    "bg-muted-foreground",
  ]

  const sorted = Object.entries(breakdown)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6)

  return (
    <div className="space-y-3">
      <div className="flex h-2 rounded-full overflow-hidden gap-px">
        {sorted.map(([lang, count], i) => (
          <div
            key={lang}
            className={`${colors[i % colors.length]} transition-all`}
            style={{ width: `${(count / total) * 100}%` }}
            title={`${lang}: ${((count / total) * 100).toFixed(1)}%`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {sorted.map(([lang, count], i) => (
          <div key={lang} className="flex items-center gap-1.5">
            <div className={`size-2 rounded-full ${colors[i % colors.length]}`} />
            <span className="text-xs text-muted-foreground">{lang}</span>
            <span className="text-xs font-medium">{((count / total) * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: number | string }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4 px-4 flex items-center gap-3">
        <div className="flex size-8 items-center justify-center rounded-md bg-muted shrink-0">
          <Icon className="size-4 text-muted-foreground" />
        </div>
        <div className="min-w-0">
          <p className="text-lg font-bold leading-none">{value}</p>
          <p className="text-xs text-muted-foreground mt-0.5 truncate">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}

export function AnalyzeView({
  initialUrl,
  knowledgePack,
  isLoading,
  error,
  onAnalyze,
  onStartInterview,
  isStartingInterview,
  modelProvider,
  onModelProviderChange,
}: AnalyzeViewProps) {
  const [url, setUrl] = useState(initialUrl)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = url.trim()
    if (trimmed) onAnalyze(trimmed)
  }

  const profile = knowledgePack?.profile
  const hasLimitedSignal = Boolean(
    knowledgePack && profile && (knowledgePack.stats.chunk_count < 5 || profile.statistics.file_count < 5),
  )
  const dependencySignals =
    profile?.dependencies
      .slice(0, 5)
      .map((manifest) => ({
        manifest: manifest.path,
        packageManager: manifest.package_manager || manifest.manifest_type,
        dependencies: manifest.dependencies.slice(0, 4),
      })) ?? []

  return (
    <div className="flex flex-col min-h-svh">
      {/* header */}
      <header className="sticky top-0 z-40 border-b border-border/50 bg-background/80 backdrop-blur-sm">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 h-14 flex items-center gap-4">
          <button
            onClick={() => onAnalyze("")}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <div className="flex size-7 items-center justify-center rounded-md bg-primary">
              <BookOpen className="size-4 text-primary-foreground" />
            </div>
            <span className="font-semibold tracking-tight">RepoLens</span>
          </button>
          <Separator orientation="vertical" className="h-5" />
          <form onSubmit={handleSubmit} className="flex-1 flex gap-2 max-w-xl">
            <div className="relative flex-1">
              <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repo"
                className="pl-8 h-8 text-xs"
                disabled={isLoading}
              />
            </div>
            <Button type="submit" size="sm" className="h-8 gap-1" disabled={!url.trim() || isLoading}>
              {isLoading ? <Loader2 className="size-3 animate-spin" /> : <ArrowRight className="size-3" />}
              {isLoading ? "Analyzing…" : "Analyze"}
            </Button>
          </form>
          <div className="hidden sm:flex items-center gap-1 rounded-full border border-border p-1">
            <Button
              type="button"
              size="sm"
              variant={modelProvider === "openai" ? "secondary" : "ghost"}
              disabled={isLoading}
              onClick={() => onModelProviderChange("openai")}
              className="h-6 rounded-full px-2 text-[11px]"
            >
              OpenAI
            </Button>
            <Button
              type="button"
              size="sm"
              variant={modelProvider === "gemini" ? "secondary" : "ghost"}
              disabled={isLoading}
              onClick={() => onModelProviderChange("gemini")}
              className="h-6 rounded-full px-2 text-[11px]"
            >
              Gemini
            </Button>
          </div>
        </div>
      </header>

      {/* content */}
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 sm:px-6 py-8">
        {isLoading && <LoadingState />}

        {!isLoading && !profile && !error && <LoadingSkeleton />}

        {error && (
          <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
            <div className="flex size-12 items-center justify-center rounded-full bg-destructive/10">
              <Loader2 className="size-5 text-destructive" />
            </div>
            <div>
              <p className="font-medium text-sm">Analysis failed</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                {error.includes("Failed to fetch")
                  ? "Could not reach the RepoLens backend. Make sure the server is running."
                  : error}
              </p>
            </div>
            <Button size="sm" variant="outline" onClick={() => onAnalyze(url)}>
              Try again
            </Button>
          </div>
        )}

        {!isLoading && profile && knowledgePack && (
          <div className="space-y-6">
            {/* repo header */}
            <div className="flex flex-col sm:flex-row sm:items-start gap-4 justify-between">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-2xl font-bold tracking-tight">{profile.repo_name}</h1>
                  {profile.primary_language && (
                    <Badge variant="secondary">{profile.primary_language}</Badge>
                  )}
                  {profile.project_type && (
                    <Badge variant="outline">{profile.project_type.replace(/-/g, " ")}</Badge>
                  )}
                  {profile.frameworks.slice(0, 3).map((f) => (
                    <Badge key={f} variant="outline">{f}</Badge>
                  ))}
                </div>
                {profile.repo_type_summary && (
                  <p className="mt-1.5 text-sm text-muted-foreground max-w-xl">{profile.repo_type_summary}</p>
                )}
                {profile.project_purpose && (
                  <p className="mt-1 text-xs text-muted-foreground max-w-xl">{profile.project_purpose}</p>
                )}
                <a
                  href={profile.repo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ExternalLink className="size-3" />
                  {profile.repo_url}
                </a>
              </div>

              <Button
                size="lg"
                onClick={onStartInterview}
                disabled={isStartingInterview}
                className="sm:self-start gap-2 shrink-0"
              >
                {isStartingInterview ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Starting…
                  </>
                ) : (
                  <>
                    Start Interview
                    <ArrowRight className="size-4" />
                  </>
                )}
              </Button>
            </div>

            {/* stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard icon={FileText} label="Files" value={profile.statistics.file_count} />
              <StatCard icon={Code2} label="Entry Points" value={profile.statistics.entry_point_count} />
              <StatCard icon={TestTube} label="Test Files" value={profile.statistics.test_file_count} />
              <StatCard icon={Package} label="Manifests" value={profile.statistics.dependency_manifest_count} />
            </div>

            {hasLimitedSignal && (
              <Card className="border-amber-300/60 bg-amber-50 text-amber-950 dark:border-amber-400/30 dark:bg-amber-950/30 dark:text-amber-100">
                <CardContent className="pt-4 text-sm">
                  Limited repository signal found, interview may focus on available artifacts.
                </CardContent>
              </Card>
            )}



            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* language breakdown */}
              {Object.keys(profile.language_breakdown).length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm">Language Breakdown</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <LanguageBar breakdown={profile.language_breakdown} />
                  </CardContent>
                </Card>
              )}

              {/* knowledge pack stats */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center gap-1.5">
                    <Zap className="size-3.5 text-primary" />
                    Knowledge Pack
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {knowledgePack.stats.chunk_count} context chunks ready for grounding
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {[
                      { label: "Total chunks", value: knowledgePack.stats.chunk_count },
                      { label: "Embedded chunks", value: knowledgePack.stats.embedded_chunk_count },
                      { label: "Topics indexed", value: Object.keys(knowledgePack.topic_hits).length },
                    ].map(({ label, value }) => (
                      <div key={label} className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">{label}</span>
                        <span className="text-xs font-semibold tabular-nums">{value}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* dependency + maintainability signals */}
            {(dependencySignals.length > 0 || profile.config_files.length > 0 || profile.test_files.length > 0) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-1.5">
                      <Package className="size-3.5" />
                      Dependency Signals
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {dependencySignals.length === 0 ? (
                      <p className="text-xs text-muted-foreground">No dependency manifests detected.</p>
                    ) : (
                      dependencySignals.map((item) => (
                        <div key={item.manifest} className="rounded-md border border-border/70 p-2.5">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-xs font-mono truncate">{item.manifest}</p>
                            <Badge variant="secondary" className="text-[10px]">
                              {item.packageManager}
                            </Badge>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {item.dependencies.length > 0
                              ? item.dependencies.join(", ")
                              : "No explicit dependencies parsed"}
                          </p>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm flex items-center gap-1.5">
                      <ShieldAlert className="size-3.5" />
                      Interview Risk Checks
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Config files</span>
                      <span className="font-semibold tabular-nums">{profile.config_files.length}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Test files</span>
                      <span className="font-semibold tabular-nums">{profile.test_files.length}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Documentation files</span>
                      <span className="font-semibold tabular-nums">{profile.documentation_files.length}</span>
                    </div>
                    <Separator />
                    <p className="text-xs text-muted-foreground">
                      Suggested focus: {profile.test_files.length === 0 ? "testing gaps, reliability risks" : "test strategy and coverage quality"}.
                    </p>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* feature signals */}
            {profile.interview_focus_areas.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Suggested Interview Themes</CardTitle>
                  <CardDescription className="text-xs">Language-independent topics inferred from repository artifacts</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {profile.interview_focus_areas.map((area) => (
                      <Badge key={area} variant="outline" className="text-xs capitalize">
                        {area}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* feature signals */}
            {profile.feature_signals.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Detected Features</CardTitle>
                  <CardDescription className="text-xs">Topics likely to appear in your interview</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {profile.feature_signals.map((sig) => (
                      <Badge key={sig} variant="secondary" className="text-xs">
                        {sig}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* file structure preview */}
            {profile.important_files.length > 0 && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center gap-1.5">
                    <FolderOpen className="size-3.5" />
                    Key Files
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                    {profile.important_files.slice(0, 12).map((f) => (
                      <div key={f} className="flex items-center gap-1.5 text-xs text-muted-foreground font-mono">
                        <FileText className="size-3 shrink-0" />
                        <span className="truncate">{f}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* CTA banner */}
            <div className="rounded-xl border border-primary/20 bg-primary/5 p-6 flex flex-col sm:flex-row items-start sm:items-center gap-4 justify-between">
              <div>
                <h3 className="font-semibold">Ready to practice?</h3>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Start a personalized interview grounded in {profile.repo_name}&apos;s codebase.
                </p>
              </div>
              <Button
                size="lg"
                onClick={onStartInterview}
                disabled={isStartingInterview}
                className="gap-2 shrink-0"
              >
                {isStartingInterview ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <ArrowRight className="size-4" />
                )}
                Start Interview
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
