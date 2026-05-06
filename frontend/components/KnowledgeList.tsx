"use client";

import { useState } from "react";

import { DocumentPreview, deleteDocument, renameDocument } from "@/lib/api";
import { useUi } from "@/lib/ui";

type KnowledgeListProps = {
  workspaceId: string;
  documents: DocumentPreview[];
  onDeleted: () => void;
};

const FILE_ICONS: Record<string, string> = {
  pdf: "picture_as_pdf",
  txt: "text_snippet",
  md: "article",
};

const BADGE_COLORS: Record<string, string> = {
  pdf: "bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400",
  txt: "bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400",
  md: "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400",
};

export default function KnowledgeList({ workspaceId, documents, onDeleted }: KnowledgeListProps) {
  const { language, t } = useUi();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(language === "vi" ? "vi-VN" : "en-US", { dateStyle: "short" });
  };

  const handleDelete = async (id: string) => {
    await deleteDocument(id, workspaceId);
    setOpenMenuId(null);
    onDeleted();
  };

  const handleRenameStart = (id: string, currentName: string) => {
    setEditingId(id);
    setEditingName(currentName);
    setOpenMenuId(null);
  };

  const handleRenameSubmit = async (id: string) => {
    if (!editingName.trim()) { setEditingId(null); return; }
    try {
      setIsRenaming(true);
      await renameDocument(id, editingName, workspaceId);
      onDeleted();
    } finally {
      setEditingId(null);
      setIsRenaming(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3 shrink-0">
        <span className="material-symbols-outlined text-primary text-[20px]">layers</span>
        <div className="flex-1 min-w-0">
          <h2 className="font-bold text-on-surface text-sm font-headline">{t("knowledgeTitle")}</h2>
        </div>
        <span className="text-[10px] font-bold bg-primary-container text-on-primary-container px-2 py-0.5 rounded-full">
          {documents.length}
        </span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-0.5">
        {documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <span className="material-symbols-outlined text-3xl text-on-surface-variant mb-2">folder_open</span>
            <p className="text-xs font-medium text-on-surface-variant">{t("noDocs")}</p>
          </div>
        ) : (
          documents.map((doc, index) => (
            <article
              key={doc.id}
              className="group rounded-xl bg-surface-container-low dark:bg-slate-800/60 hover:bg-surface-container dark:hover:bg-slate-800 p-3 transition-all animate-fadeIn"
              style={{ animationDelay: `${index * 40}ms` }}
            >
              <div className="flex items-start gap-2.5">
                {/* Icon */}
                <div className="w-8 h-8 rounded-lg bg-white dark:bg-slate-700 flex items-center justify-center shrink-0 shadow-sm">
                  <span className="material-symbols-outlined text-primary text-[16px]">
                    {FILE_ICONS[doc.file_type.toLowerCase()] ?? "description"}
                  </span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  {editingId === doc.id ? (
                    <input
                      autoFocus
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      placeholder={t("renamePlaceholder")}
                      className="w-full rounded-lg border border-primary/50 bg-white dark:bg-slate-800 px-2 py-1 text-xs font-semibold outline-none focus:ring-2 focus:ring-primary/20"
                      onKeyDown={(e) => {
                        if (e.key === "Enter") void handleRenameSubmit(doc.id);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                    />
                  ) : (
                    <p className="text-xs font-semibold text-on-surface truncate group-hover:text-primary transition-colors">
                      {doc.filename}
                    </p>
                  )}
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${BADGE_COLORS[doc.file_type.toLowerCase()] ?? "bg-surface-container text-on-surface-variant"}`}>
                      {doc.file_type.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-on-surface-variant">{formatDate(doc.created_at)}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="relative shrink-0">
                  {editingId === doc.id ? (
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => void handleRenameSubmit(doc.id)}
                        disabled={isRenaming}
                        className="px-2 py-1 bg-primary text-on-primary rounded-lg text-[10px] font-bold hover:bg-primary-dim transition-colors disabled:opacity-50"
                      >
                        OK
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        disabled={isRenaming}
                        className="px-2 py-1 bg-surface-container text-on-surface-variant rounded-lg text-[10px] font-medium hover:bg-surface-container-high transition-colors"
                      >
                        ✕
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => setOpenMenuId(openMenuId === doc.id ? null : doc.id)}
                        className="w-6 h-6 flex items-center justify-center rounded-lg text-on-surface-variant opacity-0 group-hover:opacity-100 hover:bg-surface-container-high transition-all"
                      >
                        <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                        </svg>
                      </button>
                      {openMenuId === doc.id && (
                        <div className="absolute right-0 z-50 mt-1 w-40 overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 shadow-xl animate-slideIn">
                          <button
                            type="button"
                            onClick={() => handleRenameStart(doc.id, doc.filename)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-on-surface hover:bg-surface-container-low transition-colors"
                          >
                            <span className="material-symbols-outlined text-[14px]">edit</span>
                            {t("rename")}
                          </button>
                          <button
                            type="button"
                            onClick={() => void handleDelete(doc.id)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-error hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                          >
                            <span className="material-symbols-outlined text-[14px]">delete</span>
                            {t("delete")}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
