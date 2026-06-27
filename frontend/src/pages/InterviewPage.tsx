import { FormEvent, useState } from "react";

import { answerInterview, startInterview } from "../api/client";
import type {
  InterviewAnswerResponse,
  InterviewStartResponse,
} from "../types/contracts";

type InterviewPageProps = {
  initialRepositoryUrl?: string;
};

type ChatRole = "coach" | "user" | "feedback" | "system";
type SessionState = "idle" | "active" | "complete" | "retry_later";

type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
};

export function InterviewPage({ initialRepositoryUrl = "" }: InterviewPageProps) {
  const [repositoryUrl, setRepositoryUrl] = useState(initialRepositoryUrl);
  const [session, setSession] = useState<InterviewStartResponse | null>(null);
  const [sessionState, setSessionState] = useState<SessionState>("idle");
  const [answer, setAnswer] = useState("");
  const [lastSubmittedAnswer, setLastSubmittedAnswer] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function nextMessageId(): string {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  async function onStart(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setMessages([]);
    setAnswer("");
    setLastSubmittedAnswer("");
    setSessionState("idle");

    try {
      const nextSession = await startInterview({
        repository_url: repositoryUrl.trim(),
      });
      setSession(nextSession);
      setSessionState("active");
      setMessages([
        {
          id: nextMessageId(),
          role: "coach",
          text: nextSession.question.prompt,
        },
      ]);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to start interview.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function submitAnswerText(text: string): Promise<void> {
    if (!session || !text.trim()) {
      return;
    }
    setLoading(true);
    setError(null);
    const normalizedAnswer = text.trim();
    setLastSubmittedAnswer(normalizedAnswer);

    try {
      const result: InterviewAnswerResponse = await answerInterview({
        session_id: session.session_id,
        answer: normalizedAnswer,
      });
      setMessages((current) => [
        ...current,
        { id: nextMessageId(), role: "user", text: normalizedAnswer },
        { id: nextMessageId(), role: "feedback", text: result.evaluation },
      ]);

      if (result.next_action === "continue_interview" && result.follow_up_question) {
        setSession((current) =>
          current
            ? {
                ...current,
                question: { ...current.question, prompt: result.follow_up_question as string },
              }
            : current,
        );
        setSessionState("active");
        setMessages((current) => [
          ...current,
          { id: nextMessageId(), role: "coach", text: result.follow_up_question as string },
        ]);
      } else if (result.next_action === "retry_later") {
        setSessionState("retry_later");
        setMessages((current) => [
          ...current,
          {
            id: nextMessageId(),
            role: "system",
            text: "Provider unavailable. Wait a bit, then use Retry Last Turn.",
          },
        ]);
      } else {
        setSessionState("complete");
        setMessages((current) => [
          ...current,
          {
            id: nextMessageId(),
            role: "system",
            text: "Interview turn complete. Start another interview to continue.",
          },
        ]);
        setSession(null);
      }
      setAnswer("");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to submit answer.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function onSubmitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitAnswerText(answer);
  }

  async function onRetryLastTurn() {
    if (!lastSubmittedAnswer) {
      return;
    }
    await submitAnswerText(lastSubmittedAnswer);
  }

  return (
    <section className="panel">
      <h1>Interview</h1>
      <p className="muted">Start a live repository-specific interview and answer in chat.</p>

      <form className="stack" onSubmit={onStart}>
        <input
          type="url"
          required
          placeholder="https://github.com/owner/repo"
          value={repositoryUrl}
          onChange={(event) => setRepositoryUrl(event.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Starting..." : "Start Interview"}
        </button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      {sessionState === "retry_later" ? (
        <div className="row">
          <button type="button" className="ghost" onClick={() => void onRetryLastTurn()} disabled={loading}>
            Retry Last Turn
          </button>
        </div>
      ) : null}

      <section className="chat-thread">
        {messages.length === 0 ? (
          <p className="muted">No messages yet. Start an interview to begin.</p>
        ) : null}
        {messages.map((message) => (
          <article key={message.id} className={`chat-bubble chat-bubble--${message.role}`}>
            <p>{message.text}</p>
          </article>
        ))}
      </section>

      <form className="chat-composer" onSubmit={onSubmitAnswer}>
        <textarea
          rows={4}
          placeholder={session ? "Type your answer..." : "Start a session first to unlock the chat input."}
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          disabled={!session}
        />
        <button type="submit" disabled={loading || !answer.trim() || !session}>
          {loading ? "Evaluating..." : "Send"}
        </button>
      </form>
    </section>
  );
}
