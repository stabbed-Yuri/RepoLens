import type { PropsWithChildren } from "react";

type MessageScrollerProps = PropsWithChildren<{
  emptyText?: string;
}>;

export function MessageScroller({ children, emptyText }: MessageScrollerProps) {
  return (
    <section className="message-scroller" role="log" aria-live="polite">
      {emptyText ? <p className="muted">{emptyText}</p> : null}
      {children}
    </section>
  );
}
