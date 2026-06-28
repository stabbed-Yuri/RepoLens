import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { InterviewPage } from "./InterviewPage";

vi.mock("../api/client", () => ({
  startInterview: vi.fn(),
  answerInterview: vi.fn(),
  stopInterview: vi.fn(),
}));

import { answerInterview, startInterview } from "../api/client";

describe("InterviewPage", () => {
  it("renders chat flow and appends user + feedback messages", async () => {
    vi.mocked(startInterview).mockResolvedValue({
      session_id: "session_1",
      status: "in_progress",
      question: { prompt: "First question?", focus_area: "overview", difficulty: "medium" },
    });
    vi.mocked(answerInterview).mockResolvedValue({
      session_id: "session_1",
      evaluation: "Great answer.",
      score_out_of_10: 8,
      follow_up_question: "Second question?",
      next_action: "continue_interview",
    });

    render(<InterviewPage />);

    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repo"), {
      target: { value: "https://github.com/octocat/demo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start Interview" }));

    await waitFor(() => expect(screen.getByText("First question?")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Type your answer..."), {
      target: { value: "My answer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.getByText("Great answer.")).toBeInTheDocument());
    expect(screen.getByText("My answer")).toBeInTheDocument();
    expect(screen.getByText("Second question?")).toBeInTheDocument();
  });

  it("ends cleanly when no follow-up is returned", async () => {
    vi.mocked(startInterview).mockResolvedValue({
      session_id: "session_2",
      status: "in_progress",
      question: { prompt: "Only question?", focus_area: "overview", difficulty: "medium" },
    });
    vi.mocked(answerInterview).mockResolvedValue({
      session_id: "session_2",
      evaluation: "Complete.",
      score_out_of_10: 7,
      follow_up_question: null,
      next_action: "study_plan_ready",
    });

    render(<InterviewPage />);
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repo"), {
      target: { value: "https://github.com/octocat/demo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start Interview" }));
    await waitFor(() => expect(screen.getByText("Only question?")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Type your answer..."), {
      target: { value: "done" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(screen.getByText(/Interview turn complete. Start another interview/)).toBeInTheDocument(),
    );
  });

  it("shows retry CTA for retry_later responses", async () => {
    vi.mocked(startInterview).mockResolvedValue({
      session_id: "session_3",
      status: "in_progress",
      question: { prompt: "Question?", focus_area: "overview", difficulty: "medium" },
    });
    vi.mocked(answerInterview).mockResolvedValue({
      session_id: "session_3",
      evaluation: "Provider busy.",
      score_out_of_10: null,
      follow_up_question: "Retry soon.",
      next_action: "retry_later",
    });

    render(<InterviewPage />);
    fireEvent.change(screen.getByPlaceholderText("https://github.com/owner/repo"), {
      target: { value: "https://github.com/octocat/demo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Start Interview" }));
    await waitFor(() => expect(screen.getByText("Question?")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText("Type your answer..."), {
      target: { value: "ans" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Retry Last Turn" })).toBeInTheDocument());
  });
});
