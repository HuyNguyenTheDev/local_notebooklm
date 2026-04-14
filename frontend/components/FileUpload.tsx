"use client";

import { useMemo, useState } from "react";

import { uploadFile } from "@/lib/api";
import { useUi } from "@/lib/ui";

type FileUploadProps = {
  workspaceId: string;
  onUploaded: () => void;
};

const ACCEPTED = [".pdf", ".txt", ".md"];

const FILE_ICONS: Record<string, string> = {
  pdf: "picture_as_pdf",
  txt: "text_snippet",
  md: "article",
};

function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  return FILE_ICONS[ext] ?? "description";
}

export default function FileUpload({ workspaceId, onUploaded }: FileUploadProps) {
  const { t } = useUi();
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const fileSummary = useMemo(() => {
    if (files.length === 0) return t("noFiles");
    return `${files.length} file${files.length !== 1 ? "s" : ""} ready`;
  }, [files, t]);

  const handleUpload = async () => {
    if (files.length === 0) return;
    try {
      setError(null);
      setIsUploading(true);
      await uploadFile(files, workspaceId);
      setFiles([]);
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload error");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = Array.from(e.dataTransfer.files).filter((f) =>
      ACCEPTED.some((ext) => f.name.toLowerCase().endsWith(ext)),
    );
    if (dropped.length > 0) setFiles((prev) => [...prev, ...dropped]);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Drop zone */}
      <label
        className={`group block cursor-pointer rounded-xxl border-2 border-dashed transition-all ${
          isDragging
            ? "border-primary bg-primary/5"
            : "border-outline-variant/40 hover:border-primary/50 hover:bg-primary/5"
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <input
          type="file"
          className="hidden"
          multiple
          accept={ACCEPTED.join(",")}
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        />
        <div className="flex flex-col items-center justify-center gap-3 p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-surface-container-low dark:bg-slate-800 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <span className="material-symbols-outlined text-3xl text-primary">upload_file</span>
          </div>
          <div>
            <p className="font-bold text-on-surface text-sm">{t("uploadTitle")}</p>
            <p className="text-xs text-on-surface-variant mt-1">
              {t("acceptedTypes")}: {ACCEPTED.join(", ")}
            </p>
          </div>
          <span className="px-5 py-2 bg-primary text-on-primary rounded-xl text-xs font-bold hover:bg-primary-dim transition-colors shadow-md shadow-primary/20">
            {t("selectFiles")}
          </span>
        </div>
      </label>

      {/* File list */}
      {files.length > 0 && (
        <div className="rounded-xxl bg-surface-container-low dark:bg-slate-800/60 overflow-hidden">
          <div className="px-4 py-2 border-b border-outline-variant/10 flex items-center justify-between">
            <p className="text-xs font-semibold text-on-surface-variant">{fileSummary}</p>
            <button
              type="button"
              onClick={() => setFiles([])}
              className="text-[11px] text-on-surface-variant hover:text-error transition-colors font-medium"
            >
              {t("clearAll")}
            </button>
          </div>
          <div className="max-h-36 overflow-y-auto divide-y divide-outline-variant/10">
            {files.map((file) => (
              <div key={file.name} className="flex items-center gap-3 px-4 py-2.5">
                <span className="material-symbols-outlined text-primary text-[18px] shrink-0">
                  {getFileIcon(file.name)}
                </span>
                <p className="truncate text-xs font-medium text-on-surface flex-1">{file.name}</p>
                <button
                  type="button"
                  onClick={() => setFiles((prev) => prev.filter((f) => f.name !== file.name))}
                  className="text-on-surface-variant hover:text-error transition-colors shrink-0"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload button */}
      <button
        type="button"
        onClick={handleUpload}
        disabled={isUploading || files.length === 0}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-bold text-on-primary shadow-md shadow-primary/20 transition-all hover:bg-primary-dim active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isUploading ? (
          <>
            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>{t("uploading")}</span>
          </>
        ) : (
          <>
            <span className="material-symbols-outlined text-[18px]">cloud_upload</span>
            <span>{t("upload")}</span>
          </>
        )}
      </button>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 rounded-xl bg-error/10 border border-error/20 px-3 py-2.5">
          <span className="material-symbols-outlined text-error text-[18px]">error_outline</span>
          <p className="text-xs font-medium text-error">{error}</p>
        </div>
      )}
    </div>
  );
}
