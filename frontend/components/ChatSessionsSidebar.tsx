"use client";

import { useState } from "react";

import { ChatSession } from "@/lib/api";
import { useUi } from "@/lib/ui";

type ChatSessionsSidebarProps = {
  sessions: ChatSession[];
  activeSessionId: string | null;
  loading?: boolean;
  onNewSession: () => void;
  onSelectSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, title: string) => Promise<void> | void;
  onDeleteSession: (sessionId: string) => Promise<void> | void;
};

export default function ChatSessionsSidebar({
  sessions,
  activeSessionId,
  loading = false,
  onNewSession,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
}: ChatSessionsSidebarProps) {
  const { language, t } = useUi();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [savingId, setSavingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const startRename = (session: ChatSession) => {
    setEditingId(session.id);
    setEditingTitle(session.title);
  };

  const submitRename = async (sessionId: string) => {
    const nextTitle = editingTitle.trim();
    if (!nextTitle) {
      setEditingId(null);
      return;
    }

    try {
      setSavingId(sessionId);
      await onRenameSession(sessionId, nextTitle);
      setEditingId(null);
    } finally {
      setSavingId(null);
    }
  };

  const submitDelete = async (sessionId: string) => {
    try {
      setDeletingId(sessionId);
      await onDeleteSession(sessionId);
      if (editingId === sessionId) setEditingId(null);
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (iso: string) => {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", {
      day: "2-digit",
      month: "2-digit",
    });
  };

  return (
    <aside className="flex h-full flex-col">
      <div className="flex items-center gap-2 mb-3 shrink-0">
        <span className="material-symbols-outlined text-primary text-[20px]">forum</span>
        <div className="flex-1 min-w-0">
          <h2 className="font-bold text-on-surface text-sm font-headline">{t("chatSessionsTitle")}</h2>
        </div>
        <span className="text-[10px] font-bold bg-primary-container text-on-primary-container px-2 py-0.5 rounded-full">
          {sessions.length}
        </span>
      </div>

      <button
        type="button"
        onClick={onNewSession}
        className="mb-3 flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2.5 text-xs font-bold text-on-primary shadow-md shadow-primary/20 transition-all hover:bg-primary-dim active:scale-[0.98]"
      >
        <span className="material-symbols-outlined text-[16px]">add_comment</span>
        {t("newChat")}
      </button>

      <div className="flex-1 overflow-y-auto space-y-2 pr-0.5">
        {loading ? (
          <div className="rounded-xl bg-surface-container-low dark:bg-slate-800/60 px-3 py-3 text-xs font-medium text-on-surface-variant">
            {t("loadingChatSessions")}
          </div>
        ) : sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <span className="material-symbols-outlined text-3xl text-on-surface-variant mb-2">chat_bubble</span>
            <p className="text-xs font-medium text-on-surface-variant">{t("noChatSessions")}</p>
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId;

            return (
              <article
                key={session.id}
                className={`group rounded-xl p-3 transition-all ${
                  isActive
                    ? "bg-primary-container text-on-primary-container"
                    : "bg-surface-container-low dark:bg-slate-800/60 hover:bg-surface-container dark:hover:bg-slate-800"
                }`}
              >
                <div className="flex items-start gap-2">
                  {editingId === session.id ? (
                    <div className="flex min-w-0 flex-1 items-start gap-2">
                      <span className={`material-symbols-outlined mt-0.5 text-[16px] ${isActive ? "text-primary" : "text-on-surface-variant"}`}>
                        chat
                      </span>
                      <div className="min-w-0 flex-1">
                        <input
                          autoFocus
                          value={editingTitle}
                          disabled={savingId === session.id}
                          onChange={(event) => setEditingTitle(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") void submitRename(session.id);
                            if (event.key === "Escape") setEditingId(null);
                          }}
                          className="w-full rounded-lg border border-primary/50 bg-white dark:bg-slate-900 px-2 py-1 text-xs font-semibold text-on-surface outline-none focus:ring-2 focus:ring-primary/20"
                        />
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => onSelectSession(session.id)}
                      className="flex min-w-0 flex-1 items-start gap-2 text-left"
                    >
                      <span className={`material-symbols-outlined mt-0.5 text-[16px] ${isActive ? "text-primary" : "text-on-surface-variant"}`}>
                        chat
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-xs font-semibold text-on-surface">
                          {session.title || t("newChat")}
                        </span>
                        <span className="mt-1 block text-[10px] text-on-surface-variant">
                          {formatDate(session.created_at)}
                        </span>
                      </span>
                    </button>
                  )}

                  {editingId === session.id ? (
                    <button
                      type="button"
                      disabled={savingId === session.id}
                      onClick={() => void submitRename(session.id)}
                      className="rounded-lg px-1.5 py-1 text-primary hover:bg-surface-container-high disabled:opacity-50"
                      aria-label={t("saveChatName")}
                    >
                      <span className="material-symbols-outlined text-[15px]">check</span>
                    </button>
                  ) : (
                    <div className="flex items-center">
                      <button
                        type="button"
                        onClick={() => startRename(session)}
                        className="rounded-lg px-1.5 py-1 text-on-surface-variant opacity-0 transition-all hover:bg-surface-container-high hover:text-primary group-hover:opacity-100"
                        aria-label={t("renameChat")}
                      >
                        <span className="material-symbols-outlined text-[15px]">edit</span>
                      </button>
                      <button
                        type="button"
                        disabled={deletingId === session.id}
                        onClick={() => void submitDelete(session.id)}
                        className="rounded-lg px-1.5 py-1 text-on-surface-variant opacity-0 transition-all hover:bg-red-50 hover:text-error disabled:opacity-50 dark:hover:bg-red-950/30 group-hover:opacity-100"
                        aria-label={t("deleteChat")}
                      >
                        <span className="material-symbols-outlined text-[15px]">delete</span>
                      </button>
                    </div>
                  )}
                </div>
              </article>
            );
          })
        )}
      </div>
    </aside>
  );
}
