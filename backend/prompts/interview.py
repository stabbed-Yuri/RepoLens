from __future__ import annotations

from backend.models import KnowledgePack


SYSTEM_PROMPT = (
    "You are RepoLens, an interview coach. Ask concise, repository-specific technical "
    "questions and provide actionable answer feedback."
)


def build_start_question_prompt(pack: KnowledgePack) -> str:
    top_paths = [chunk.source_path for chunk in pack.key_chunks[:10]]
    return (
        "Generate exactly one interview question for this repository.\n"
        "Output only the question text.\n\n"
        f"Repo: {pack.repo_name}\n"
        f"Primary language: {pack.profile.primary_language}\n"
        f"Frameworks: {', '.join(pack.profile.frameworks[:8]) or 'unknown'}\n"
        f"Entry points: {', '.join(pack.profile.entry_points[:8]) or 'unknown'}\n"
        f"Important files: {', '.join(top_paths) or 'unknown'}\n"
    )


def build_answer_evaluation_prompt(
    *,
    pack: KnowledgePack,
    question: str,
    answer: str,
) -> str:
    supporting_chunks = "\n\n".join(
        f"[{chunk.source_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.text_excerpt}"
        for chunk in pack.key_chunks[:6]
    )
    return (
        "Evaluate the candidate answer to the interview question using the repository context.\n"
        "Return valid JSON only with keys: evaluation, follow_up_question.\n"
        "Keep evaluation under 120 words and make it constructive.\n\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        "Repository context excerpts:\n"
        f"{supporting_chunks}"
    )
