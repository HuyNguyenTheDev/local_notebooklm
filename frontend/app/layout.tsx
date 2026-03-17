import type { Metadata } from "next";

import TopBar from "@/components/TopBar";
import { UiProvider } from "@/lib/ui";

import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Local NotebookLM",
  description: "Upload docs, build knowledge, and chat with your local assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-shell text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <UiProvider>
          <TopBar />
          {children}
        </UiProvider>
      </body>
    </html>
  );
}
