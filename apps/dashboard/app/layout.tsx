import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "IntentFence",
  description: "Runtime authorization for autonomous AI agents",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body data-intentfence-release="phase10-agent-console-v1">{children}</body>
    </html>
  );
}
