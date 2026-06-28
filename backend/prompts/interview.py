from __future__ import annotations

from backend.models import KnowledgePack, KnowledgePackChunk


SYSTEM_PROMPT = """
You are RepoLens, a senior technical interviewer and interview coach.

Your task is to understand what kind of project this repository is before asking questions.
Do not assume the repository is a Python app, web app, API, or library.

Infer the project type from repository summary, README, manifests, config files, entry points,
test files, documentation, important filenames/extensions, feature signals, and retrieved context.

General behavior:
- Ask exactly one concise question at a time.
- Make the question relevant to the general idea of the project, not just its programming language.
- Never reveal the answer before the candidate responds.
- Never repeat a previously asked question or follow-up.
- Do not ask generic trivia unless it directly relates to the repository.
- Use only repository context provided by the application as source of truth.
- Cover different parts of the project instead of staying on one topic too long.
- Start with one broad project architecture or purpose question, then move into deeper implementation,
  testing, deployment, schema, or failure-mode questions in later turns.

Project-type guidance:
- Reporting projects: ask about data sources, report definitions, datasets, schema changes, maintainability, or deployment.
- API services: ask about route design, validation, persistence, errors, testing, or deployment.
- Frontend apps: ask about state flow, component boundaries, API integration, accessibility, or build/deploy choices.
- Libraries: ask about public API design, compatibility, error handling, tests, or versioning.
- Infrastructure/config repos: ask about environments, secrets, reproducibility, rollout, or failure modes.

When evaluating answers:
- Compare the answer with repository context and prior Q/A history.
- Reward design reasoning, concrete artifacts, and trade-off awareness.
- Keep feedback concise, constructive, and actionable.
- Choose a non-repeating follow-up that deepens the topic or moves to a valuable uncovered area.
"""


def build_start_question_prompt(pack: KnowledgePack) -> str:
    top_paths = [chunk.source_path for chunk in pack.key_chunks[:10]]
    test_paths = pack.profile.test_files[:8]
    config_paths = pack.profile.config_files[:8]
    feature_signals = pack.profile.feature_signals[:8]
    evidence = _format_context_chunks(_select_prompt_context_chunks(pack, max_chunks=8))
    return (
        "Generate exactly one interview question for this repository.\n"
        "Output only the question text.\n\n"
        "Rules:\n"
        "- First infer the project type and purpose from the context.\n"
        "- This is the first question, so ask about the project's overall architecture, purpose, or how multiple core artifacts work together.\n"
        "- The first question must not focus on one helper function, auth token detail, schema edge case, or deployment setting.\n"
        "- For web apps, the first question should connect at least two of: components, routes, state management, API boundary, user flow.\n"
        "- For reporting projects, the first question should connect report definitions, data sources, datasets, and report purpose.\n"
        "- Save narrow schema, deployment, and failure-mode questions for later follow-ups.\n"
        "- Avoid language-only questions unless language choice is central to this repository.\n"
        "- Avoid generic questions like 'What is the purpose of this repository?'\n"
        "- Anchor the question to a concrete file, module, artifact, or project concept from context.\n"
        "- Prefer high-signal files over dotfiles, generated files, or assets.\n"
        "- Keep it concise (max 24 words) and end with '?'.\n\n"
        f"Repo: {pack.repo_name}\n"
        f"Project type: {pack.profile.project_type or 'unknown'}\n"
        f"Project purpose: {pack.profile.project_purpose or 'unknown'}\n"
        f"Primary language: {pack.profile.primary_language}\n"
        f"Repo type summary: {pack.profile.repo_type_summary or 'unknown'}\n"
        f"Frameworks: {', '.join(pack.profile.frameworks[:8]) or 'unknown'}\n"
        f"Interview focus areas: {', '.join(pack.profile.interview_focus_areas[:8]) or 'unknown'}\n"
        f"Entry points: {', '.join(pack.profile.entry_points[:8]) or 'unknown'}\n"
        f"Test files: {', '.join(test_paths) or 'unknown'}\n"
        f"Config files: {', '.join(config_paths) or 'unknown'}\n"
        f"Feature signals: {', '.join(feature_signals) or 'unknown'}\n"
        f"Important files: {', '.join(top_paths) or 'unknown'}\n"
        f"Retrieved evidence from diverse repository chunks:\n{evidence or 'none'}\n"
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
    turn_history: list[dict[str, str]],
    recent_questions: list[str],
    turns_completed: int,
    max_turns: int,
) -> str:
    supporting_chunks = _format_context_chunks(_select_prompt_context_chunks(pack, max_chunks=10))
    candidate_topics = [
        *pack.profile.interview_focus_areas[:8],
        f"architecture ({pack.profile.entry_points[0]})" if pack.profile.entry_points else "architecture",
        "testing strategy" if pack.profile.test_files else "quality and validation",
        "configuration/runtime risks" if pack.profile.config_files else "configuration",
    ]
    serialized_history = "\n".join(
        (
            f"Turn {index + 1}\n"
            f"Q: {turn.get('question', '')}\n"
            f"A: {turn.get('answer', '')}\n"
            f"Eval: {turn.get('evaluation', '')}\n"
        )
        for index, turn in enumerate(turn_history[-5:])
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
        "- Use prior turns to avoid repeating question wording or already-covered topic angles.\n"
        "- Identify covered topics from prior turns before choosing the next question.\n"
        "- follow_up_question should either deepen the current topic or move to the next highest-value uncovered topic.\n"
        "- Prefer uncovered topics from candidate_topics when current topic is already strong.\n"
        "- Never repeat the current or recent questions.\n"
        "- If turns_completed >= max_turns - 1, set follow_up_question to empty string.\n\n"
        f"Project type: {pack.profile.project_type or 'unknown'}\n"
        f"Project purpose: {pack.profile.project_purpose or 'unknown'}\n"
        f"Repo type summary: {pack.profile.repo_type_summary or 'unknown'}\n"
        f"turns_completed: {turns_completed}\n"
        f"max_turns: {max_turns}\n"
        f"recent_questions: {recent_questions[-4:]}\n"
        f"candidate_topics: {candidate_topics}\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        f"Prior turns:\n{serialized_history or 'No prior turns.'}\n\n"
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


def _select_prompt_context_chunks(pack: KnowledgePack, max_chunks: int) -> list[KnowledgePackChunk]:
    """Pick compact, diverse evidence without sending the whole repository."""
    selected: list[KnowledgePackChunk] = []
    seen_paths: set[str] = set()

    candidates: list[KnowledgePackChunk] = list(pack.key_chunks[: max_chunks * 2])
    for hits in pack.topic_hits.values():
        candidates.extend(hit.chunk for hit in hits[:2])

    for chunk in candidates:
        path_key = chunk.source_path.lower()
        if path_key in seen_paths:
            continue
        selected.append(chunk)
        seen_paths.add(path_key)
        if len(selected) >= max_chunks:
            break

    if len(selected) < max_chunks:
        seen_chunk_ids = {chunk.chunk_id for chunk in selected}
        for chunk in candidates:
            if chunk.chunk_id in seen_chunk_ids:
                continue
            selected.append(chunk)
            seen_chunk_ids.add(chunk.chunk_id)
            if len(selected) >= max_chunks:
                break

    return selected


def _format_context_chunks(chunks: list[KnowledgePackChunk]) -> str:
    return "\n\n".join(
        f"[{chunk.source_path}:{chunk.start_line}-{chunk.end_line}]\n{chunk.text_excerpt[:500]}"
        for chunk in chunks
    )
