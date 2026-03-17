"use client";

import { useMemo, useState } from "react";

import { uploadFile } from "@/lib/api";
import { useUi } from "@/lib/ui";

type FileUploadProps = {
  workspaceId: string;
  onUploaded: () => void;
};

const ACCEPTED = [".pdf", ".txt", ".md"];

export default function FileUpload({ workspaceId, onUploaded }: FileUploadProps) {
  const { t } = useUi();
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileSummary = useMemo(() => {
    if (files.length === 0) {
      return t("noFiles");
    }
    return `${files.length} file(s) ready`;
  }, [files, t]);

  const handleUpload = async () => {
    if (files.length === 0) {
      return;
    }

    try {
      setError(null);
      setIsUploading(true);
      await uploadFile(files, workspaceId);
      setFiles([]);
      onUploaded();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload error";
      setError(message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200/80 bg-white/95 p-5 shadow-card backdrop-blur animate-rise dark:border-slate-700 dark:bg-slate-900/80">
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-ink dark:text-slate-100">{t("uploadTitle")}</h2>
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{t("acceptedTypes")}: {ACCEPTED.join(", ")}</p>
      </div>

      <label className="group block cursor-pointer rounded-lg border border-dashed border-slate-300 bg-gradient-to-b from-slate-50 to-white p-4 transition hover:border-moss/60 hover:from-emerald-50/40 hover:to-white dark:border-slate-700 dark:from-slate-950 dark:to-slate-900 dark:hover:border-emerald-700/70">
        <input
          type="file"
          className="hidden"
          multiple
          accept={ACCEPTED.join(",")}
          onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
        />
        <div className="flex items-center gap-3">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-slate-200/70 text-slate-700 group-hover:bg-emerald-100 group-hover:text-emerald-700 dark:bg-slate-800 dark:text-slate-200 dark:group-hover:bg-emerald-900/40 dark:group-hover:text-emerald-300">
            +
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Choose files</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">PDF, TXT, MD</p>
          </div>
        </div>
      </label>

      <p className="mt-3 text-xs text-slate-600 dark:text-slate-400">{fileSummary}</p>

      {files.length > 0 ? (
        <div className="mt-3 max-h-28 space-y-1 overflow-auto rounded-md border border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-950">
          {files.map((file) => (
            <p key={file.name} className="truncate text-xs text-slate-700 dark:text-slate-300">
              {file.name}
            </p>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        onClick={handleUpload}
        disabled={isUploading || files.length === 0}
        className="mt-4 w-full rounded-md bg-gradient-to-r from-clay to-moss px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-105 disabled:cursor-not-allowed disabled:from-slate-400 disabled:to-slate-400 disabled:opacity-70"
      >
        {isUploading ? t("uploading") : t("upload")}
      </button>

      {error ? <p className="mt-3 text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
