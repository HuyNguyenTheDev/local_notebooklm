import type { Metadata } from "next";

import Sidebar from "@/components/Sidebar";
import TopBar from "@/components/TopBar";
import { UiProvider } from "@/lib/ui";

import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Local NotebookLM",
  description: "Upload docs, build knowledge, and chat with your local assistant",
  icons: {
    icon: [
      { url: "/notebooklm.png", sizes: "32x32", type: "image/png" },
      { url: "/notebooklm.png", sizes: "64x64", type: "image/png" },
      { url: "/notebooklm.png", sizes: "192x192", type: "image/png" },
    ],
    shortcut: "/notebooklm.png",
    apple: [{ url: "/notebooklm.png", sizes: "180x180", type: "image/png" }],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-surface text-on-surface dark:bg-slate-950 dark:text-slate-100 overflow-hidden">
        <UiProvider>
          <div className="flex h-screen w-full overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
              <TopBar />
              <main className="flex-1 overflow-y-auto">
                {children}
              </main>
            </div>
          </div>
        </UiProvider>
      </body>
    </html>
  );
}
