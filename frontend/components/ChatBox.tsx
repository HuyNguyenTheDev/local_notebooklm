"use client";

import { FormEvent, useMemo, useState } from "react";

import { ChatMessage, sendChat } from "@/lib/api";
import { useUi } from "@/lib/ui";
import MessageBubble from "@/components/MessageBubble";

type ChatBoxProps = {
  workspaceId: string;
};

export default function ChatBox({ workspaceId }: ChatBoxProps) {
  const { t } = useUi();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);

  const hasMessages = useMemo(() => messages.length > 0, [messages]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = question.trim();
    if (!trimmed || isTyping) {
      return;
    }

    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);

    try {
      setIsTyping(true);
      const answer = await sendChat(trimmed, workspaceId);
      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
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
    <div className="flex h-full min-h-[420px] flex-col rounded-xl bg-white/90 p-5 shadow-card backdrop-blur animate-rise dark:bg-slate-900/80">
      <h2 className="text-lg font-semibold text-ink dark:text-slate-100">{t("chatTitle")}</h2>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{t("chatHint")}</p>

      <div className="mt-4 flex-1 space-y-3 overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950">
        {!hasMessages ? (
          <p className="text-sm text-slate-500 dark:text-slate-400">{t("startQuestion")}</p>
        ) : (
          messages.map((message, index) => <MessageBubble key={index} message={message} />)
        )}

        {isTyping ? (
          <div className="inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-xs text-slate-500 dark:bg-slate-900 dark:text-slate-400">
            <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400" />
            {t("typing")}
          </div>
        ) : null}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={t("chatPlaceholder")}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-moss dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
        />
        <button
          type="submit"
          disabled={isTyping || !question.trim()}
          className="rounded-md bg-pine px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {t("send")}
        </button>
      </form>
    </div>
  );
}
