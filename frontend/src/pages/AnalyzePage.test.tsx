import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AnalyzePage } from "./AnalyzePage";

vi.mock("../api/client", () => ({
  analyzeRepository: vi.fn(),
  buildKnowledgePack: vi.fn(),
}));

import { analyzeRepository, buildKnowledgePack } from "../api/client";

describe("AnalyzePage", () => {
  it("renders profile and knowledge pack summary on success", async () => {
    vi.mocked(analyzeRepository).mockResolvedValue({
      repo_name: "demo",
      repo_url: "https://github.com/octocat/demo",
      primary_language: "TypeScript",
      language_breakdown: { TypeScript: 1 },
      frameworks: ["react"],
      dependencies: [],
      entry_points: ["src/main.tsx"],
      folder_tree: ["README.md", "src/main.tsx"],
      readme_text: "# demo",
      important_files: ["README.md"],
      test_files: [],
      config_files: ["package.json"],
      documentation_files: ["README.md"],
      feature_signals: [],
      statistics: {
        file_count: 2,
        directory_count: 1,
        binary_file_count: 0,
        generated_file_count: 0,
        vendored_file_count: 0,
        documentation_file_count: 1,
        config_file_count: 1,
        test_file_count: 0,
        entry_point_count: 1,
        dependency_manifest_count: 1,
      },
      classification_tool: "linguist-compatible",
      repo_type_summary: "TypeScript repository with react",
      scanned_at: "2026-06-28T00:00:00Z",
    });
    vi.mocked(buildKnowledgePack).mockResolvedValue({
      repo_name: "demo",
      repo_url: "https://github.com/octocat/demo",
      repo_sha: "abc123",
      profile: {} as never,
      key_chunks: [
        {
          chunk_id: "demo:1",
          source_path: "src/main.tsx",
          chunk_type: "source",
          start_line: 1,
          end_line: 10,
          text_excerpt: "x",
        },
      ],
      topic_hits: {},
      stats: { chunk_count: 1, embedded_chunk_count: 1, embedding_dimensions: 1536 },
      generated_at: "2026-06-28T00:00:00Z",
    });

    render(<AnalyzePage onUseForInterview={() => undefined} />);

    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repo"), {
      target: { value: "https://github.com/octocat/demo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));

    await waitFor(() => expect(screen.getByText("demo")).toBeInTheDocument());
    expect(screen.getByText(/TypeScript repository with react/)).toBeInTheDocument();
    expect(screen.getByText(/SHA: abc123/)).toBeInTheDocument();
  });

  it("shows error state when API call fails", async () => {
    vi.mocked(analyzeRepository).mockRejectedValue(new Error("boom"));
    vi.mocked(buildKnowledgePack).mockRejectedValue(new Error("boom"));

    render(<AnalyzePage onUseForInterview={() => undefined} />);
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repo"), {
      target: { value: "https://github.com/octocat/demo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Analyze" }));

    await waitFor(() =>
      expect(screen.getByText(/Failed to analyze repository|boom/)).toBeInTheDocument(),
    );
  });
});
