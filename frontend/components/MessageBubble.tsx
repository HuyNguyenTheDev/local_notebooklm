import { ChatMessage } from "@/lib/api";

type MessageBubbleProps = {
  message: ChatMessage;
};

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex items-end gap-2.5 animate-fadeIn ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
          isUser
            ? "bg-surface-container-high dark:bg-slate-700"
            : "bg-primary"
        }`}
      >
        {isUser ? (
          <span className="material-symbols-outlined text-on-surface-variant text-[16px]">person</span>
        ) : (
          <span
            className="material-symbols-outlined text-on-primary text-[16px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            smart_toy
          </span>
        )}
      </div>

      {/* Bubble */}
      <div
        className={[
          "max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
          isUser
            ? "bg-primary text-on-primary rounded-br-sm"
            : "bg-white dark:bg-slate-800 text-on-surface dark:text-slate-100 border border-outline-variant/20 rounded-bl-sm",
        ].join(" ")}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
