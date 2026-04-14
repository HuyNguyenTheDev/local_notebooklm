"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useUi } from "@/lib/ui";

export default function TopBar() {
  const pathname = usePathname();
  const { t, language, setLanguage, theme, setTheme } = useUi();

  const workspaceMatch = pathname.match(/^\/workspace\/([^/]+)/);
  const workspaceName = workspaceMatch ? decodeURIComponent(workspaceMatch[1]) : null;

  return (
    <header className="flex justify-between items-center px-6 py-3 w-full border-b border-slate-200/50 dark:border-slate-800/50 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md sticky top-0 z-40 font-manrope">
      {/* Left: Title + workspace breadcrumb + search */}
      <div className="flex items-center gap-6 flex-1 min-w-0">
        <Link
          href="/"
          className="text-base font-bold text-slate-900 dark:text-slate-50 tracking-tight hover:text-primary transition-colors shrink-0"
        >
          {t("appTitle")}
        </Link>

        {workspaceName && (
          <>
            <div className="h-4 w-px bg-slate-200 dark:bg-slate-700" />
            <div className="flex items-center gap-2 text-on-surface-variant font-medium text-sm min-w-0">
              <span className="material-symbols-outlined text-[16px] shrink-0">description</span>
              <span className="truncate">{workspaceName}</span>
            </div>
          </>
        )}

        {/* Search */}
        <div className="hidden lg:block ml-4 relative max-w-xs w-full">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[18px]">
            search
          </span>
          <input
            type="text"
            placeholder={t("searchPlaceholder")}
            className="w-full bg-surface-container-low dark:bg-slate-800 border-none rounded-xl pl-9 pr-4 py-2 text-sm focus:ring-2 focus:ring-primary/20 outline-none placeholder:text-on-surface-variant"
          />
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-2 shrink-0">
        {/* AI status */}
        <div className="hidden sm:flex items-center gap-2 rounded-full bg-surface-container-low dark:bg-slate-800 px-3 py-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-medium text-on-surface-variant">{t("aiActive")}</span>
        </div>

        {/* Language selector */}
        <div className="relative flex items-center">
          <span className="material-symbols-outlined text-[16px] text-on-surface-variant absolute left-2.5 pointer-events-none">
            language
          </span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as "en" | "vi")}
            className="appearance-none cursor-pointer rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 pl-8 pr-6 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 outline-none hover:border-primary/50 focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all"
            aria-label={t("lang")}
          >
            <option value="vi">VI</option>
            <option value="en">EN</option>
          </select>
          <span className="material-symbols-outlined text-[14px] text-on-surface-variant absolute right-1.5 pointer-events-none">
            expand_more
          </span>
        </div>

        {/* Theme toggle */}
        <button
          type="button"
          onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          className="flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:border-primary/50 transition-all"
          aria-label={theme === "light" ? t("dark") : t("light")}
        >
          {theme === "light" ? (
            <>
              <span className="material-symbols-outlined text-[16px]">dark_mode</span>
              <span className="hidden sm:inline">{t("dark")}</span>
            </>
          ) : (
            <>
              <span className="material-symbols-outlined text-[16px]">light_mode</span>
              <span className="hidden sm:inline">{t("light")}</span>
            </>
          )}
        </button>

        {/* Divider + icon buttons */}
        <div className="flex items-center gap-1 border-l border-slate-200 dark:border-slate-700 pl-2">
          <button
            type="button"
            className="text-on-surface-variant hover:text-primary transition-colors p-1.5 rounded-lg hover:bg-surface-container-low"
            aria-label="Notifications"
          >
            <span className="material-symbols-outlined text-[20px]">notifications</span>
          </button>
          <button
            type="button"
            className="text-on-surface-variant hover:text-primary transition-colors p-1.5 rounded-lg hover:bg-surface-container-low"
            aria-label="Account"
          >
            <span className="material-symbols-outlined text-[20px]">account_circle</span>
          </button>
        </div>
      </div>
    </header>
  );
}
