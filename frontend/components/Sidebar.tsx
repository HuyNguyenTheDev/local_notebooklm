"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { useUi } from "@/lib/ui";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useUi();
  const showSidebar = false;

  // Temporarily hide left sidebar. Set to true to enable it again.
  if (!showSidebar) {
    return null;
  }

  const workspaceMatch = pathname.match(/^\/workspace\/([^/]+)/);
  const workspaceName = workspaceMatch ? decodeURIComponent(workspaceMatch[1]) : null;
  const isWorkspacePage = !!workspaceName;

  return (
    <aside className="flex flex-col h-screen shrink-0 w-64 bg-slate-100 dark:bg-slate-900 font-manrope text-sm font-medium overflow-hidden">
      {/* Header / Brand */}
      <div className="px-6 pt-6 pb-4">
        <Link href="/" className="flex items-center gap-3 mb-6 group">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-on-primary shadow-sm group-hover:scale-105 transition-transform">
            <span className="material-symbols-outlined text-[20px]">auto_awesome</span>
          </div>
          <div>
            <h2 className="font-black text-indigo-600 dark:text-indigo-400 leading-tight text-base">
              {workspaceName ?? t("appTitle")}
            </h2>
            <p className="text-[10px] text-on-surface-variant tracking-wider uppercase">
              AI Workspace
            </p>
          </div>
        </Link>

        {/* CTA Button */}
        {isWorkspacePage ? (
          <button
            type="button"
            onClick={() => router.push("/")}
            className="w-full py-2.5 px-4 bg-primary text-on-primary rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-primary-dim transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-[18px]">upload_file</span>
            {t("addSource")}
          </button>
        ) : (
          <button
            type="button"
            onClick={() => router.push("/")}
            className="w-full py-2.5 px-4 bg-primary text-on-primary rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-primary-dim transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            {t("newWorkspace")}
          </button>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-4 space-y-0.5 overflow-y-auto">
        <NavItem
          href="/"
          icon="home"
          label={t("pickWorkspace")}
          active={pathname === "/"}
        />
        {isWorkspacePage && (
          <NavItem
            href={`/workspace/${encodeURIComponent(workspaceName!)}`}
            icon="book"
            label={t("sources")}
            active={isWorkspacePage}
            filled
          />
        )}
        <NavItem href="#" icon="folder_shared" label="Notebooks" active={false} disabled />
        <NavItem href="#" icon="edit_note" label="Templates" active={false} disabled />
        <NavItem href="#" icon="delete" label={t("delete")} active={false} disabled />
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-slate-200/60 dark:border-slate-800/60 space-y-0.5">
        <NavItem href="#" icon="settings" label={t("settings")} active={false} small />
        <NavItem href="#" icon="help_outline" label={t("help")} active={false} small />
      </div>
    </aside>
  );
}

type NavItemProps = {
  href: string;
  icon: string;
  label: string;
  active: boolean;
  filled?: boolean;
  small?: boolean;
  disabled?: boolean;
};

function NavItem({ href, icon, label, active, filled, small, disabled }: NavItemProps) {
  const baseClass = small
    ? "flex items-center gap-3 py-2 px-3 rounded-lg transition-colors"
    : "flex items-center gap-3 py-2.5 px-3 rounded-lg transition-colors";

  if (active) {
    return (
      <Link
        href={href}
        className={`${baseClass} text-indigo-700 dark:text-indigo-300 font-bold border-l-4 border-indigo-600 !rounded-none !pl-2 bg-slate-200/60 dark:bg-slate-800/60`}
      >
        <span
          className="material-symbols-outlined text-[20px]"
          style={filled ? { fontVariationSettings: "'FILL' 1" } : undefined}
        >
          {icon}
        </span>
        {label}
      </Link>
    );
  }

  if (disabled) {
    return (
      <span className={`${baseClass} text-slate-400 dark:text-slate-600 cursor-not-allowed opacity-60`}>
        <span className="material-symbols-outlined text-[20px]">{icon}</span>
        {label}
      </span>
    );
  }

  return (
    <Link
      href={href}
      className={`${baseClass} text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-200`}
    >
      <span className="material-symbols-outlined text-[20px]">{icon}</span>
      {label}
    </Link>
  );
}
