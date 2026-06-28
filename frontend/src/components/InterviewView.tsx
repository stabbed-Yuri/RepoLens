import { useEffect, useRef, useState } from "react"
import {
  BookOpen,
  Send,
  Square,
  Bot,
  User,
  Loader2,
  Star,
  ChevronRight,
  AlertTriangle,
  Trophy,
  ListChecks,
  GitBranch,
  ArrowLeft,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { ChatMessage, InterviewStopResponse } from "@/types"
import { cn } from "@/lib/utils"

interface InterviewViewProps {
  repoName: string
  repoUrl: string
  messages: ChatMessage[]
  summary: InterviewStopResponse | null
  isWaiting: boolean
  onAnswer: (answer: string) => void
  onStop: () => void
  onBackToAnalysis: () => void
  isStopping: boolean
  phase: "interview" | "summary"
  questionCount: number
}

function ScoreDots({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "size-1.5 rounded-full transition-colors",
            i < score
              ? score >= 8
                ? "bg-emerald-500"
                : score >= 5
                  ? "bg-amber-500"
                  : "bg-destructive"
              : "bg-border"
          )}
        />
      ))}
      <span className="ml-1.5 text-xs font-semibold tabular-nums">{score}/10</span>
    </div>
  )
}

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const d = difficulty.toLowerCase()
  if (d.includes("easy") || d.includes("basic"))
    return <Badge variant="secondary" className="text-xs">Easy</Badge>
  if (d.includes("hard") || d.includes("advanced"))
    return <Badge variant="destructive" className="text-xs">Hard</Badge>
  return <Badge variant="outline" className="text-xs">Medium</Badge>
}

