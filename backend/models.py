from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalyzeRequest(BaseModel):
    repository_url: HttpUrl


class DependencyManifest(BaseModel):
    path: str
    manifest_type: str
    package_manager: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    dev_dependencies: list[str] = Field(default_factory=list)
    framework_hints: list[str] = Field(default_factory=list)


class ClassifiedFiles(BaseModel):
    primary_language: str | None = None
    language_breakdown: dict[str, float] = Field(default_factory=dict)
    binary_files: list[str] = Field(default_factory=list)
    generated_files: list[str] = Field(default_factory=list)
    vendored_files: list[str] = Field(default_factory=list)
    documentation_files: list[str] = Field(default_factory=list)
    classification_tool: str = "linguist-compatible"


class RepositoryStatistics(BaseModel):
    file_count: int = 0
    directory_count: int = 0
    binary_file_count: int = 0
    generated_file_count: int = 0
    vendored_file_count: int = 0
    documentation_file_count: int = 0
    config_file_count: int = 0
    test_file_count: int = 0
    entry_point_count: int = 0
    dependency_manifest_count: int = 0


class RepositoryProfile(BaseModel):
    repo_name: str
    repo_url: HttpUrl
    primary_language: str | None = None
    language_breakdown: dict[str, float] = Field(default_factory=dict)
    frameworks: list[str] = Field(default_factory=list)
    dependencies: list[DependencyManifest] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    folder_tree: list[str] = Field(default_factory=list)
    readme_text: str | None = None
    important_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    documentation_files: list[str] = Field(default_factory=list)
    feature_signals: list[str] = Field(default_factory=list)
    statistics: RepositoryStatistics = Field(default_factory=RepositoryStatistics)
    classification_tool: str = "linguist-compatible"
    scanned_at: datetime = Field(default_factory=utc_now)

    @property
    def repository_name(self) -> str:
        return self.repo_name

    @property
    def repository_url(self) -> HttpUrl:
        return self.repo_url


AnalyzeResponse = RepositoryProfile


class InterviewStartRequest(BaseModel):
    repository_url: HttpUrl
    user_id: str | None = None


class InterviewQuestion(BaseModel):
    prompt: str
    focus_area: str
    difficulty: str = "medium"


class InterviewStartResponse(BaseModel):
    session_id: str
    question: InterviewQuestion
    status: str = "in_progress"


class InterviewAnswerRequest(BaseModel):
    session_id: str
    answer: str = Field(min_length=1)


class InterviewAnswerResponse(BaseModel):
    session_id: str
    evaluation: str
    follow_up_question: str | None = None
    next_action: str = "wait_for_gemini"


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
