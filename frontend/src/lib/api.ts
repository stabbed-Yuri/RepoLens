import type {
  KnowledgePack,
  InterviewStartResponse,
  InterviewAnswerResponse,
  InterviewStopResponse,
  ModelProvider,
} from "@/types"

const rawBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  (import.meta.env.VITE_API_URL as string | undefined) ??
  "http://localhost:8000"
const BASE_URL = rawBaseUrl.replace(/\/+$/, "")

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(text || `Request failed with status ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () =>
    request<{ status: string; timestamp: string }>("/health"),

  analyzeKnowledgePack: (repository_url: string, model_provider: ModelProvider = "openai") =>
    request<KnowledgePack>("/analyze/knowledge-pack", {
      method: "POST",
      body: JSON.stringify({ repository_url, model_provider }),
    }),

  interviewStart: (repository_url: string, model_provider: ModelProvider = "openai", user_id?: string) =>
    request<InterviewStartResponse>("/interview/start", {
      method: "POST",
      body: JSON.stringify({ repository_url, user_id, model_provider }),
    }),

  interviewAnswer: (session_id: string, answer: string) =>
    request<InterviewAnswerResponse>("/interview/answer", {
      method: "POST",
      body: JSON.stringify({ session_id, answer }),
    }),

  interviewStop: (session_id: string) =>
    request<InterviewStopResponse>("/interview/stop", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),
}
