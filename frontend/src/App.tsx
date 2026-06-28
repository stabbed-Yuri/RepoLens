import { useState, useCallback } from "react"
import { HeroSection } from "@/components/HeroSection"
import { AnalyzeView } from "@/components/AnalyzeView"
import { InterviewView } from "@/components/InterviewView"
import { api } from "@/lib/api"
import type {
  AppPhase,
  ChatMessage,
  KnowledgePack,
  InterviewStopResponse,
  ModelProvider,
} from "@/types"

let messageCounter = 0
function makeId() {
  return `msg_${++messageCounter}_${Date.now()}`
}

export function App() {
  const [phase, setPhase] = useState<AppPhase>("landing")
  const [repoUrl, setRepoUrl] = useState("")
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [knowledgePack, setKnowledgePack] = useState<KnowledgePack | null>(null)
  const [modelProvider, setModelProvider] = useState<ModelProvider>("openai")

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isStartingInterview, setIsStartingInterview] = useState(false)
  const [isWaiting, setIsWaiting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [summary, setSummary] = useState<InterviewStopResponse | null>(null)
  const [questionCount, setQuestionCount] = useState(0)
  const [interviewPhase, setInterviewPhase] = useState<"interview" | "summary">("interview")

  const handleAnalyze = useCallback(async (url: string) => {
    if (!url) {
      setPhase("landing")
      setRepoUrl("")
      setKnowledgePack(null)
      setAnalyzeError(null)
      return
    }

    setRepoUrl(url)
    setAnalyzeError(null)
    setKnowledgePack(null)
    setIsAnalyzing(true)
    setPhase("analyzing")

    try {
      const pack = await api.analyzeKnowledgePack(url, modelProvider)
      setKnowledgePack(pack)
      setPhase("analyzed")
    } catch (err) {
      setAnalyzeError(
        err instanceof Error ? err.message : "Analysis failed. Check the URL and try again."
      )
      setPhase("analyzed")
    } finally {
      setIsAnalyzing(false)
    }
  }, [modelProvider])

  const handleStartInterview = useCallback(async () => {
    if (!repoUrl) return
    setIsStartingInterview(true)
    setMessages([])
    setSummary(null)
    setQuestionCount(0)
    setInterviewPhase("interview")

    try {
      const resp = await api.interviewStart(repoUrl, modelProvider)
      setSessionId(resp.session_id)
      setQuestionCount(1)
      const fallbackMessage: ChatMessage[] = resp.fallback_used
        ? [
            {
              id: makeId(),
              type: "system",
              content: `${resp.fallback_reason || "Selected provider was unavailable"}, continued with ${resp.provider_used?.toUpperCase() || "fallback provider"}.`,
              timestamp: new Date(),
            },
          ]
        : []
      setMessages([
        ...fallbackMessage,
        {
          id: makeId(),
          type: "system",
          content: `Interview started for ${knowledgePack?.repo_name ?? repoUrl}`,
          timestamp: new Date(),
        },
        {
          id: makeId(),
          type: "question",
          content: resp.question.prompt,
          focusArea: resp.question.focus_area,
          difficulty: resp.question.difficulty,
          timestamp: new Date(),
        },
      ])
      setPhase("interview")
    } catch (err) {
      setAnalyzeError(
        err instanceof Error ? err.message : "Failed to start interview. Please try again."
      )
    } finally {
      setIsStartingInterview(false)
    }
  }, [repoUrl, knowledgePack, modelProvider])

  const doStop = useCallback(
    async (sid: string) => {
      setIsStopping(true)
      try {
        const resp = await api.interviewStop(sid)
        setSummary(resp)
        setInterviewPhase("summary")
        setMessages((prev) => [
          ...prev,
          ...(resp.fallback_used
            ? [
                {
                  id: makeId(),
                  type: "system" as const,
                  content: `${resp.fallback_reason || "Selected provider was unavailable"}, continued with ${resp.provider_used?.toUpperCase() || "fallback provider"}.`,
                  timestamp: new Date(),
                },
              ]
            : []),
          {
            id: makeId(),
            type: "system",
            content: "Interview ended.",
            timestamp: new Date(),
          },
        ])
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: makeId(),
            type: "system",
            content: `Could not retrieve summary: ${err instanceof Error ? err.message : "Unknown error"}`,
            timestamp: new Date(),
          },
        ])
      } finally {
        setIsStopping(false)
      }
    },
    []
  )

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!sessionId) return
      setIsWaiting(true)

      setMessages((prev) => [
        ...prev,
        { id: makeId(), type: "answer", content: answer, timestamp: new Date() },
      ])

      try {
        const resp = await api.interviewAnswer(sessionId, answer)

        const evalMsg: ChatMessage = {
          id: makeId(),
          type: "evaluation",
          content: resp.evaluation,
          score: resp.score_out_of_10,
          timestamp: new Date(),
        }

        const fallbackMessage: ChatMessage[] = resp.fallback_used
          ? [
              {
                id: makeId(),
                type: "system",
                content: `${resp.fallback_reason || "Selected provider was unavailable"}, continued with ${resp.provider_used?.toUpperCase() || "fallback provider"}.`,
                timestamp: new Date(),
              },
            ]
          : []

        if (resp.next_action === "continue_interview" && resp.follow_up_question) {
          setQuestionCount((n) => n + 1)
          setMessages((prev) => [
            ...prev,
            ...fallbackMessage,
            evalMsg,
            {
              id: makeId(),
              type: "follow_up",
              content: resp.follow_up_question!,
              timestamp: new Date(),
            },
          ])
        } else if (resp.next_action === "study_plan_ready") {
          setMessages((prev) => [...prev, ...fallbackMessage, evalMsg])
          await doStop(sessionId)
        } else if (resp.next_action === "retry_later") {
          setMessages((prev) => [
            ...prev,
            ...fallbackMessage,
            evalMsg,
            {
              id: makeId(),
              type: "system",
              content: "Session paused. Stop the interview to view your summary.",
              timestamp: new Date(),
            },
          ])
        } else {
          setMessages((prev) => [...prev, ...fallbackMessage, evalMsg])
        }
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            id: makeId(),
            type: "system",
            content: `Error: ${err instanceof Error ? err.message : "Something went wrong."}`,
            timestamp: new Date(),
          },
        ])
      } finally {
        setIsWaiting(false)
      }
    },
    [sessionId, doStop]
  )

  const handleStop = useCallback(() => {
    if (sessionId) doStop(sessionId)
  }, [sessionId, doStop])

  const handleBackToAnalysis = useCallback(() => {
    setSessionId(null)
    setMessages([])
    setSummary(null)
    setQuestionCount(0)
    setInterviewPhase("interview")
    setPhase(knowledgePack ? "analyzed" : "landing")
  }, [knowledgePack])

  if (phase === "landing") {
    return (
      <HeroSection
        onAnalyze={handleAnalyze}
        isLoading={isAnalyzing}
        modelProvider={modelProvider}
        onModelProviderChange={setModelProvider}
      />
    )
  }

  if (phase === "analyzing" || phase === "analyzed") {
    return (
      <AnalyzeView
        initialUrl={repoUrl}
        knowledgePack={knowledgePack}
        isLoading={isAnalyzing}
        error={analyzeError}
        onAnalyze={handleAnalyze}
        onStartInterview={handleStartInterview}
        isStartingInterview={isStartingInterview}
        modelProvider={modelProvider}
        onModelProviderChange={setModelProvider}
      />
    )
  }

  if (phase === "interview" && knowledgePack) {
    return (
      <InterviewView
        repoName={knowledgePack.repo_name}
        repoUrl={knowledgePack.repo_url}
        messages={messages}
        summary={summary}
        isWaiting={isWaiting}
        onAnswer={handleAnswer}
        onStop={handleStop}
        onBackToAnalysis={handleBackToAnalysis}
        isStopping={isStopping}
        phase={interviewPhase}
        questionCount={questionCount}
      />
    )
  }

  return null
}

export default App
