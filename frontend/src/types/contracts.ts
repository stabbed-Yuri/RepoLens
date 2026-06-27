export type RepositoryProfileStats = {
  file_count: number;
  directory_count: number;
  primary_languages: Record<string, number>;
};

export type RepositoryProfile = {
  repository_url: string;
  repository_name: string;
  owner: string;
  default_branch: string | null;
  short_summary: string;
  architecture_notes: string[];
  key_technologies: string[];
  interview_focus_areas: string[];
  classification_tool: string;
  stats: RepositoryProfileStats;
};

export type InterviewSessionStatus = "pending" | "in_progress" | "complete";

export type InterviewSession = {
  session_id: string;
  repository_url: string;
  user_id: string | null;
  status: InterviewSessionStatus;
};

