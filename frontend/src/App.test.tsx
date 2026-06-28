import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import App from "./App"
import { api } from "@/lib/api"
import type { KnowledgePack } from "@/types"

vi.mock("@/lib/api", () => ({
  api: {
    analyzeKnowledgePack: vi.fn(),
    interviewStart: vi.fn(),
    interviewAnswer: vi.fn(),
    interviewStop: vi.fn(),
  },
}))

function makeKnowledgePack(): KnowledgePack {
  return {
    repo_name: "demo",
    repo_url: "https://github.com/octocat/demo",
    repo_sha: "abc123",
    profile: {
      repo_name: "demo",
      repo_url: "https://github.com/octocat/demo",
      primary_language: "TypeScript",
      language_breakdown: { TypeScript: 1 },
      frameworks: ["react"],
      dependencies: [
        {
          path: "package.json",
          manifest_type: "package.json",
          package_manager: "npm",
          dependencies: ["react"],
          dev_dependencies: ["vite"],
          framework_hints: ["react", "vite"],
        },
      ],
      entry_points: ["src/main.tsx"],
      folder_tree: ["README.md", "src/main.tsx"],
      readme_text: "# demo",
      important_files: ["README.md", "src/main.tsx"],
      test_files: ["src/App.test.tsx"],
      config_files: ["package.json", "vite.config.ts"],
      documentation_files: ["README.md"],
      feature_signals: ["project-type:web-app", "tests-present"],
      statistics: {
        file_count: 4,
        directory_count: 1,
        binary_file_count: 0,
        generated_file_count: 0,
        vendored_file_count: 0,
        documentation_file_count: 1,
        config_file_count: 2,
        test_file_count: 1,
        entry_point_count: 1,
        dependency_manifest_count: 1,
      },
      classification_tool: "test",
      project_type: "web-app",
      project_purpose: "Delivers an interactive browser-based user experience.",
      interview_focus_areas: ["state flow", "API integration"],
      repo_type_summary: "Web App repository using react",
      scanned_at: "2026-06-28T00:00:00Z",
    },
    key_chunks: [
      {
        chunk_id: "demo:1",
        source_path: "src/main.tsx",
        chunk_type: "source",
        start_line: 1,
        end_line: 5,
        text_excerpt: "createRoot(document.getElementById('root'))",
      },
    ],
    topic_hits: {
      architecture: [
        {
          score: 0.87,
          chunk: {
            chunk_id: "demo:1",
            source_path: "src/main.tsx",
            chunk_type: "source",
            start_line: 1,
            end_line: 5,
            text_excerpt: "createRoot(document.getElementById('root'))",
          },
        },
      ],
    },
    stats: { chunk_count: 1, embedded_chunk_count: 1, embedding_dimensions: 256 },
    provider_used: "openai",
    fallback_used: false,
    fallback_reason: null,
    generated_at: "2026-06-28T00:00:00Z",
  }
}

function makeFallbackKnowledgePack(): KnowledgePack {
  return {
    ...makeKnowledgePack(),
    provider_used: "openai",
    fallback_used: true,
    fallback_reason: "gemini quota or rate limit reached",
  }
}

