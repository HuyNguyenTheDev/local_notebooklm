import { ChatMessage } from "@/lib/api";

type MessageBubbleProps = {
  message: ChatMessage;
};

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={[
          "max-w-[80%] rounded-lg px-4 py-3 text-sm leading-relaxed shadow-sm",
          isUser
            ? "bg-moss text-white"
            : "bg-white text-ink border border-slate-200 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100",
        ].join(" ")}
      >
        {message.content}
      </div>
    </div>
  );
}
