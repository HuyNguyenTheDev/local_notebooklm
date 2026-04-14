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
    // App
    appTitle: "Local NotebookLM",
    aiActive: "AI Active",
    searchPlaceholder: "Search sources...",
    // Workspace
    pickWorkspace: "Your Workspaces",
    createWorkspace: "Create Workspace",
    workspaceName: "Workspace name...",
    workspaceHint: "Each workspace stores its own documents and chat context.",
    enterWorkspace: "Enter",
    noWorkspace: "No workspaces yet. Create one to begin.",
    workspace: "Workspace",
    workspaceCreatedAt: "Created",
    deleteWorkspace: "Delete workspace",
    newWorkspace: "New Workspace",
    yourWorkspaces: "Your Workspaces",
    createFirstWorkspace: "Create your first workspace",
    enterNameHint: "Or enter a name to create a new one",
    enterNameFirst: "Enter a name below to get started",
    supportedFormats: "Supported Formats",
    // Home hero
    heroTag: "New Workspace",
    heroTitle1: "Turn your data into",
    heroTitle2: "deep intelligence.",
    heroSubtitle: "Upload sources to create a knowledge base. AI will synthesize insights from your private documents.",
    helpTooltip: "Need help getting started?",
    // Upload
    uploadTitle: "Upload Documents",
    acceptedTypes: "Accepted",
    noFiles: "No files selected",
    upload: "Upload",
    uploading: "Uploading...",
    selectFiles: "Select Files",
    dragDropHint: "PDF, Text, or Markdown files",
    clearAll: "Clear all",
    uploadFirstSource: "Upload First Source",
    uploadNewSource: "Upload New Source",
    addSource: "Add Source",
    addSourceModalTitle: "Add Source",
    // Knowledge
    knowledgeTitle: "Knowledge Base",
    noDocs: "No documents yet.",
    noDocsHint: "Upload PDFs, text files, or markdown to build your knowledge base.",
    uploadedAt: "Uploaded",
    delete: "Delete",
    rename: "Rename",
    renaming: "Renaming...",
    renamePlaceholder: "Enter new filename...",
    indexed: "Indexed",
    // Chat
    chatTitle: "AI Assistant",
    chatHint: "Ask questions based on your workspace documents.",
    chatPlaceholder: "Ask a question from your documents...",
    send: "Send",
    typing: "Assistant is typing...",
    startQuestion: "Start by asking a question.",
    startQuestionHint: "Ask anything about your uploaded documents. The AI will synthesize answers from your knowledge base.",
    clearChat: "Clear",
    chatInputHint: "Press Enter to send · Shift+Enter for new line",
    suggestedQ1: "Summarize the key points",
    suggestedQ2: "What are the main topics?",
    suggestedQ3: "Explain the key concepts",
    // Workspace page
    sources: "Sources",
    chat: "Chat",
    allSources: "All Sources",
    filterPDFs: "PDFs",
    filterText: "Text",
    filterMarkdown: "Markdown",
    loadingKnowledge: "Loading knowledge...",
    // Nav
    navUpload: "Upload & Knowledge",
    navChat: "Chat",
    backToWorkspaces: "All workspaces",
    // Settings
    lang: "Language",
    theme: "Theme",
    light: "Light",
    dark: "Dark",
    en: "English",
    vi: "Vietnamese",
    settings: "Settings",
    help: "Help",
    // Footer
    aiSystemsActive: "AI Systems Active",
    privacy: "Privacy",
    documentation: "Documentation",
    // Tips
    tipSeparateWorkspaces: "Each workspace isolates its own documents and chat history. Create multiple for different projects.",
  },
  vi: {
    // App
    appTitle: "Local NotebookLM",
    aiActive: "AI Đang hoạt động",
    searchPlaceholder: "Tìm kiếm nguồn...",
    // Workspace
    pickWorkspace: "Workspace của bạn",
    createWorkspace: "Tạo Workspace",
    workspaceName: "Tên workspace...",
    workspaceHint: "Mỗi workspace lưu bộ tài liệu và ngữ cảnh chat riêng.",
    enterWorkspace: "Vào",
    noWorkspace: "Chưa có workspace. Hãy tạo workspace để bắt đầu.",
    workspace: "Workspace",
    workspaceCreatedAt: "Tạo ngày",
    deleteWorkspace: "Xóa workspace",
    newWorkspace: "Workspace mới",
    yourWorkspaces: "Workspace của bạn",
    createFirstWorkspace: "Tạo workspace đầu tiên",
    enterNameHint: "Hoặc nhập tên để tạo workspace mới",
    enterNameFirst: "Nhập tên bên dưới để bắt đầu",
    supportedFormats: "Định dạng hỗ trợ",
    // Home hero
    heroTag: "Workspace mới",
    heroTitle1: "Biến dữ liệu của bạn thành",
    heroTitle2: "tri thức sâu sắc.",
    heroSubtitle: "Tải tài liệu lên để xây dựng kho tri thức. AI sẽ tổng hợp thông tin từ bộ sưu tập tài liệu riêng của bạn.",
    helpTooltip: "Cần trợ giúp để bắt đầu?",
    // Upload
    uploadTitle: "Tải tài liệu lên",
    acceptedTypes: "Định dạng hỗ trợ",
    noFiles: "Chưa chọn file",
    upload: "Tải lên",
    uploading: "Đang tải...",
    selectFiles: "Chọn tệp",
    dragDropHint: "PDF, văn bản hoặc Markdown",
    clearAll: "Xóa tất cả",
    uploadFirstSource: "Tải nguồn đầu tiên",
    uploadNewSource: "Tải nguồn mới",
    addSource: "Thêm nguồn",
    addSourceModalTitle: "Thêm nguồn tài liệu",
    // Knowledge
    knowledgeTitle: "Kho tri thức",
    noDocs: "Chưa có tài liệu nào.",
    noDocsHint: "Tải lên PDF, văn bản hoặc Markdown để xây dựng kho tri thức.",
    uploadedAt: "Thời gian tải",
    delete: "Xóa",
    rename: "Đổi tên",
    renaming: "Đang đổi tên...",
    renamePlaceholder: "Nhập tên file mới...",
    indexed: "Đã lập chỉ mục",
    // Chat
    chatTitle: "Trợ lý AI",
    chatHint: "Đặt câu hỏi dựa trên tài liệu của workspace này.",
    chatPlaceholder: "Nhập câu hỏi từ tài liệu...",
    send: "Gửi",
    typing: "Trợ lý đang trả lời...",
    startQuestion: "Hãy bắt đầu bằng một câu hỏi.",
    startQuestionHint: "Đặt bất kỳ câu hỏi nào về tài liệu đã tải lên. AI sẽ tổng hợp câu trả lời từ kho tri thức.",
    clearChat: "Xóa",
    chatInputHint: "Nhấn Enter để gửi · Shift+Enter để xuống dòng",
    suggestedQ1: "Tóm tắt các điểm chính",
    suggestedQ2: "Các chủ đề chính là gì?",
    suggestedQ3: "Giải thích các khái niệm quan trọng",
    // Workspace page
    sources: "Nguồn tài liệu",
    chat: "Hỏi đáp",
    allSources: "Tất cả nguồn",
    filterPDFs: "PDFs",
    filterText: "Văn bản",
    filterMarkdown: "Markdown",
    loadingKnowledge: "Đang tải kho tri thức...",
    // Nav
    navUpload: "Tài liệu & Kho tri thức",
    navChat: "Hỏi đáp",
    backToWorkspaces: "Tất cả workspace",
    // Settings
    lang: "Ngôn ngữ",
    theme: "Giao diện",
    light: "Sáng",
    dark: "Tối",
    en: "Tiếng Anh",
    vi: "Tiếng Việt",
    settings: "Cài đặt",
    help: "Trợ giúp",
    // Footer
    aiSystemsActive: "AI Đang hoạt động",
    privacy: "Quyền riêng tư",
    documentation: "Tài liệu",
    // Tips
    tipSeparateWorkspaces: "Mỗi workspace lưu tài liệu và lịch sử chat riêng biệt. Tạo nhiều workspace cho các dự án khác nhau.",
  },
};

const UiContext = createContext<UiContextType | null>(null);

export function UiProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>("vi");
  const [theme, setTheme] = useState<ThemeMode>("light");

  useEffect(() => {
    const savedLanguage = window.localStorage.getItem("ui-language") as Language | null;
    const savedTheme = window.localStorage.getItem("ui-theme") as ThemeMode | null;

    if (savedLanguage === "en" || savedLanguage === "vi") setLanguage(savedLanguage);
    if (savedTheme === "light" || savedTheme === "dark") setTheme(savedTheme);
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
  if (!context) throw new Error("useUi must be used inside UiProvider");
  return context;
}
