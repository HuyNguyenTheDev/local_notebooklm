"use client";

import { use, useCallback, useEffect, useState } from "react";

import ChatBox from "@/components/ChatBox";
import FileUpload from "@/components/FileUpload";
import KnowledgeList from "@/components/KnowledgeList";
import { DocumentPreview, getDocuments } from "@/lib/api";
import { useUi } from "@/lib/ui";

type WorkspaceEntryPageProps = {
  params: Promise<{
    workspaceId: string;
  }>;
};

export default function WorkspaceEntryPage({ params }: WorkspaceEntryPageProps) {
  const { t } = useUi();
  const { workspaceId: rawWorkspaceId } = use(params);
  const workspaceId = decodeURIComponent(rawWorkspaceId);

  const [documents, setDocuments] = useState<DocumentPreview[]>([]);
  const [loading, setLoading] = useState(true);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getDocuments(workspaceId);
      setDocuments(data);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  return (
    <main className="min-h-screen px-4 py-6 flex flex-col">
      <div className="mx-auto max-w-7xl w-full flex-1 flex flex-col">
        <section className="grid grid-cols-1 gap-5 lg:grid-cols-12 h-full">
          <div className="lg:col-span-3 flex flex-col">
            <FileUpload workspaceId={workspaceId} onUploaded={loadDocuments} />
          </div>

          <div className="lg:col-span-6 flex flex-col">
            <ChatBox workspaceId={workspaceId} />
          </div>

          <div className="lg:col-span-3 flex flex-col">
            {loading ? (
              <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-card dark:border-slate-700 dark:bg-slate-900">
                {t("loadingKnowledge")}
              </div>
            ) : (
              <KnowledgeList workspaceId={workspaceId} documents={documents} onDeleted={loadDocuments} />
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
