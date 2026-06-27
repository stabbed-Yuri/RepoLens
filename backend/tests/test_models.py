import unittest

from backend.app.models.interview import InterviewSession, InterviewStatus, StudyPlan
from backend.app.models.repository import RepositoryProfile


class ModelRoundTripTests(unittest.TestCase):
    def test_repository_profile_round_trip(self) -> None:
        profile = RepositoryProfile(
            repository_url="https://github.com/octocat/Hello-World",
            repository_name="Hello-World",
            owner="octocat",
            default_branch="main",
            short_summary="Compact repository profile placeholder.",
            architecture_notes=["API and frontend live in separate top-level directories."],
            key_technologies=["FastAPI", "React"],
            interview_focus_areas=["architecture", "tooling"],
        )

        payload = profile.model_dump(mode="json")
        reloaded = RepositoryProfile.model_validate(payload)

        self.assertEqual(reloaded.repository_name, "Hello-World")
        self.assertEqual(reloaded.owner, "octocat")
        self.assertEqual(reloaded.classification_tool, "github-linguist")

    def test_interview_session_round_trip(self) -> None:
        session = InterviewSession(
            session_id="session_demo_001",
            repository_url="https://github.com/octocat/Hello-World",
            user_id="user_123",
            status=InterviewStatus.IN_PROGRESS,
        )

        payload = session.model_dump(mode="json")
        reloaded = InterviewSession.model_validate(payload)

        self.assertEqual(reloaded.session_id, "session_demo_001")
        self.assertEqual(reloaded.status, InterviewStatus.IN_PROGRESS)
        self.assertIsNone(reloaded.study_plan)

    def test_study_plan_score_is_optional(self) -> None:
        study_plan = StudyPlan(summary="Keep practicing concise architecture explanations.")
        payload = study_plan.model_dump(mode="json")
        reloaded = StudyPlan.model_validate(payload)

        self.assertIsNone(reloaded.overall_score)


if __name__ == "__main__":
    unittest.main()

