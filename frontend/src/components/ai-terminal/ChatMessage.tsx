import { Bot, User } from "lucide-react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import type { ChatMessage as ChatMessageType } from "@/types/ai";

interface ChatMessageProps {
  message: ChatMessageType;
}

// Compact markdown styling sized for the chat bubble (tight spacing).
const chatMarkdown: Components = {
  p: ({ children }) => <p className="my-1.5 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-5 my-1.5 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 my-1.5 space-y-0.5">{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noreferrer" className="text-indigo-400 hover:underline">
      {children}
    </a>
  ),
  h1: ({ children }) => <h1 className="text-base font-semibold text-foreground mt-2 mb-1">{children}</h1>,
  h2: ({ children }) => <h2 className="text-sm font-semibold text-foreground mt-2 mb-1">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-semibold text-foreground mt-2 mb-1">{children}</h3>,
  code: ({ className, children }) => {
    const block = (className ?? "").includes("language-");
    return block ? (
      <code className="font-mono text-xs">{children}</code>
    ) : (
      <code className="font-mono text-xs bg-background px-1 py-0.5 rounded border border-border">{children}</code>
    );
  },
  pre: ({ children }) => (
    <pre className="bg-background border border-border rounded-lg p-3 my-2 overflow-x-auto text-xs">{children}</pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-border pl-3 my-1.5 text-text-secondary">{children}</blockquote>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="text-xs border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => <th className="border border-border px-2 py-1 text-left font-semibold">{children}</th>,
  td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
};

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
        {isUser ? (
          <span className="whitespace-pre-wrap">{message.content}</span>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]} components={chatMarkdown}>
            {message.content}
          </ReactMarkdown>
        )}
      </div>
      {isUser && (
        <div className="w-7 h-7 rounded-lg bg-hover-bg border border-border-prominent flex items-center justify-center shrink-0 mt-0.5">
          <User className="w-4 h-4 text-text-secondary" />
        </div>
      )}
    </div>
  );
}
