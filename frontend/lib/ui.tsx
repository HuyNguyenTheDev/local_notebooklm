"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Language = "en" | "vi";
export type ThemeMode = "light" | "dark";

type Dict = Record<string, string>;

type UiContextType = {
  language: Language;
  setLanguage: (value: Language) => void;
  theme: ThemeMode;
  setTheme: (value: ThemeMode) => void;
  t: (key: string) => string;
};

const translations: Record<Language, Dict> = {
  en: {
    appTitle: "Local NotebookLM",
    pickWorkspace: "Choose a workspace",
    createWorkspace: "Create workspace",
    workspaceName: "Workspace name",
    workspaceHint: "Each workspace stores its own documents and chat context.",
    enterWorkspace: "Enter",
    noWorkspace: "No workspace yet. Create one to begin.",
    uploadTitle: "Upload Documents",
    acceptedTypes: "Accepted",
    noFiles: "No files selected",
    upload: "Upload",
    uploading: "Uploading...",
    knowledgeTitle: "Knowledge Store",
    noDocs: "No documents uploaded yet.",
    uploadedAt: "Uploaded",
    delete: "Delete",
    deleteWorkspace: "Delete workspace",
    rename: "Rename",
    renaming: "Renaming...",
    renamePlaceholder: "Enter new filename...",
    chatTitle: "Chatbot",
    chatHint: "Ask questions based on this workspace documents.",
    chatPlaceholder: "Ask a question from your documents...",
    send: "Send",
    typing: "Assistant is typing...",
    startQuestion: "Start by asking a question.",
    navUpload: "Upload & Knowledge",
    navChat: "Chat",
    backToWorkspaces: "All workspaces",
    lang: "Language",
    theme: "Theme",
    light: "Light",
    dark: "Dark",
    en: "English",
    vi: "Vietnamese",
    workspace: "Workspace",
    workspaceCreatedAt: "Created",
    loadingKnowledge: "Loading knowledge...",
  },
  vi: {
    appTitle: "Local NotebookLM",
    pickWorkspace: "Chọn workspace",
    createWorkspace: "Tạo workspace",
    workspaceName: "Tên workspace",
    workspaceHint: "Mỗi workspace lưu bộ tài liệu và ngữ cảnh chat riêng.",
    enterWorkspace: "Vào",
    noWorkspace: "Chưa có workspace. Hãy tạo workspace để bắt đầu.",
    uploadTitle: "Tải tài liệu",
    acceptedTypes: "Định dạng hỗ trợ",
    noFiles: "Chưa chọn file",
    upload: "Tải lên",
    uploading: "Đang tải...",
    knowledgeTitle: "Kho tri thức",
    noDocs: "Chưa có tài liệu nào.",
    uploadedAt: "Thời gian tải",
    delete: "Xóa",
    deleteWorkspace: "Xóa workspace",
    rename: "Đổi tên",
    renaming: "Đang đổi tên...",
    renamePlaceholder: "Nhập tên file mới...",
    chatTitle: "Trợ lý hỏi đáp",
    chatHint: "Đặt câu hỏi dựa trên tài liệu của workspace này.",
    chatPlaceholder: "Nhập câu hỏi từ tài liệu...",
    send: "Gửi",
    typing: "Trợ lý đang trả lời...",
    startQuestion: "Hãy bắt đầu bằng một câu hỏi.",
    navUpload: "Tài liệu & Kho tri thức",
    navChat: "Hỏi đáp",
    backToWorkspaces: "Tất cả workspace",
    lang: "Ngôn ngữ",
    theme: "Giao diện",
    light: "Sáng",
    dark: "Tối",
    en: "Tiếng Anh",
    vi: "Tiếng Việt",
    workspace: "Workspace",
    workspaceCreatedAt: "Tạo ngày",
    loadingKnowledge: "Đang tải kho tri thức...",
  },
};

const UiContext = createContext<UiContextType | null>(null);

export function UiProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>("vi");
  const [theme, setTheme] = useState<ThemeMode>("light");

  useEffect(() => {
    const savedLanguage = window.localStorage.getItem("ui-language") as Language | null;
    const savedTheme = window.localStorage.getItem("ui-theme") as ThemeMode | null;

    if (savedLanguage === "en" || savedLanguage === "vi") {
      setLanguage(savedLanguage);
    }

    if (savedTheme === "light" || savedTheme === "dark") {
      setTheme(savedTheme);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("ui-language", language);
  }, [language]);

  useEffect(() => {
    window.localStorage.setItem("ui-theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const value = useMemo<UiContextType>(
    () => ({
      language,
      setLanguage,
      theme,
      setTheme,
      t: (key: string) => translations[language][key] ?? key,
    }),
    [language, theme],
  );

  return <UiContext.Provider value={value}>{children}</UiContext.Provider>;
}

export function useUi() {
  const context = useContext(UiContext);
  if (!context) {
    throw new Error("useUi must be used inside UiProvider");
  }
  return context;
}
