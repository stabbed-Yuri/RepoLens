import type { PropsWithChildren } from "react";

type MessageFrom = "user" | "assistant" | "feedback" | "system";

type MessageProps = PropsWithChildren<{
  from: MessageFrom;
  label?: string;
}>;

export function Message({ from, label, children }: MessageProps) {
  return (
    <article className={`message message--${from}`}>
      {label ? <p className="message-label">{label}</p> : null}
      {children}
    </article>
  );
}
