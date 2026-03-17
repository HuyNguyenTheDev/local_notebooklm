"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useUi } from "@/lib/ui";

export default function HomePage() {
  const router = useRouter();
  const { t } = useUi();
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaces, setWorkspaces] = useState<string[]>([]);
  const [menuWorkspace, setMenuWorkspace] = useState<string | null>(null);

  const accentGradients = [
    "from-[#f97316] to-[#eab308]",
    "from-[#ec4899] to-[#8b5cf6]",
    "from-[#06b6d4] to-[#3b82f6]",
    "from-[#22c55e] to-[#0ea5e9]",
    "from-[#ef4444] to-[#f97316]",
    "from-[#14b8a6] to-[#22c55e]",
  ];

  useEffect(() => {
    const raw = window.localStorage.getItem("workspaces");
    if (!raw) {
      return;
    }

    try {
      const parsed = JSON.parse(raw) as string[];
      setWorkspaces(parsed);
    } catch {
      setWorkspaces([]);
    }
  }, []);

  const createWorkspace = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleaned = workspaceName.trim();
    if (!cleaned) {
      return;
    }

    if (!workspaces.includes(cleaned)) {
      const updated = [cleaned, ...workspaces];
      setWorkspaces(updated);
      window.localStorage.setItem("workspaces", JSON.stringify(updated));
    }

    setWorkspaceName("");
    router.push(`/workspace/${encodeURIComponent(cleaned)}`);
  };

  const openWorkspace = (name: string) => {
    router.push(`/workspace/${encodeURIComponent(name)}`);
  };

  const getAccentClass = (name: string) => {
    let hash = 0;
    for (let i = 0; i < name.length; i += 1) {
      hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
    }
    return accentGradients[hash % accentGradients.length];
  };

  const deleteWorkspace = (name: string) => {
    const updated = workspaces.filter((workspace) => workspace !== name);
    setWorkspaces(updated);
    window.localStorage.setItem("workspaces", JSON.stringify(updated));
    setMenuWorkspace(null);
  };

  return (
    <main className="min-h-screen px-4 py-6">
      <div className="mx-auto max-w-5xl">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-card dark:border-slate-700 dark:bg-slate-900">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">{t("pickWorkspace")}</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{t("workspaceHint")}</p>

          <form onSubmit={createWorkspace} className="mt-5 flex flex-col gap-3 sm:flex-row">
            <input
              value={workspaceName}
              onChange={(event) => setWorkspaceName(event.target.value)}
              placeholder={t("workspaceName")}
              className="flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-moss dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
            <button
              type="submit"
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 dark:bg-slate-100 dark:text-slate-900"
            >
              {t("createWorkspace")}
            </button>
          </form>
        </section>

        <section className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {workspaces.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400">
              {t("noWorkspace")}
            </div>
          ) : (
            workspaces.map((workspace) => (
              <article
                key={workspace}
                className="group relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-1 hover:shadow-card dark:border-slate-700 dark:bg-slate-900"
              >
                <div className={`absolute left-0 top-0 h-full w-2 bg-gradient-to-b ${getAccentClass(workspace)}`} />

                <button
                  type="button"
                  onClick={() => setMenuWorkspace((current) => (current === workspace ? null : workspace))}
                  className="absolute right-3 top-3 z-10 rounded-md p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                  aria-label="Workspace menu"
                >
                  ...
                </button>

                {menuWorkspace === workspace ? (
                  <div className="absolute right-3 top-11 z-20 min-w-[140px] rounded-lg border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
                    <button
                      type="button"
                      onClick={() => deleteWorkspace(workspace)}
                      className="w-full rounded-md px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
                    >
                      {t("deleteWorkspace")}
                    </button>
                  </div>
                ) : null}

                <button type="button" onClick={() => openWorkspace(workspace)} className="ml-3 block w-full pr-8 text-left">
                  <p className="text-xs uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{t("workspace")}</p>
                  <h2 className="mt-2 line-clamp-2 text-lg font-semibold text-slate-900 dark:text-slate-100">{workspace}</h2>
                  <p className="mt-3 text-xs text-slate-500 transition group-hover:text-slate-700 dark:text-slate-400 dark:group-hover:text-slate-200">
                    {t("enterWorkspace")}
                  </p>
                </button>
              </article>
            ))
          )}
        </section>
      </div>
    </main>
  );
}