function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.type === "system") {
    return (
      <div className="flex justify-center py-1">
        <span className="text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    )
  }

  if (message.type === "question" || message.type === "follow_up") {
    return (
      <div className="flex gap-3">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 mt-0.5">
          <Bot className="size-4 text-primary" />
        </div>
        <div className="flex-1 space-y-2 max-w-prose">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-primary">Coach</span>
            {message.focusArea && (
              <Badge variant="outline" className="text-xs h-4 px-1.5 gap-1">
                <ChevronRight className="size-2.5" />
                {message.focusArea}
              </Badge>
            )}
            {message.difficulty && <DifficultyBadge difficulty={message.difficulty} />}
            {message.type === "follow_up" && (
              <Badge variant="secondary" className="text-xs h-4 px-1.5">Follow-up</Badge>
            )}
          </div>
          <div className="rounded-xl rounded-tl-sm bg-card border border-border px-4 py-3 text-sm leading-relaxed">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  if (message.type === "answer") {
    return (
      <div className="flex gap-3 flex-row-reverse">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted border border-border mt-0.5">
          <User className="size-4 text-muted-foreground" />
        </div>
        <div className="flex-1 flex flex-col items-end space-y-1 max-w-prose">
          <span className="text-xs font-medium text-muted-foreground">You</span>
          <div className="rounded-xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-3 text-sm leading-relaxed">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  if (message.type === "evaluation") {
    const score = message.score ?? null
    return (
      <div className="flex gap-3">
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted border border-border mt-0.5">
          <Star className="size-4 text-amber-500" />
        </div>
        <div className="flex-1 space-y-2 max-w-prose">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-medium text-muted-foreground">Evaluation</span>
            {score !== null && <ScoreDots score={score} />}
          </div>
          <div className="rounded-xl rounded-tl-sm bg-muted/50 border border-border/60 px-4 py-3 text-sm leading-relaxed text-muted-foreground">
            {message.content}
          </div>
        </div>
      </div>
    )
  }

  return null
}

function SummaryView({
  summary,
  repoName,
  onBackToAnalysis,
}: {
  summary: InterviewStopResponse
  repoName: string
  onBackToAnalysis: () => void
}) {
  const score = summary.score_out_of_10
  return (
    <div className="flex flex-col gap-6 py-8">
      {/* trophy header */}
      <div className="text-center space-y-3">
        <div className="inline-flex size-16 items-center justify-center rounded-full bg-primary/10 border-2 border-primary/20 mx-auto">
          <Trophy className="size-7 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-bold">Interview Complete</h2>
          <p className="text-sm text-muted-foreground mt-1">{repoName}</p>
        </div>
        {score !== null && (
          <div className="inline-flex items-center gap-2 rounded-full bg-card border px-5 py-2">
            <span className="text-sm text-muted-foreground">Overall score</span>
            <ScoreDots score={score} />
          </div>
        )}
      </div>

      {/* summary text */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Session Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">{summary.summary}</p>
        </CardContent>
      </Card>

      {/* next steps */}
      {summary.next_steps.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <ListChecks className="size-4" />
              Next Steps
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {summary.next_steps.map((step, i) => (
                <li key={i} className="flex gap-2.5 text-sm">
                  <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-muted-foreground leading-relaxed">{step}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-center">
        <Button type="button" variant="outline" onClick={onBackToAnalysis} className="gap-2">
          <ArrowLeft className="size-4" />
          Back to analysis
        </Button>
      </div>
    </div>
  )
}

export function InterviewView({
  repoName,
  repoUrl,
  messages,
  summary,
  isWaiting,
  onAnswer,
  onStop,
  onBackToAnalysis,
  isStopping,
  phase,
  questionCount,
}: InterviewViewProps) {
  const [answer, setAnswer] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const bottom = bottomRef.current
    if (bottom && typeof bottom.scrollIntoView === "function") {
      bottom.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, isWaiting, summary])

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault()
    const trimmed = answer.trim()
    if (!trimmed || isWaiting) return
    onAnswer(trimmed)
    setAnswer("")
    textareaRef.current?.focus()
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const lastMessage = messages[messages.length - 1]
  const canAnswer =
    phase === "interview" &&
    !isWaiting &&
    (lastMessage?.type === "question" || lastMessage?.type === "follow_up" || lastMessage?.type === "evaluation")

  return (
    <div className="flex flex-col h-svh">
      {/* header */}
      <header className="shrink-0 border-b border-border/50 bg-background/80 backdrop-blur-sm z-40">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 h-14 flex items-center gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary">
              <BookOpen className="size-4 text-primary-foreground" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-semibold tracking-tight text-sm truncate">{repoName}</span>
                <a
                  href={repoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
                >
                  <GitBranch className="size-3.5" />
                </a>
              </div>
              {phase === "interview" && questionCount > 0 && (
                <p className="text-xs text-muted-foreground">Question {questionCount}</p>
              )}
              {phase === "summary" && (
                <p className="text-xs text-muted-foreground">Interview complete</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {phase === "interview" && (
              <Button
                variant="outline"
                size="sm"
                onClick={onStop}
                disabled={isStopping || isWaiting}
                className="h-8 gap-1.5 text-muted-foreground hover:text-foreground"
              >
                {isStopping ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <Square className="size-3" />
                )}
                {isStopping ? "Finishing…" : "Stop"}
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* messages */}
      <ScrollArea className="flex-1">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 py-6 space-y-5">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {isWaiting && (
            <div className="flex gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20 mt-0.5">
                <Bot className="size-4 text-primary" />
              </div>
              <div className="flex items-center gap-1.5 px-4 py-3 rounded-xl rounded-tl-sm bg-card border border-border">
                <span className="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:0ms]" />
                <span className="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:150ms]" />
                <span className="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}

          {phase === "summary" && summary && (
            <>
              <Separator />
              <SummaryView summary={summary} repoName={repoName} onBackToAnalysis={onBackToAnalysis} />
            </>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* input area */}
      {phase === "interview" && (
        <div className="shrink-0 border-t border-border/50 bg-background/80 backdrop-blur-sm">
          <div className="mx-auto max-w-3xl px-4 sm:px-6 py-3">
            {!canAnswer && !isWaiting && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground justify-center py-1">
                <AlertTriangle className="size-3" />
                Waiting for the next question…
              </div>
            )}
            <form onSubmit={handleSubmit} className="relative">
              <Textarea
                ref={textareaRef}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={canAnswer ? "Type your answer... (Shift+Enter for newline)" : "Waiting..."}
                disabled={!canAnswer}
                rows={3}
                className="resize-none pr-12 text-sm"
              />
              <Button
                type="submit"
                size="icon-sm"
                aria-label="Send answer"
                disabled={!answer.trim() || !canAnswer}
                className="absolute right-2 bottom-2"
              >
                <Send className="size-3.5" />
              </Button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
