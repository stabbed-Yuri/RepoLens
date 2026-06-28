from __future__ import annotations

from backend.models import KnowledgePack


SYSTEM_PROMPT = """
You are RepoLens, an AI technical interviewer and interview coach.

Your goal is to help developers prepare for technical interviews using their own GitHub repositories.

You are conducting a realistic technical interview, not a quiz.

General behavior:
- Ask exactly ONE question at a time.
- Keep questions concise and conversational.
- Never reveal the answer before the candidate responds.
- Never repeat a previously asked question or follow-up.
- Do not ask generic programming trivia unless it directly relates to the repository.
- Base every question on the repository's architecture, implementation, design decisions, technologies, or trade-offs.
- Adapt the interview based on previous answers.
- If the candidate demonstrates strong understanding, increase the difficulty.
- If they struggle, ask a simpler follow-up before moving on.
- Cover different parts of the project instead of staying on one topic too long.
- Simulate the style of a senior software engineer conducting a real technical interview.

When evaluating answers:
- Compare the answer with the repository context.
- Reward understanding of design decisions, not memorized definitions.
- Explain what was answered well.
- Explain what important concepts were missing.
- Keep feedback constructive and actionable.
- Do not invent repository details that are not supported by the provided context.

Interview priorities:
1. Project architecture
2. Feature implementation
3. Design decisions
4. Code quality
5. Security
6. Performance
7. Testing
8. Deployment
9. Scalability
10. Future improvements

Always use the repository context provided by the application as the source of truth.
"""


def build_start_question_prompt(pack: KnowledgePack) -> str:
    top_paths = [chunk.source_path for chunk in pack.key_chunks[:10]]
    test_paths = pack.profile.test_files[:8]
    config_paths = pack.profile.config_files[:8]
    feature_signals = pack.profile.feature_signals[:8]
    return (
        "Generate exactly one interview question for this repository.\n"
        "Output only the question text.\n\n"
        "Rules:\n"
        "- Ask about architecture, module responsibilities, design trade-offs, testing strategy, or configuration risk.\n"
        "- Avoid generic questions like 'What is the purpose of this repository?'\n"
        "- Anchor the question to one concrete file/module/path from context.\n"
        "- Prefer high-signal files (entry points, tests, config, core source) over dotfiles.\n"
        "- Keep it concise (max 24 words) and end with '?'.\n\n"
        f"Repo: {pack.repo_name}\n"
        f"Primary language: {pack.profile.primary_language}\n"
        f"Repo type summary: {pack.profile.repo_type_summary or 'unknown'}\n"
        f"Frameworks: {', '.join(pack.profile.frameworks[:8]) or 'unknown'}\n"
        f"Entry points: {', '.join(pack.profile.entry_points[:8]) or 'unknown'}\n"
        f"Test files: {', '.join(test_paths) or 'unknown'}\n"
        f"Config files: {', '.join(config_paths) or 'unknown'}\n"
        f"Feature signals: {', '.join(feature_signals) or 'unknown'}\n"
        f"Important files: {', '.join(top_paths) or 'unknown'}\n"
    )


def build_start_question_retry_prompt(pack: KnowledgePack) -> str:
    return (
        build_start_question_prompt(pack)
        + "\nReturn one complete sentence ending with '?'. No markdown, no code fences."
    )


def build_answer_evaluation_prompt(
    *,
    pack: KnowledgePack,
    question: str,
    answer: str,
    recent_questions: list[str],
    turns_completed: int,
    max_turns: int,
) -> str:
    supporting_chunks = "\n\n".join(
        f"[{chunk.source_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.text_excerpt}"
        for chunk in pack.key_chunks[:6]
    )
    return (
        "Evaluate the candidate answer to the interview question using the repository context.\n"
        "Return valid JSON only with keys: score_out_of_10, evaluation_bullets, follow_up_question.\n"
        "Scoring rubric:\n"
        "- Repository correctness and technical accuracy (0-4)\n"
        "- Specificity using concrete files/modules (0-3)\n"
        "- Reasoning and trade-off awareness (0-2)\n"
        "- Clarity and concision (0-1)\n"
        "Rules:\n"
        "- score_out_of_10 must be an integer 0..10.\n"
        "- evaluation_bullets must contain 2-4 concise bullets, each under 16 words.\n"
        "- At least one bullet must reference a concrete repository artifact (file/module/test/config).\n"
        "- follow_up_question must be one concise question or empty string.\n"
        "- follow_up_question should deepen the same topic, not switch randomly.\n"
        "- Never repeat the current or recent questions.\n"
        "- If turns_completed >= max_turns - 1, set follow_up_question to empty string.\n\n"
        f"turns_completed: {turns_completed}\n"
        f"max_turns: {max_turns}\n"
        f"recent_questions: {recent_questions[-4:]}\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        "Repository context excerpts:\n"
        f"{supporting_chunks}"
    )


def build_answer_repair_prompt(raw_output: str) -> str:
    return (
        "Rewrite the following model output into valid JSON with keys "
        '"score_out_of_10", "evaluation_bullets", and "follow_up_question".\n'
        "Set score_out_of_10 to an integer in 0..10.\n"
        "Set evaluation_bullets to 2-4 concise bullet strings.\n"
        "If follow_up_question is not present, set it to an empty string.\n"
        "Return JSON only.\n\n"
        f"Output to repair:\n{raw_output}"
    )


def build_summary_repair_prompt(raw_output: str) -> str:
    return (
        "Rewrite the following model output into valid JSON with keys "
        '"score_out_of_10", "summary_bullets", and "next_steps".\n'
        "Set score_out_of_10 to an integer in 0..10.\n"
        "Set summary_bullets to 3-5 concise bullet strings.\n"
        "Set next_steps to 2-4 concise bullet strings.\n"
        "Return JSON only.\n\n"
        f"Output to repair:\n{raw_output}"
    )


def build_interview_summary_prompt(*, pack: KnowledgePack, history: list[dict[str, str]]) -> str:
    serialized_history = "\n".join(
        (
            f"Turn {index + 1}\n"
            f"Q: {turn.get('question', '')}\n"
            f"A: {turn.get('answer', '')}\n"
            f"Eval: {turn.get('evaluation', '')}\n"
        )
        for index, turn in enumerate(history[-8:])
    )
    return (
        "Create a concise overall interview summary.\n"
        "Return valid JSON only with keys: score_out_of_10, summary_bullets, next_steps.\n"
        "Rules:\n"
        "- score_out_of_10 must be integer 0..10.\n"
        "- summary_bullets: 3-5 bullets, each under 16 words.\n"
        "- next_steps: 2-4 practical action bullets, each under 16 words.\n\n"
        f"Repository: {pack.repo_name}\n"
        f"Primary language: {pack.profile.primary_language}\n"
        f"Frameworks: {', '.join(pack.profile.frameworks[:8]) or 'unknown'}\n"
        f"Interview history:\n{serialized_history or 'No turns available.'}"
    )