describe("App", () => {
  it("renders the pitch-ready landing screen", () => {
    render(<App />)

    expect(screen.getByText(/Turn any GitHub repository/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText("https://github.com/owner/repository")).toBeInTheDocument()
    expect(screen.getByText(/Demo repos/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /React web app/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Python framework/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Low-signal repo/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /OpenAI current/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Gemini 3.1 Flash Lite/i })).toBeInTheDocument()
  })

  it("starts analysis when a demo repo is clicked", async () => {
    vi.mocked(api.analyzeKnowledgePack).mockResolvedValue(makeKnowledgePack())

    render(<App />)
    fireEvent.click(screen.getByRole("button", { name: /React web app/i }))

    await waitFor(() =>
      expect(api.analyzeKnowledgePack).toHaveBeenCalledWith(
        "https://github.com/gothinkster/react-redux-realworld-example-app",
        "openai",
      ),
    )
  })

  it("sends the selected Gemini provider to analyze and interview start", async () => {
    vi.mocked(api.analyzeKnowledgePack).mockResolvedValue(makeKnowledgePack())
    vi.mocked(api.interviewStart).mockResolvedValue({
      session_id: "session_gemini",
      status: "in_progress",
      question: {
        prompt: "How does the app fit together?",
        focus_area: "architecture",
        difficulty: "medium",
      },
      provider_used: "gemini",
      fallback_used: false,
      fallback_reason: null,
    })

    render(<App />)
    fireEvent.click(screen.getByRole("button", { name: /Gemini 3.1 Flash Lite/i }))
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repository"), {
      target: { value: "https://github.com/octocat/demo" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }))
    await waitFor(() => expect(screen.getByText("demo")).toBeInTheDocument())
    fireEvent.click(screen.getAllByRole("button", { name: /Start Interview/i })[0])

    await waitFor(() =>
      expect(api.analyzeKnowledgePack).toHaveBeenCalledWith(
        "https://github.com/octocat/demo",
        "gemini",
      ),
    )
    expect(api.interviewStart).toHaveBeenCalledWith("https://github.com/octocat/demo", "gemini")
  })

  it("analyzes a repository and renders actionable analysis sections", async () => {
    vi.mocked(api.analyzeKnowledgePack).mockResolvedValue(makeKnowledgePack())

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repository"), {
      target: { value: "https://github.com/octocat/demo" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }))

    await waitFor(() => expect(screen.getByText("demo")).toBeInTheDocument())
    expect(screen.getByText(/Dependency Signals/i)).toBeInTheDocument()
    expect(screen.getByText(/Interview Risk Checks/i)).toBeInTheDocument()
    expect(screen.getByText(/Suggested Interview Themes/i)).toBeInTheDocument()
    expect(screen.getByText(/Limited repository signal found/i)).toBeInTheDocument()
  })

  it("renders provider fallback notice from analyze metadata", async () => {
    vi.mocked(api.analyzeKnowledgePack).mockResolvedValue(makeFallbackKnowledgePack())

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repository"), {
      target: { value: "https://github.com/octocat/demo" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }))

    await waitFor(() => expect(screen.getByText(/gemini quota or rate limit reached/i)).toBeInTheDocument())
    expect(screen.getByText(/continued with/i)).toBeInTheDocument()
  })

  it("starts, answers, follows up, and stops an interview", async () => {
    vi.mocked(api.analyzeKnowledgePack).mockResolvedValue(makeKnowledgePack())
    vi.mocked(api.interviewStart).mockResolvedValue({
      session_id: "session_1",
      status: "in_progress",
      question: {
        prompt: "How does src/main.tsx shape the app startup flow?",
        focus_area: "architecture",
        difficulty: "medium",
      },
      provider_used: "openai",
      fallback_used: false,
      fallback_reason: null,
    })
    vi.mocked(api.interviewAnswer).mockResolvedValue({
      session_id: "session_1",
      evaluation: "Score: 8/10\n- Good artifact-specific explanation.\n- Add deployment trade-offs.",
      score_out_of_10: 8,
      follow_up_question: "What API integration risk would you test next?",
      next_action: "continue_interview",
      provider_used: "openai",
      fallback_used: false,
      fallback_reason: null,
    })
    vi.mocked(api.interviewStop).mockResolvedValue({
      session_id: "session_1",
      summary: "- Strong repository understanding\n- Needs deployment detail",
      score_out_of_10: 8,
      next_steps: ["Practice API integration risks", "Cite exact files"],
      provider_used: "openai",
      fallback_used: false,
      fallback_reason: null,
    })

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repository"), {
      target: { value: "https://github.com/octocat/demo" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }))
    await waitFor(() => expect(screen.getByText("demo")).toBeInTheDocument())
    fireEvent.click(screen.getAllByRole("button", { name: /Start Interview/i })[0])

    await waitFor(() => expect(screen.getByText(/app startup flow/i)).toBeInTheDocument())
    const answerInput = screen.getByPlaceholderText(/Type your answer/i)
    fireEvent.change(answerInput, {
      target: { value: "It mounts the root React app." },
    })
    fireEvent.keyDown(answerInput, { key: "Enter", code: "Enter" })

    await waitFor(() => expect(screen.getByText(/Good artifact-specific explanation/i)).toBeInTheDocument())
    expect(screen.getByText(/API integration risk/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Stop/i }))
    await waitFor(() => expect(screen.getAllByText(/Interview Complete/i).length).toBeGreaterThan(0))
    expect(screen.getByText(/Strong repository understanding/i)).toBeInTheDocument()
    expect(screen.getByText(/Practice API integration risks/i)).toBeInTheDocument()
  })

  it("returns to analysis after stopping before answering", async () => {
    vi.mocked(api.analyzeKnowledgePack).mockResolvedValue(makeKnowledgePack())
    vi.mocked(api.interviewStart).mockResolvedValue({
      session_id: "session_empty",
      status: "in_progress",
      question: {
        prompt: "How does src/main.tsx shape the app startup flow?",
        focus_area: "architecture",
        difficulty: "medium",
      },
      provider_used: "openai",
      fallback_used: false,
      fallback_reason: null,
    })
    vi.mocked(api.interviewStop).mockResolvedValue({
      session_id: "session_empty",
      summary: "Interview ended before any answer was submitted.",
      score_out_of_10: null,
      next_steps: ["Start again and answer at least one question."],
      provider_used: "openai",
      fallback_used: false,
      fallback_reason: null,
    })

    render(<App />)
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repository"), {
      target: { value: "https://github.com/octocat/demo" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Analyze Repository/i }))
    await waitFor(() => expect(screen.getByText("demo")).toBeInTheDocument())
    fireEvent.click(screen.getAllByRole("button", { name: /Start Interview/i })[0])

    await waitFor(() => expect(screen.getByText(/app startup flow/i)).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: /Stop/i }))

    await waitFor(() => expect(screen.getByText(/Interview ended before any answer/i)).toBeInTheDocument())
    fireEvent.click(screen.getByRole("button", { name: /Back to analysis/i }))

    await waitFor(() => expect(screen.getByText("demo")).toBeInTheDocument())
    expect(screen.getAllByRole("button", { name: /Start Interview/i }).length).toBeGreaterThan(0)
  })
})
