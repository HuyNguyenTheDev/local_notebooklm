"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useUi } from "@/lib/ui";

export default function TopBar() {
  const pathname = usePathname();
  const { language, setLanguage, theme, setTheme, t } = useUi();
  const workspaceMatch = pathname.match(/^\/workspace\/([^/]+)/);
  const workspaceName = workspaceMatch ? decodeURIComponent(workspaceMatch[1]) : null;

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200/70 bg-white/80 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Link href="/" className="inline-flex items-center gap-2 text-lg font-bold text-slate-900 dark:text-white">
            <Image
              src="/notebook.png"
              alt="Notebook logo"
              width={24}
              height={24}
              className="h-6 w-6 rounded"
              priority
            />
            <span>{t("appTitle")}</span>
          </Link>
          {workspaceName ? (
            <div className="hidden max-w-[320px] items-center gap-2 rounded-full border border-slate-200 bg-gradient-to-r from-white to-slate-50 px-2 py-1 text-xs text-slate-700 shadow-sm md:flex dark:border-slate-700 dark:from-slate-900 dark:to-slate-800 dark:text-slate-200">
              <span className="inline-flex h-5 items-center rounded-full bg-slate-900 px-2 text-[10px] font-bold uppercase tracking-[0.12em] text-white dark:bg-slate-100 dark:text-slate-900">
                {t("workspace")}
              </span>
              <span className="truncate pr-1 font-semibold">{workspaceName}</span>
            </div>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value as "en" | "vi")}
            className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
          >
            <option value="vi">{t("vi")}</option>
            <option value="en">{t("en")}</option>
          </select>

          <button
            type="button"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-200"
          >
            {t("theme")}: {theme === "light" ? t("light") : t("dark")}
          </button>
        </div>
      </div>
    </header>
  );
}
