# Prompt Inventory

This file tracks the prompt shapes planned for the RepoLens MVP. The prompts remain compact and modular so they can be loaded by dedicated backend prompt utilities later.

## Repository Understanding

Purpose: Convert a compact `RepositoryProfile` into a concise explanation of the project, its architecture, and likely interview focus areas.

Prompt outline:

- Input: compact repository profile only
- Goals:
  - summarize the project in plain language
  - identify key architecture concepts
  - identify high-signal interview topics
- Constraints:
  - do not invent files or modules not present in the profile
  - keep output concise and structured

## Question Generation

Purpose: Generate the next best interview question from the repository profile and prior turns.

Prompt outline:

- Inputs:
  - repository profile
  - prior interview turns
  - current focus area
- Goals:
  - ask one question at a time
  - adapt difficulty to the prior answer quality
  - prioritize repository-specific questions over generic trivia

## Answer Evaluation

Purpose: Evaluate the candidate answer with strengths, gaps, and an overall summary.

Prompt outline:

- Inputs:
  - repository profile
  - current question
  - user answer
- Goals:
  - identify what was correct
  - identify what was missing or vague
  - keep the evaluation constructive and actionable

## Follow-Up Generation

Purpose: Decide whether a follow-up question is necessary and, if so, generate a focused follow-up.

Prompt outline:

- Inputs:
  - repository profile
  - current turn
  - evaluation summary
- Goals:
  - ask for clarification only when it will improve signal
  - avoid repetitive or redundant follow-ups

## Study Plan Generation

Purpose: Produce a short, practical study plan from the session transcript and evaluation history.

Prompt outline:

- Inputs:
  - repository profile
  - interview turns
  - evaluation summaries
- Goals:
  - prioritize the highest-value learning gaps
  - recommend concrete practice actions
  - keep the plan concise enough for an MVP report

