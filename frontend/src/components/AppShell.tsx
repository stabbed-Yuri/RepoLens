import type { PropsWithChildren } from "react";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <main className="app-shell">
      <div className="app-shell__inner">{children}</div>
    </main>
  );
}

