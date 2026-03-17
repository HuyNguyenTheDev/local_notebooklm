"use client";

import { DocumentPreview, deleteDocument, renameDocument } from "@/lib/api";
import { useUi } from "@/lib/ui";
import { useState } from "react";

type KnowledgeListProps = {
  workspaceId: string;
  documents: DocumentPreview[];
  onDeleted: () => void;
};

function FileTypeIcon({ type }: { type: string }) {
  const normalized = type.toLowerCase();
  const label = normalized === "pdf" ? "PDF" : normalized.toUpperCase();
  const accent = normalized === "pdf" ? "text-red-600 border-red-200 bg-red-50" : "text-slate-600 border-slate-200 bg-slate-50";

  return (
    <span
      className={`inline-flex h-8 min-w-8 items-center justify-center rounded-md border px-1 text-[10px] font-bold ${accent} dark:border-slate-700 dark:bg-slate-900`}
      aria-label={label}
    >
      {label}
    </span>
  );
}

export default function KnowledgeList({ workspaceId, documents, onDeleted }: KnowledgeListProps) {
  const { language, t } = useUi();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  const formatDate = (iso: string) => {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) {
      return iso;
    }
    return date.toLocaleString(language === "vi" ? "vi-VN" : "en-US", {
      dateStyle: "medium",
      timeStyle: "short",
    });
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
    if (!editingName.trim()) {
      setEditingId(null);
      return;
    }

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
    <div className="flex flex-col h-full rounded-xl bg-white/90 p-5 shadow-card backdrop-blur animate-rise dark:bg-slate-900/80">
      <h2 className="text-lg font-semibold text-ink dark:text-slate-100">{t("knowledgeTitle")}</h2>

      <div className="mt-4 space-y-3 flex-1 overflow-auto pr-1">
        {documents.length === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">{t("noDocs")}</p>
        ) : (
          documents.map((doc) => (
            <article key={doc.id} className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-950">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <FileTypeIcon type={doc.type} />
                  <div className="min-w-0">
                    {editingId === doc.id ? (
                      <input
                        autoFocus
                        type="text"
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        placeholder={t("renamePlaceholder")}
                        className="w-full text-sm font-semibold rounded px-2 py-1 border border-slate-300 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleRenameSubmit(doc.id);
                          if (e.key === "Escape") setEditingId(null);
                        }}
                      />
                    ) : (
                      <h3 className="truncate text-sm font-semibold text-ink dark:text-slate-100">{doc.filename}</h3>
                    )}
                  </div>
                </div>
                <div className="relative">
                  {editingId === doc.id ? (
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => handleRenameSubmit(doc.id)}
                        disabled={isRenaming}
                        className="rounded-md bg-moss-500 px-2 py-1 text-xs text-white hover:bg-moss-600 disabled:opacity-50 dark:bg-moss-600 dark:hover:bg-moss-700"
                      >
                        {isRenaming ? t("renaming") : "OK"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        disabled={isRenaming}
                        className="rounded-md bg-slate-300 px-2 py-1 text-xs text-slate-700 hover:bg-slate-400 disabled:opacity-50 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => setOpenMenuId(openMenuId === doc.id ? null : doc.id)}
                        className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 transition"
                        title="More options"
                      >
                        ⋮
                      </button>

                      {openMenuId === doc.id && (
                        <div className="absolute right-0 z-50 mt-1 w-36 rounded-md border border-slate-200 bg-white shadow-lg dark:border-slate-600 dark:bg-slate-800">
                          <button
                            type="button"
                            onClick={() => handleRenameStart(doc.id, doc.filename)}
                            className="block w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-700 first:rounded-t-md"
                          >
                            {t("rename")}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(doc.id)}
                            className="block w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-slate-700 last:rounded-b-md"
                          >
                            {t("delete")}
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{t("uploadedAt")}: {formatDate(doc.created_at)}</p>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
