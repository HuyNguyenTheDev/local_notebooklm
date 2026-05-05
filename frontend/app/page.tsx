"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { WorkspacePreview, createWorkspace as createWorkspaceApi, deleteWorkspace as deleteWorkspaceApi, getWorkspaces } from "@/lib/api";
import { useUi } from "@/lib/ui";

type WorkspaceItem = {
  name: string;
  createdAt: string;
  icon: string;
};

const WORKSPACE_ICONS = ["📘", "📗", "📙", "📕", "📓", "🧠", "🗂️", "📝"];

function pickIcon(seed?: string) {
  if (!seed) return WORKSPACE_ICONS[Math.floor(Math.random() * WORKSPACE_ICONS.length)];
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return WORKSPACE_ICONS[hash % WORKSPACE_ICONS.length];
}

const DOC_TYPE_ICONS: Record<string, string> = {
  pdf: "picture_as_pdf",
  txt: "text_snippet",
  md: "article",
};

function docIcon(type: string) {
  return DOC_TYPE_ICONS[type.toLowerCase()] ?? "description";
}

export default function HomePage() {
  const router = useRouter();
  const { t } = useUi();
  const [workspaceName, setWorkspaceName] = useState("");
  const [workspaces, setWorkspaces] = useState<WorkspaceItem[]>([]);
  const [workspaceAlert, setWorkspaceAlert] = useState<string | null>(null);
  const [menuWorkspace, setMenuWorkspace] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const mergeWorkspaceSources = (localItems: WorkspaceItem[], remoteItems: WorkspacePreview[]) => {
    const merged = new Map<string, WorkspaceItem>();
    localItems.forEach((item) => merged.set(item.name, item));
    remoteItems.forEach((item) => {
      if (!merged.has(item.workspace_id)) {
        merged.set(item.workspace_id, {
          name: item.workspace_id,
          createdAt: item.created_at,
          icon: pickIcon(item.workspace_id),
        });
      }
    });
    return Array.from(merged.values());
  };

  useEffect(() => {
    const load = async () => {
      let localItems: WorkspaceItem[] = [];
      const raw = window.localStorage.getItem("workspaces");
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as unknown;
          if (
            Array.isArray(parsed) &&
            parsed.every(
              (i) => typeof i === "object" && i !== null && "name" in i && "createdAt" in i && "icon" in i,
            )
          ) {
            localItems = parsed as WorkspaceItem[];
          } else if (Array.isArray(parsed) && parsed.every((i) => typeof i === "string")) {
            localItems = (parsed as string[]).map((name) => ({
              name,
              createdAt: new Date().toISOString(),
              icon: pickIcon(),
            }));
            window.localStorage.setItem("workspaces", JSON.stringify(localItems));
          }
        } catch {
          localItems = [];
        }
      }
      setWorkspaces(localItems);
      try {
        const remote = await getWorkspaces();
        const merged = mergeWorkspaceSources(localItems, remote);
        setWorkspaces(merged);
        window.localStorage.setItem("workspaces", JSON.stringify(merged));
      } catch {
        // keep local
      }
    };
    void load();
  }, []);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" }).format(d);
  };

  const createWorkspace = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleaned = workspaceName.trim();
    if (!cleaned) return;

    const normalize = (value: string) => value.trim().toLocaleLowerCase();
    const normalizedCleaned = normalize(cleaned);
    setWorkspaceAlert(null);

    try {
      const remote = await getWorkspaces();
      const merged = mergeWorkspaceSources(workspaces, remote);
      setWorkspaces(merged);
      window.localStorage.setItem("workspaces", JSON.stringify(merged));

      const existsInBackend = remote.some((w) => normalize(w.workspace_id) === normalizedCleaned);
      const existsInLocal = merged.some((w) => normalize(w.name) === normalizedCleaned);

      if (existsInBackend || existsInLocal) {
        setWorkspaceAlert(t("workspaceExistsBackendAlert"));
        return;
      }
    } catch {
      if (workspaces.some((w) => normalize(w.name) === normalizedCleaned)) {
        setWorkspaceAlert(t("workspaceExistsBackendAlert"));
        return;
      }
    }

    const nw: WorkspaceItem = { name: cleaned, createdAt: new Date().toISOString(), icon: pickIcon() };
    const updated = [nw, ...workspaces];
    setWorkspaces(updated);
    window.localStorage.setItem("workspaces", JSON.stringify(updated));
    setWorkspaceName("");
    void createWorkspaceApi(cleaned);
    router.push(`/workspace/${encodeURIComponent(cleaned)}`);
  };

  const openWorkspace = (workspace: WorkspaceItem) => {
    router.push(`/workspace/${encodeURIComponent(workspace.name)}`);
  };

  const deleteWorkspace = async (name: string) => {
    await deleteWorkspaceApi(name);
    const updated = workspaces.filter((w) => w.name !== name);
    setWorkspaces(updated);
    window.localStorage.setItem("workspaces", JSON.stringify(updated));
    setMenuWorkspace(null);
  };

  const hasWorkspaces = workspaces.length > 0;

  return (
    <div className="min-h-full relative overflow-hidden">
      {/* Background decorative blobs */}
      <div className="absolute -top-32 -right-32 w-96 h-96 bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-secondary/5 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 py-5">
        {/* Hero */}
        <div className="text-center mb-12 max-w-2xl mx-auto animate-fadeIn">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-on-surface mb-5 tracking-tight leading-tight font-headline">
            {t("heroTitle1")}{" "}
            <br />
            <span className="bg-gradient-to-r from-primary to-primary-dim bg-clip-text text-transparent">
              {t("heroTitle2")}
            </span>
          </h1>
        </div>

        {/* Create Workspace + Upload Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 mb-6 animate-rise">
          {/* Main Upload / Create area */}
          <div className="md:col-span-8 bg-surface-container-lowest dark:bg-slate-900 rounded-xxl p-1.5 group transition-all duration-300 hover:shadow-[0_12px_40px_rgba(42,52,57,0.06)]">
            <div
              className={`border-2 border-dashed rounded-[1.2rem] flex flex-col items-center justify-center p-6 text-center transition-colors ${
                isDragging
                  ? "border-primary bg-primary/5"
                  : "border-outline-variant/30 group-hover:border-primary/40"
              }`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => { e.preventDefault(); setIsDragging(false); }}
            >
              <div className="w-20 h-20 rounded-full bg-surface-container-low dark:bg-slate-800 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-500">
                <span className="material-symbols-outlined text-4xl text-primary">upload_file</span>
              </div>
              <h3 className="text-xl font-bold font-headline mb-2">
                {hasWorkspaces ? t("pickWorkspace") : t("createFirstWorkspace")}
              </h3>
              <p className="text-on-surface-variant text-sm mb-7">
                {hasWorkspaces ? t("enterNameHint") : t("enterNameFirst")}
              </p>

              {/* Create form */}
              <form onSubmit={createWorkspace} className="flex gap-3 w-full max-w-md">
                <input
                  value={workspaceName}
                  onChange={(e) => {
                    setWorkspaceName(e.target.value);
                    if (workspaceAlert) setWorkspaceAlert(null);
                  }}
                  placeholder={t("workspaceName")}
                  className="flex-1 rounded-xl border border-outline-variant/50 bg-surface-container-low dark:bg-slate-800 px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all placeholder:text-on-surface-variant"
                />
                <button
                  type="submit"
                  className="px-6 py-2.5 bg-primary text-on-primary rounded-xl font-bold hover:bg-primary-dim transition-all shadow-lg shadow-primary/20 text-sm"
                >
                  {t("createWorkspace")}
                </button>
              </form>
              {workspaceAlert && (
                <div className="mt-3 w-full max-w-md px-6 py-2.5 bg-primary text-on-primary rounded-xl font-bold transition-all shadow-lg shadow-primary/20 text-sm text-center">
                  {workspaceAlert}
                </div>
              )}
            </div>
          </div>

          {/* Quick action cards */}
          <div className="md:col-span-4 flex flex-col gap-4">
            {/* Tip card */}
            <div className="bg-primary-container/40 dark:bg-indigo-950/40 rounded-xxl p-5 flex items-start gap-3">
              <span
                className="material-symbols-outlined text-primary mt-0.5 shrink-0"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                lightbulb
              </span>
              <p className="text-[11px] font-medium text-on-primary-container dark:text-indigo-200 leading-relaxed">
                {t("tipSeparateWorkspaces")}
              </p>
            </div>

            {/* Format info */}
            <div className="bg-surface-container-low dark:bg-slate-800/60 rounded-xxl p-5 flex flex-col gap-3">
              <p className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">{t("supportedFormats")}</p>
              {[
                { icon: "picture_as_pdf", label: "PDF Documents", color: "text-red-500" },
                { icon: "text_snippet", label: "Plain Text (.txt)", color: "text-blue-500" },
                { icon: "article", label: "Markdown (.md)", color: "text-purple-500" },
              ].map(({ icon, label, color }) => (
                <div key={label} className="flex items-center gap-2.5">
                  <span className={`material-symbols-outlined text-[18px] ${color}`}>{icon}</span>
                  <span className="text-xs text-on-surface-variant">{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Workspace Grid */}
        {hasWorkspaces && (
          <section className="animate-rise" style={{ animationDelay: "100ms" }}>
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-extrabold font-headline text-on-surface tracking-tight">
                {t("yourWorkspaces")}
              </h2>
              <span className="text-xs font-semibold text-on-surface-variant bg-surface-container px-3 py-1 rounded-full">
                {workspaces.length} workspace{workspaces.length !== 1 ? "s" : ""}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {workspaces.map((workspace, index) => (
                <article
                  key={workspace.name}
                  className="group relative bg-surface-container-lowest dark:bg-slate-900 rounded-3xl p-5 hover:shadow-xl transition-all duration-200 flex flex-col justify-between min-h-[160px] cursor-pointer border border-transparent hover:border-primary/20 animate-rise"
                  style={{ animationDelay: `${index * 60}ms` }}
                  onClick={() => openWorkspace(workspace)}
                >
                  {/* Menu button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuWorkspace((cur) => (cur === workspace.name ? null : workspace.name));
                    }}
                    className="absolute top-4 right-4 z-10 w-7 h-7 rounded-lg text-on-surface-variant opacity-0 group-hover:opacity-100 hover:bg-surface-container-high flex items-center justify-center transition-all"
                    aria-label="Menu"
                  >
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                    </svg>
                  </button>

                  {/* Dropdown */}
                  {menuWorkspace === workspace.name && (
                    <div className="absolute right-4 top-12 z-20 min-w-[160px] overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 shadow-xl animate-slideIn">
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); void deleteWorkspace(workspace.name); }}
                        className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-error transition-colors hover:bg-red-50 dark:hover:bg-red-950/30"
                      >
                        <span className="material-symbols-outlined text-[16px]">delete</span>
                        {t("deleteWorkspace")}
                      </button>
                    </div>
                  )}

                  {/* Content */}
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-2xl bg-surface-container dark:bg-slate-800 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                      {workspace.icon}
                    </div>
                    <div className="flex-1 min-w-0 pr-7">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-0.5">
                        {t("workspace")}
                      </p>
                      <h3 className="font-bold text-on-surface group-hover:text-primary transition-colors truncate text-sm">
                        {workspace.name}
                      </h3>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mt-auto pt-3 border-t border-outline-variant/10">
                    <p className="text-[11px] text-on-surface-variant">
                      {t("workspaceCreatedAt")}: {formatDate(workspace.createdAt)}
                    </p>
                    <span className="material-symbols-outlined text-[16px] text-on-surface-variant group-hover:text-primary transition-colors">
                      arrow_forward
                    </span>
                  </div>
                </article>
              ))}

              {/* Ghost add card */}
              <button
                type="button"
                onClick={() => document.querySelector<HTMLInputElement>('input[placeholder]')?.focus()}
                className="group border-2 border-dashed border-outline-variant/30 rounded-3xl p-5 flex flex-col items-center justify-center gap-3 hover:border-primary/50 hover:bg-primary/5 transition-all min-h-[160px]"
              >
                <div className="w-10 h-10 rounded-full bg-surface-container dark:bg-slate-800 flex items-center justify-center group-hover:bg-primary-container transition-colors">
                  <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors text-[20px]">
                    add
                  </span>
                </div>
                <p className="text-sm font-bold text-on-surface-variant group-hover:text-primary transition-colors">
                  {t("newWorkspace")}
                </p>
              </button>
            </div>
          </section>
        )}

        {/* Footer meta */}
        <div className="mt-16 flex flex-col sm:flex-row items-center justify-between border-t border-outline-variant/10 pt-6 text-on-surface-variant text-xs gap-3">
          <div className="flex items-center gap-5">
            <span className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> {t("aiSystemsActive")}
            </span>
            <span>Local NotebookLM v1.0</span>
          </div>
          <div className="flex items-center gap-5">
            <span className="hover:text-primary cursor-pointer transition-colors">{t("privacy")}</span>
            <span className="hover:text-primary cursor-pointer transition-colors">{t("documentation")}</span>
          </div>
        </div>
      </div>

      {/* Help floating tooltip */}
      {/* <div className="fixed bottom-8 right-8 glass dark:bg-slate-900/80 p-3.5 rounded-xl shadow-[0_12px_40px_rgba(42,52,57,0.1)] flex items-center gap-3 border border-white/20 dark:border-slate-700/50 z-50">
        <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        <p className="text-xs font-medium text-on-surface dark:text-slate-200">{t("helpTooltip")}</p>
        <button
          type="button"
          className="bg-primary text-on-primary p-1.5 rounded-lg hover:scale-105 transition-transform"
        >
          <span className="material-symbols-outlined text-[16px] leading-none">chat_bubble</span>
        </button>
      </div> */}
    </div>
  );
}
