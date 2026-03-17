"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useUi } from "@/lib/ui";

type WorkspaceTabsProps = {
  workspaceId: string;
};

export default function WorkspaceTabs({ workspaceId }: WorkspaceTabsProps) {
  const pathname = usePathname();
  const { t } = useUi();

  const tabs = [
    { href: `/workspace/${workspaceId}/upload`, label: t("navUpload") },
    { href: `/workspace/${workspaceId}/chat`, label: t("navChat") },
  ];

  return (
    <div className="mb-5 flex items-center justify-between gap-3">
      <Link
        href="/"
        className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 dark:border-slate-700 dark:text-slate-100"
      >
        {t("backToWorkspaces")}
      </Link>

      <div className="flex gap-2 rounded-2xl border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-900">
        {tabs.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={[
                "rounded-xl px-3 py-2 text-xs font-semibold transition",
                active
                  ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
              ].join(" ")}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
