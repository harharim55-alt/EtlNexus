import { Bot, User } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/types/ai";

interface ChatMessageProps {
  message: ChatMessageType;
}

function parseBold(text: string): React.ReactNode[] {
  const parts = text.split(/\*\*(.*?)\*\*/g);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="text-foreground font-semibold">
        {part}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0 mt-0.5">
          <Bot className="w-4 h-4 text-indigo-400" />
        </div>
      )}
      <div
        className={`max-w-[80%] px-4 py-2.5 rounded-xl text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-500/10 border border-indigo-500/20 text-text-primary"
            : "bg-hover-bg border border-border text-text-primary"
        }`}
      >
        {parseBold(message.content)}
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-lg bg-hover-bg border border-border-prominent flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-text-secondary" />
        </div>
      )}
    </div>
  );
}
