"use client";

import { use, useCallback, useEffect, useState } from "react";

import ChatBox from "@/components/ChatBox";
import ChatSessionsSidebar from "@/components/ChatSessionsSidebar";
import FileUpload from "@/components/FileUpload";
import KnowledgeList from "@/components/KnowledgeList";
import {
  ChatSession,
  deleteChatSession,
  DocumentChunk,
  DocumentPreview,
  getChatSessions,
  getDocuments,
  renameChatSession,
} from "@/lib/api";
import { useUi } from "@/lib/ui";

type WorkspaceEntryPageProps = {
  params: Promise<{ workspaceId: string }>;
};

type ActiveView = "sources" | "chat";

const FINAL_PARSE_STATUSES = new Set(["done", "failed"]);

export default function WorkspaceEntryPage({ params }: WorkspaceEntryPageProps) {
  const { t } = useUi();
  const { workspaceId: rawWorkspaceId } = use(params);
  const workspaceId = decodeURIComponent(rawWorkspaceId);

  const [documents, setDocuments] = useState<DocumentPreview[]>([]);
  const [loading, setLoading] = useState(true);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [activeChatSessionId, setActiveChatSessionId] = useState<string | null>(null);
  const [loadingChatSessions, setLoadingChatSessions] = useState(true);
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [showUploadModal, setShowUploadModal] = useState(false);

  const loadDocuments = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const data = await getDocuments(workspaceId);
      setDocuments(data);
    } finally {
      if (showLoading) setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const refreshChatSessions = useCallback(async () => {
    const data = await getChatSessions(workspaceId);
    setChatSessions(data);
    return data;
  }, [workspaceId]);

  useEffect(() => {
    let cancelled = false;

    const loadInitialChatSessions = async () => {
      setLoadingChatSessions(true);
      setActiveChatSessionId(null);
      try {
        const data = await getChatSessions(workspaceId);
        if (cancelled) return;
        setChatSessions(data);
        setActiveChatSessionId(data[0]?.id ?? null);
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setChatSessions([]);
      } finally {
        if (!cancelled) setLoadingChatSessions(false);
      }
    };

    void loadInitialChatSessions();

    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  useEffect(() => {
    const hasActiveIngest = documents.some((doc) => !FINAL_PARSE_STATUSES.has(doc.parse_status));
    if (!hasActiveIngest) return;

    const timerId = window.setInterval(() => {
      void loadDocuments(false);
    }, 2000);

    return () => window.clearInterval(timerId);
  }, [documents, loadDocuments]);

  const handleUploaded = () => {
    setShowUploadModal(false);
    void loadDocuments();
  };

  const handleCreateChatSession = () => {
    setActiveChatSessionId(null);
    setActiveView("chat");
  };

  const handleRenameChatSession = async (sessionId: string, title: string) => {
    const session = await renameChatSession(sessionId, workspaceId, title);
    setChatSessions((prev) =>
      prev.map((item) => (item.id === session.id ? session : item)),
    );
  };

  const handleDeleteChatSession = async (sessionId: string) => {
    await deleteChatSession(sessionId, workspaceId);
    setChatSessions((prev) => {
      const next = prev.filter((item) => item.id !== sessionId);
      if (activeChatSessionId === sessionId) {
        setActiveChatSessionId(next[0]?.id ?? null);
      }
      return next;
    });
  };

  return (
    <div className="flex flex-col h-full min-h-[calc(100vh-57px)]">
      {/* Page header */}
      <div className="px-8 pt-4 pb-2 border-b border-outline-variant/10">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-5">
          <div>
            <h1 className="text-3xl font-extrabold text-on-surface tracking-tight font-headline mb-1">
              {workspaceId}
            </h1>
            <p className="text-on-surface-variant text-sm">
              {documents.length} source{documents.length !== 1 ? "s" : ""} indexed • {t("workspaceHint")}
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* View toggle */}
            <div className="flex bg-surface-container-low dark:bg-slate-800 rounded-xl p-1 gap-1">
              <button
                type="button"
                onClick={() => setActiveView("chat")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                  activeView === "chat"
                    ? "bg-white dark:bg-slate-700 text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">chat</span>
                {t("chat")}
              </button>
              <button
                type="button"
                onClick={() => setActiveView("sources")}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                  activeView === "sources"
                    ? "bg-white dark:bg-slate-700 text-primary shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                <span className="material-symbols-outlined text-[16px]">book</span>
                {t("sources")}
              </button>
            </div>

            {/* Upload button */}
            <button
              type="button"
              onClick={() => setShowUploadModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 bg-primary text-on-primary rounded-xl font-bold text-sm hover:bg-primary-dim transition-all shadow-md shadow-primary/20"
            >
              <span className="material-symbols-outlined text-[18px]">upload_file</span>
              {t("addSource")}
            </button>
          </div>
        </div>

        {/* Filter chips */}
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {activeView === "sources" ? (
          /* Sources view: bento document grid */
          <div className="h-full overflow-y-auto px-8 py-6">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="flex flex-col items-center gap-3">
                  <svg className="h-8 w-8 animate-spin text-primary" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-sm font-medium text-on-surface-variant">{t("loadingKnowledge")}</p>
                </div>
              </div>
            ) : (
              <DocumentGrid
                workspaceId={workspaceId}
                documents={documents}
                onDeleted={loadDocuments}
                onAddSource={() => setShowUploadModal(true)}
              />
            )}
          </div>
        ) : (
          /* Chat view: sessions + chat + knowledge sidebar */
          <div className="h-full flex overflow-hidden">
            <div className="w-72 border-r border-outline-variant/10 overflow-hidden p-4 flex flex-col">
              <ChatSessionsSidebar
                sessions={chatSessions}
                activeSessionId={activeChatSessionId}
                loading={loadingChatSessions}
                onNewSession={() => void handleCreateChatSession()}
                onSelectSession={setActiveChatSessionId}
                onRenameSession={handleRenameChatSession}
                onDeleteSession={handleDeleteChatSession}
              />
            </div>
            <div className="flex-1 overflow-hidden p-4">
              <ChatBox
                workspaceId={workspaceId}
                activeSessionId={activeChatSessionId}
                onSessionChange={setActiveChatSessionId}
                onSessionsChanged={() => void refreshChatSessions()}
              />
            </div>
            <div className="w-72 border-l border-outline-variant/10 overflow-hidden p-4 flex flex-col">
              {loading ? null : (
                <KnowledgeList
                  workspaceId={workspaceId}
                  documents={documents}
                  onDeleted={loadDocuments}
                />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Upload modal */}
      {showUploadModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fadeIn"
          onClick={() => setShowUploadModal(false)}
        >
          <div
            className="bg-white dark:bg-slate-900 rounded-xxl shadow-2xl p-6 w-full max-w-md mx-4 animate-rise"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg font-headline">{t("addSourceModalTitle")}</h3>
              <button
                type="button"
                onClick={() => setShowUploadModal(false)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-container-low transition-colors"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
            <FileUpload workspaceId={workspaceId} onUploaded={handleUploaded} />
          </div>
        </div>
      )}

      {/* Chat FAB (visible in sources view) */}
      {activeView === "sources" && (
        <button
          type="button"
          onClick={() => setActiveView("chat")}
          className="fixed bottom-8 right-8 w-14 h-14 rounded-2xl bg-primary text-on-primary shadow-2xl flex items-center justify-center hover:scale-105 active:scale-95 transition-transform z-40"
          aria-label="Open Chat"
        >
          <span
            className="material-symbols-outlined text-[28px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            smart_toy
          </span>
        </button>
      )}
    </div>
  );
}

/* Document bento grid */
type DocumentGridProps = {
  workspaceId: string;
  documents: DocumentPreview[];
  onDeleted: () => void;
  onAddSource: () => void;
};

function DocumentGrid({ workspaceId, documents, onDeleted, onAddSource }: DocumentGridProps) {
  const { t, language } = useUi();
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [viewing, setViewing] = useState<{
    id: string;
    filename: string;
    mode: "content" | "chunks";
    content: string;
    chunks: DocumentChunk[];
    loading: boolean;
  } | null>(null);

  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { deleteDocument, renameDocument, getDocumentContent, getDocumentChunks } = require("@/lib/api") as typeof import("@/lib/api");

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { dateStyle: "medium" });
  };

  const getDocIcon = (type: string) => {
    const map: Record<string, string> = { pdf: "picture_as_pdf", txt: "text_snippet", md: "article" };
    return map[type.toLowerCase()] ?? "description";
  };

  const getBadgeColors = (type: string) => {
    const map: Record<string, string> = {
      pdf: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400",
      txt: "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400",
      md: "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400",
    };
    return map[type.toLowerCase()] ?? "bg-surface-container text-on-surface-variant";
  };

  const getStatusColors = (status: string) => {
    const map: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-400",
      processing: "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400",
      done: "bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-400",
      failed: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400",
    };
    return map[status.toLowerCase()] ?? "bg-surface-container text-on-surface-variant";
  };

  const getStatusLabel = (status: string) => {
    const map: Record<string, string> = {
      pending: "Pending",
      processing: "Processing",
      done: "Indexed",
      failed: "Failed",
    };
    return map[status.toLowerCase()] ?? status;
  };

  const canViewContent = (doc: DocumentPreview) => FINAL_PARSE_STATUSES.has(doc.parse_status);
  const canViewChunks = (doc: DocumentPreview) => doc.parse_status === "done";

  const handleDelete = async (id: string) => {
    await deleteDocument(id, workspaceId);
    setOpenMenuId(null);
    onDeleted();
  };

  const handleRenameSubmit = async (id: string) => {
    if (!editingName.trim()) { setEditingId(null); return; }
    await renameDocument(id, editingName, workspaceId);
    setEditingId(null);
    onDeleted();
  };

  const handleViewContent = async (doc: DocumentPreview) => {
    setOpenMenuId(null);
    setViewing({ id: doc.id, filename: doc.filename, mode: "content", content: "", chunks: [], loading: true });
    try {
      const data = await getDocumentContent(doc.id);
      setViewing({
        id: doc.id,
        filename: data.filename || doc.filename,
        mode: "content",
        content: data.raw_text || "",
        chunks: [],
        loading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load content";
      setViewing({ id: doc.id, filename: doc.filename, mode: "content", content: message, chunks: [], loading: false });
    }
  };

  const handleViewChunks = async (doc: DocumentPreview) => {
    setOpenMenuId(null);
    setViewing({ id: doc.id, filename: doc.filename, mode: "chunks", content: "", chunks: [], loading: true });
    try {
      const chunks = await getDocumentChunks(doc.id);
      setViewing({
        id: doc.id,
        filename: doc.filename,
        mode: "chunks",
        content: "",
        chunks,
        loading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load chunks";
      setViewing({ id: doc.id, filename: doc.filename, mode: "content", content: message, chunks: [], loading: false });
    }
  };

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-20 h-20 rounded-full bg-surface-container dark:bg-slate-800 flex items-center justify-center mb-5">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant">folder_open</span>
        </div>
        <h3 className="text-lg font-bold font-headline mb-2">{t("noDocs")}</h3>
        <p className="text-on-surface-variant text-sm mb-6 max-w-sm">
          {t("noDocsHint")}
        </p>
        <button
          type="button"
          onClick={onAddSource}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-on-primary rounded-xl font-bold hover:bg-primary-dim transition-all shadow-lg shadow-primary/20"
        >
          <span className="material-symbols-outlined text-[18px]">upload_file</span>
          {t("uploadFirstSource")}
        </button>
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
      {documents.map((doc, index) => (
        <article
          key={doc.id}
          className="group relative bg-surface-container-lowest dark:bg-slate-900 rounded-3xl p-5 hover:shadow-xl transition-all duration-200 flex flex-col justify-between min-h-[200px] border border-transparent hover:border-primary/15 animate-rise"
          style={{ animationDelay: `${index * 50}ms` }}
        >
          {/* Menu */}
          <div className="absolute top-4 right-4">
            <button
              type="button"
              onClick={() => setOpenMenuId(openMenuId === doc.id ? null : doc.id)}
              className="w-7 h-7 rounded-lg text-on-surface-variant opacity-0 group-hover:opacity-100 hover:bg-surface-container-high flex items-center justify-center transition-all"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
              </svg>
            </button>
            {openMenuId === doc.id && (
              <div className="absolute right-0 z-20 mt-1 w-44 overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 shadow-xl animate-slideIn">
                <button
                  type="button"
                  onClick={() => void handleViewContent(doc)}
                  disabled={!canViewContent(doc)}
                  className={`flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm transition-colors ${
                    canViewContent(doc)
                      ? "text-on-surface hover:bg-surface-container-low"
                      : "text-on-surface-variant/60 cursor-not-allowed"
                  }`}
                >
                  <span className="material-symbols-outlined text-[16px]">visibility</span>
                  View content
                </button>
                <button
                  type="button"
                  onClick={() => void handleViewChunks(doc)}
                  disabled={!canViewChunks(doc)}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm transition-colors text-on-surface hover:bg-surface-container-low disabled:text-on-surface-variant/60 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                >
                  <span className="material-symbols-outlined text-[16px]">view_list</span>
                  View chunks
                </button>
                <button
                  type="button"
                  onClick={() => { setEditingId(doc.id); setEditingName(doc.filename); setOpenMenuId(null); }}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-on-surface hover:bg-surface-container-low transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">edit</span>
                  {t("rename")}
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(doc.id)}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-error hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">delete</span>
                  {t("delete")}
                </button>
              </div>
            )}
          </div>

          {/* Top content */}
          <div>
            <div className="flex items-start gap-3 mb-3">
              <div className="p-3 bg-surface-container-low dark:bg-slate-800 rounded-2xl group-hover:bg-primary-container transition-colors shrink-0">
                <span className="material-symbols-outlined text-primary text-[24px]">{getDocIcon(doc.file_type)}</span>
              </div>
              <div className="flex-1 min-w-0 pr-7">
                {editingId === doc.id ? (
                  <input
                    autoFocus
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleRenameSubmit(doc.id);
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    className="w-full rounded-lg border border-primary/50 bg-white dark:bg-slate-800 px-2 py-1 text-sm font-semibold outline-none focus:ring-2 focus:ring-primary/20"
                  />
                ) : (
                  <h3 className="font-bold text-on-surface group-hover:text-primary transition-colors text-sm leading-snug truncate">
                    {doc.filename}
                  </h3>
                )}
                <div className="flex gap-1.5 mt-2 flex-wrap">
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${getBadgeColors(doc.file_type)}`}>
                    {doc.file_type.toUpperCase()}
                  </span>
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${getStatusColors(doc.parse_status)}`}>
                    {getStatusLabel(doc.parse_status)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between mt-auto pt-3 border-t border-outline-variant/10">
            <div className="text-[11px] text-on-surface-variant">
              <p className="font-semibold">{formatDate(doc.created_at)}</p>
            </div>
            {editingId === doc.id && (
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => void handleRenameSubmit(doc.id)}
                  className="px-2.5 py-1 bg-primary text-on-primary rounded-lg text-xs font-bold hover:bg-primary-dim transition-colors"
                >
                  OK
                </button>
                <button
                  type="button"
                  onClick={() => setEditingId(null)}
                  className="px-2.5 py-1 bg-surface-container text-on-surface-variant rounded-lg text-xs font-medium hover:bg-surface-container-high transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </article>
      ))}

      {/* Ghost add card */}
      <button
        type="button"
        onClick={onAddSource}
        className="group border-2 border-dashed border-outline-variant/30 rounded-3xl p-5 flex flex-col items-center justify-center gap-3 hover:border-primary/50 hover:bg-primary/5 transition-all min-h-[200px]"
      >
        <div className="w-12 h-12 rounded-full bg-surface-container dark:bg-slate-800 flex items-center justify-center group-hover:bg-primary-container transition-colors">
          <span className="material-symbols-outlined text-on-surface-variant group-hover:text-primary transition-colors">
            upload_file
          </span>
        </div>
        <p className="font-bold text-on-surface-variant group-hover:text-primary transition-colors text-sm">
          {t("uploadNewSource")}
        </p>
        <p className="text-[11px] text-on-surface-variant text-center px-2">
          {t("dragDropHint")}
        </p>
      </button>
      </div>

      {viewing && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fadeIn"
          onClick={() => setViewing(null)}
        >
          <div
            className="bg-white dark:bg-slate-900 rounded-xxl shadow-2xl p-6 w-full max-w-3xl mx-4 animate-rise"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="min-w-0">
                <h3 className="font-bold text-lg font-headline truncate">{viewing.filename}</h3>
                {viewing.mode === "chunks" && !viewing.loading && (
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    {viewing.chunks.length} chunks
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setViewing(null)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-container-low transition-colors"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="border-2 border-dashed rounded-[1.2rem] p-5 bg-surface-container-lowest dark:bg-slate-950/40">
              {viewing.loading ? (
                <div className="text-sm text-on-surface-variant">
                  Loading {viewing.mode === "chunks" ? "chunks" : "content"}...
                </div>
              ) : viewing.mode === "chunks" ? (
                <div className="max-h-[60vh] overflow-y-auto space-y-3 pr-1">
                  {viewing.chunks.length > 0 ? (
                    viewing.chunks.map((chunk) => (
                      <section
                        key={chunk.id}
                        className="rounded-xl border border-outline-variant/20 bg-white/70 dark:bg-slate-900/70 p-4"
                      >
                        <div className="flex items-center justify-between gap-3 mb-2">
                          <span className="text-xs font-bold text-primary">
                            Chunk #{chunk.chunk_index + 1}
                          </span>
                          <span className="text-[11px] text-on-surface-variant shrink-0">
                            {chunk.token_count ?? 0} tokens
                          </span>
                        </div>
                        <pre className="text-xs text-on-surface whitespace-pre-wrap leading-relaxed">
{chunk.content}
                        </pre>
                      </section>
                    ))
                  ) : (
                    <div className="text-sm text-on-surface-variant">No chunks available.</div>
                  )}
                </div>
              ) : (
                <pre className="text-xs text-on-surface whitespace-pre-wrap max-h-[60vh] overflow-y-auto">
{viewing.content || "No content available."}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
