import type {
  AnalyzeRequest,
  InterviewAnswerRequest,
  InterviewAnswerResponse,
  InterviewStartRequest,
  InterviewStartResponse,
  InterviewStopRequest,
  InterviewStopResponse,
  KnowledgePack,
  RepositoryProfile,
} from "../types/contracts";

const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const apiBaseUrl = rawApiBaseUrl.replace(/\/+$/, "");

export type RequestOptions = {
  method?: "GET" | "POST";
  body?: unknown;
};

export async function apiRequest<TResponse>(
  path: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  const { method = "GET", body } = options;
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

export function analyzeRepository(payload: AnalyzeRequest): Promise<RepositoryProfile> {
  return apiRequest<RepositoryProfile>("/analyze", {
    method: "POST",
    body: payload,
  });
}

export function buildKnowledgePack(payload: AnalyzeRequest): Promise<KnowledgePack> {
  return apiRequest<KnowledgePack>("/analyze/knowledge-pack", {
    method: "POST",
    body: payload,
  });
}

export function startInterview(
  payload: InterviewStartRequest,
): Promise<InterviewStartResponse> {
  return apiRequest<InterviewStartResponse>("/interview/start", {
    method: "POST",
    body: payload,
  });
}

export function answerInterview(
  payload: InterviewAnswerRequest,
): Promise<InterviewAnswerResponse> {
  return apiRequest<InterviewAnswerResponse>("/interview/answer", {
    method: "POST",
    body: payload,
  });
}

export function stopInterview(payload: InterviewStopRequest): Promise<InterviewStopResponse> {
  return apiRequest<InterviewStopResponse>("/interview/stop", {
    method: "POST",
    body: payload,
  });
}
