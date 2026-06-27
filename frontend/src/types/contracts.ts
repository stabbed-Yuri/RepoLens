export type AnalyzeRequest = {
  repository_url: string;
};

export type DependencyManifest = {
  path: string;
  manifest_type: string;
  package_manager: string | null;
  dependencies: string[];
  dev_dependencies: string[];
  framework_hints: string[];
};

export type RepositoryStatistics = {
  file_count: number;
  directory_count: number;
  binary_file_count: number;
  generated_file_count: number;
  vendored_file_count: number;
  documentation_file_count: number;
  config_file_count: number;
  test_file_count: number;
  entry_point_count: number;
  dependency_manifest_count: number;
};

export type RepositoryProfile = {
  repo_name: string;
  repo_url: string;
  primary_language: string | null;
  language_breakdown: Record<string, number>;
  frameworks: string[];
  dependencies: DependencyManifest[];
  entry_points: string[];
  folder_tree: string[];
  readme_text: string | null;
  important_files: string[];
  test_files: string[];
  config_files: string[];
  documentation_files: string[];
  feature_signals: string[];
  statistics: RepositoryStatistics;
  classification_tool: string;
  repo_type_summary: string | null;
  scanned_at: string;
};

export type KnowledgePackChunk = {
  chunk_id: string;
  source_path: string;
  chunk_type: "source" | "documentation" | "config" | "manifest";
  start_line: number;
  end_line: number;
  text_excerpt: string;
};

export type KnowledgePackStats = {
  chunk_count: number;
  embedded_chunk_count: number;
  embedding_dimensions: number;
};

export type KnowledgePack = {
  repo_name: string;
  repo_url: string;
  repo_sha: string;
  profile: RepositoryProfile;
  key_chunks: KnowledgePackChunk[];
  topic_hits: Record<string, unknown[]>;
  stats: KnowledgePackStats;
  generated_at: string;
};

export type InterviewQuestion = {
  prompt: string;
  focus_area: string;
  difficulty: string;
};

export type InterviewStartRequest = {
  repository_url: string;
  user_id?: string | null;
};

export type InterviewStartResponse = {
  session_id: string;
  question: InterviewQuestion;
  status: string;
};

export type InterviewAnswerRequest = {
  session_id: string;
  answer: string;
};

export type InterviewAnswerResponse = {
  session_id: string;
  evaluation: string;
  follow_up_question: string | null;
  next_action: "continue_interview" | "study_plan_ready" | "retry_later";
};
