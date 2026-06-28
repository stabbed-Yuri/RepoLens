import type { PropsWithChildren } from "react";

type BubbleProps = PropsWithChildren<{
  tone?: "default" | "primary" | "muted" | "info";
}>;

export function Bubble({ tone = "default", children }: BubbleProps) {
  return <div className={`bubble bubble--${tone}`}>{children}</div>;
}
