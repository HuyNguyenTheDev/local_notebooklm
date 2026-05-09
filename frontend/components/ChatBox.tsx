"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ChatMessage, ChatSession, getChatMessages, getChatSessions, sendChat } from "@/lib/api";
import { useUi } from "@/lib/ui";
import MessageBubble from "@/components/MessageBubble";

type ChatBoxProps = {
  workspaceId: string;
};

export default function ChatBox({ workspaceId }: ChatBoxProps) {
  const { t } = useUi();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const hasMessages = useMemo(() => messages.length > 0, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const loadSessionMessages = useCallback(async (sessionId: string) => {
    setIsLoadingHistory(true);
    try {
      const data = await getChatMessages(sessionId);
      setMessages(data);
      setActiveSessionId(sessionId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load chat history";
      setMessages([{ role: "assistant", content: `Unable to load chat history: ${message}` }]);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const refreshSessions = useCallback(async () => {
    const data = await getChatSessions(workspaceId);
    setSessions(data);
    return data;
  }, [workspaceId]);

  useEffect(() => {
    let cancelled = false;

    const loadInitialHistory = async () => {
      setMessages([]);
      setActiveSessionId(null);
      try {
        const data = await getChatSessions(workspaceId);
        if (cancelled) return;
        setSessions(data);
        if (data.length > 0) {
          const latestSessionId = data[0].id;
          const history = await getChatMessages(latestSessionId);
          if (cancelled) return;
          setMessages(history);
          setActiveSessionId(latestSessionId);
        }
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setSessions([]);
      }
    };

    void loadInitialHistory();

    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  const handleNewChat = () => {
    setQuestion("");
    setMessages([]);
    setActiveSessionId(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isTyping) return;

    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);

    try {
      setIsTyping(true);
      const data = await sendChat(trimmed, workspaceId, activeSessionId);
      setActiveSessionId(data.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
      void refreshSessions();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Chat error";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Unable to answer now: ${message}` },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex h-full flex-col rounded-xxl bg-surface-container-lowest dark:bg-slate-900 overflow-hidden border border-outline-variant/10">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-outline-variant/10 bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm shrink-0">
        <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shadow-sm">
          <span
            className="material-symbols-outlined text-on-primary text-[18px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            smart_toy
          </span>
        </div>
        <div className="flex-1">
          <h2 className="font-bold text-on-surface text-sm font-headline">{t("chatTitle")}</h2>
          <p className="text-[11px] text-on-surface-variant">{t("chatHint")}</p>
        </div>
        <div className="flex items-center gap-2">
          {sessions.length > 0 && (
            <select
              value={activeSessionId ?? ""}
              onChange={(event) => {
                const nextSessionId = event.target.value;
                if (!nextSessionId) {
                  handleNewChat();
                  return;
                }
                void loadSessionMessages(nextSessionId);
              }}
              className="max-w-32 rounded-lg bg-surface-container-low dark:bg-slate-800 px-2 py-1 text-[11px] font-medium text-on-surface-variant outline-none hover:text-on-surface"
              disabled={isTyping || isLoadingHistory}
            >
              <option value="">New chat</option>
              {sessions.map((session, index) => (
                <option key={session.id} value={session.id}>
                  Chat {sessions.length - index}
                </option>
              ))}
            </select>
          )}
          {hasMessages && (
            <button
              type="button"
              onClick={handleNewChat}
              className="text-[11px] font-medium text-on-surface-variant hover:text-error transition-colors px-2 py-1 rounded-lg hover:bg-surface-container-low"
            >
              {t("clearChat")}
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 bg-gradient-to-b from-surface-container-lowest to-surface-container-low dark:from-slate-900 dark:to-slate-950">
        {isLoadingHistory ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-xs font-medium text-on-surface-variant">Loading chat history...</div>
          </div>
        ) : !hasMessages ? (
          <div className="flex h-full flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-primary-container flex items-center justify-center mb-4">
              <span
                className="material-symbols-outlined text-primary text-[28px]"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                chat_bubble
              </span>
            </div>
            <p className="font-bold text-on-surface text-sm mb-1">{t("startQuestion")}</p>
            <p className="text-xs text-on-surface-variant max-w-xs leading-relaxed">
              {t("startQuestionHint")}
            </p>

            {/* Suggested questions */}
            <div className="mt-6 flex flex-col gap-2 w-full max-w-sm">
              {[t("suggestedQ1"), t("suggestedQ2"), t("suggestedQ3")].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setQuestion(suggestion)}
                  className="text-left px-4 py-2.5 rounded-xl bg-surface-container dark:bg-slate-800 hover:bg-surface-container-high hover:text-primary text-xs font-medium text-on-surface-variant transition-all border border-outline-variant/20 hover:border-primary/30"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <MessageBubble key={index} message={message} />
            ))}
            {isTyping && (
              <div className="flex items-end gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shrink-0">
                  <span
                    className="material-symbols-outlined text-on-primary text-[15px]"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    smart_toy
                  </span>
                </div>
                <div className="flex items-center gap-1.5 bg-white dark:bg-slate-800 px-4 py-3 rounded-2xl rounded-bl-sm shadow-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                  <span className="text-xs text-on-surface-variant ml-1">{t("typing")}</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-outline-variant/10 bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm shrink-0">
        <form onSubmit={handleSubmit} className="flex gap-2.5 items-end">
          <div className="flex-1 relative">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSubmit(e as unknown as FormEvent<HTMLFormElement>);
                }
              }}
              placeholder={t("chatPlaceholder")}
              rows={1}
              className="w-full rounded-xl border border-outline-variant/40 bg-surface-container-low dark:bg-slate-800 px-4 py-3 text-sm outline-none transition-all resize-none placeholder:text-on-surface-variant focus:border-primary focus:ring-2 focus:ring-primary/15 dark:text-slate-100 leading-relaxed"
              style={{ minHeight: "44px", maxHeight: "120px" }}
            />
          </div>
          <button
            type="submit"
            disabled={isTyping || !question.trim()}
            className="w-11 h-11 flex items-center justify-center rounded-xl bg-primary text-on-primary shadow-md shadow-primary/20 transition-all hover:bg-primary-dim active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 shrink-0"
            aria-label={t("send")}
          >
            <span className="material-symbols-outlined text-[20px]">send</span>
          </button>
        </form>
        {/* <p className="text-[10px] text-on-surface-variant mt-2 text-center">
          {t("chatInputHint")}
        </p> */}
      </div>
    </div>
  );
}
