export interface DependencyManifest {
  path: string
  manifest_type: string
  package_manager: string | null
  dependencies: string[]
  dev_dependencies: string[]
  framework_hints: string[]
}

export interface RepoStatistics {
  file_count: number
  directory_count: number
  binary_file_count: number
  generated_file_count: number
  vendored_file_count: number
  documentation_file_count: number
  config_file_count: number
  test_file_count: number
  entry_point_count: number
  dependency_manifest_count: number
}

export interface RepositoryProfile {
  repo_name: string
  repo_url: string
  primary_language: string | null
  language_breakdown: Record<string, number>
  frameworks: string[]
  dependencies: DependencyManifest[]
  entry_points: string[]
  folder_tree: string[]
  readme_text: string | null
  important_files: string[]
  test_files: string[]
  config_files: string[]
  documentation_files: string[]
  feature_signals: string[]
  statistics: RepoStatistics
  classification_tool: string
  project_type: string | null
  project_purpose: string | null
  interview_focus_areas: string[]
  repo_type_summary: string | null
  scanned_at: string
}

export interface KeyChunk {
  chunk_id: string
  source_path: string
  chunk_type: "source" | "documentation" | "config" | "manifest"
  start_line: number
  end_line: number
  text_excerpt: string
}

export interface KnowledgePack {
  repo_name: string
  repo_url: string
  repo_sha: string
  profile: RepositoryProfile
  key_chunks: KeyChunk[]
  topic_hits: Record<string, unknown[]>
  stats: {
    chunk_count: number
    embedded_chunk_count: number
    embedding_dimensions: number
  }
  provider_used: ModelProvider | "hash" | null
  fallback_used: boolean
  fallback_reason: string | null
  generated_at: string
}

export interface InterviewQuestion {
  prompt: string
  focus_area: string
  difficulty: string
}

export interface InterviewStartResponse {
  session_id: string
  question: InterviewQuestion
  status: string
  provider_used: ModelProvider | null
  fallback_used: boolean
  fallback_reason: string | null
}

export interface InterviewAnswerResponse {
  session_id: string
  evaluation: string
  score_out_of_10: number | null
  follow_up_question: string | null
  next_action: "continue_interview" | "study_plan_ready" | "retry_later"
  provider_used: ModelProvider | null
  fallback_used: boolean
  fallback_reason: string | null
}

export interface InterviewStopResponse {
  session_id: string
  summary: string
  score_out_of_10: number | null
  next_steps: string[]
  provider_used: ModelProvider | null
  fallback_used: boolean
  fallback_reason: string | null
}

export type AppPhase =
  | "landing"
  | "analyzing"
  | "analyzed"
  | "starting_interview"
  | "interview"
  | "summary"

export type ChatMessageType =
  | "question"
  | "answer"
  | "evaluation"
  | "follow_up"
  | "system"
  | "summary"

export interface ChatMessage {
  id: string
  type: ChatMessageType
  content: string
  focusArea?: string
  difficulty?: string
  score?: number | null
  timestamp: Date
}
export type ModelProvider = "openai" | "gemini"
