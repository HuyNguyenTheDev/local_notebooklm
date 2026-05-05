export type DocumentPreview = {
  id: string;
  filename: string;
  type: string;
  preview: string;
  created_at: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type WorkspacePreview = {
  workspace_id: string;
  created_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

export async function uploadFile(files: File[], workspaceId: string): Promise<DocumentPreview[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("workspace_id", workspaceId);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Upload failed: ${detail}`);
  }

  return response.json();
}

export async function getDocuments(workspaceId: string): Promise<DocumentPreview[]> {
  const query = new URLSearchParams({ workspace_id: workspaceId }).toString();
  const response = await fetch(`${API_BASE_URL}/documents?${query}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error("Failed to fetch documents");
  }

  return response.json();
}

export async function createWorkspace(workspaceId: string): Promise<WorkspacePreview> {
  const query = new URLSearchParams({ workspace_id: workspaceId }).toString();
  const response = await fetch(`${API_BASE_URL}/documents/workspaces?${query}`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Failed to create workspace");
  }

  return response.json();
}

export async function searchWorkspaces(query: string): Promise<WorkspacePreview[]> {
  const q = new URLSearchParams({ q: query }).toString();
  const response = await fetch(`${API_BASE_URL}/documents/workspaces/search?${q}`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error("Failed to search workspaces");
  }

  return response.json();
}

export async function getWorkspaces(): Promise<WorkspacePreview[]> {
  const response = await fetch(`${API_BASE_URL}/documents/workspaces`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error("Failed to fetch workspaces");
  }

  return response.json();
}

export async function deleteDocument(id: string, workspaceId: string): Promise<void> {
  const query = new URLSearchParams({ workspace_id: workspaceId }).toString();
  const response = await fetch(`${API_BASE_URL}/documents/${id}?${query}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to delete document");
  }
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/documents/workspace/${encodeURIComponent(workspaceId)}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error("Failed to delete workspace");
  }
}

export async function renameDocument(id: string, newFilename: string, workspaceId: string): Promise<void> {
  const query = new URLSearchParams({ workspace_id: workspaceId, new_filename: newFilename }).toString();
  const response = await fetch(`${API_BASE_URL}/documents/${id}?${query}`, {
    method: "PATCH",
  });

  if (!response.ok) {
    throw new Error("Failed to rename document");
  }
}

export async function sendChat(question: string, workspaceId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, workspace_id: workspaceId }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Chat failed: ${detail}`);
  }

  const data = await response.json();
  return data.answer;
}
