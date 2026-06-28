import { FormEvent, useEffect, useRef, useState } from "react";

import { answerInterview, startInterview, stopInterview } from "../api/client";
import { Attachment } from "../components/Attachment";
import { Bubble } from "../components/Bubble";
import { Marker } from "../components/Marker";
import { Message } from "../components/Message";
import { MessageScroller } from "../components/MessageScroller";
import type {
  InterviewAnswerResponse,
  InterviewStartResponse,
  InterviewStopResponse,
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
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  function nextMessageId(): string {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  useEffect(() => {
    const endNode = chatEndRef.current;
    if (endNode && typeof endNode.scrollIntoView === "function") {
      endNode.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages]);

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
          { id: nextMessageId(), role: "user", text: normalizedAnswer },
          { id: nextMessageId(), role: "feedback", text: result.evaluation },
          { id: nextMessageId(), role: "coach", text: result.follow_up_question as string },
        ]);
      } else if (result.next_action === "retry_later") {
        setSessionState("retry_later");
        setMessages((current) => [
          ...current,
          { id: nextMessageId(), role: "user", text: normalizedAnswer },
          { id: nextMessageId(), role: "feedback", text: result.evaluation },
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
          { id: nextMessageId(), role: "user", text: normalizedAnswer },
          { id: nextMessageId(), role: "feedback", text: result.evaluation },
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

  async function onStopInterview() {
    if (!session) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const summary: InterviewStopResponse = await stopInterview({ session_id: session.session_id });
      const scoreLabel =
        summary.score_out_of_10 === null ? "Final score: pending" : `Final score: ${summary.score_out_of_10}/10`;
      const nextStepsText =
        summary.next_steps.length > 0
          ? `\n\nNext steps:\n${summary.next_steps.map((step) => `- ${step}`).join("\n")}`
          : "";
      setMessages((current) => [
        ...current,
        {
          id: nextMessageId(),
          role: "system",
          text: `${scoreLabel}\n${summary.summary}${nextStepsText}`,
        },
      ]);
      setSession(null);
      setSessionState("complete");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Failed to stop interview.",
      );
    } finally {
      setLoading(false);
    }
  }

  function roleToMessageFrom(role: ChatRole): "assistant" | "user" | "feedback" | "system" {
    if (role === "coach") {
      return "assistant";
    }
    if (role === "user") {
      return "user";
    }
    if (role === "feedback") {
      return "feedback";
    }
    return "system";
  }

  function roleToBubbleTone(role: ChatRole): "default" | "primary" | "muted" | "info" {
    if (role === "user") {
      return "primary";
    }
    if (role === "feedback") {
      return "info";
    }
    if (role === "system") {
      return "muted";
    }
    return "default";
  }

  function messageLabel(role: ChatRole): string {
    if (role === "coach") {
      return "Coach";
    }
    if (role === "user") {
      return "You";
    }
    if (role === "feedback") {
      return "Evaluation";
    }
    return "System";
  }

  function extractScore(text: string): string | null {
    const match = text.match(/Score:\s*([0-9]|10)\/10/i);
    return match ? `${match[1]}/10` : null;
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Interview Chat</h2>
          <p className="muted">One question at a time, with immediate evaluation.</p>
        </div>
        <div className="status-stack">
          <p className={`status-chip status-chip--${sessionState}`}>
            {sessionState === "idle" ? "Idle" : null}
            {sessionState === "active" ? "Active" : null}
            {sessionState === "complete" ? "Complete" : null}
            {sessionState === "retry_later" ? "Retry Later" : null}
          </p>
        </div>
      </div>

      <form className="row" onSubmit={onStart}>
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
        <button
          type="button"
          className="ghost"
          onClick={() => void onStopInterview()}
          disabled={loading || !session}
        >
          Stop + Summary
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

      <MessageScroller
        emptyText={messages.length === 0 ? "No messages yet. Start an interview to begin." : undefined}
      >
        <Marker text="Interview Session" />
        {messages.map((message) => (
          <Message
            key={message.id}
            from={roleToMessageFrom(message.role)}
            label={messageLabel(message.role)}
          >
            <Bubble tone={roleToBubbleTone(message.role)}>
              <p className="bubble-text">{message.text}</p>
              {message.role === "feedback" ? (
                <Attachment
                  title="Score"
                  subtitle={extractScore(message.text) ?? "Pending"}
                />
              ) : null}
            </Bubble>
          </Message>
        ))}
        <div ref={chatEndRef} />
      </MessageScroller>

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
