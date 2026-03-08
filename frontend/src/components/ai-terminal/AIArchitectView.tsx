import { useEffect, useRef } from "react";
import { useAIStore } from "@/stores/ai-store";
import { useAIChat } from "@/hooks/use-ai-chat";
import { TerminalHeader } from "./TerminalHeader";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";

export function AIArchitectView() {
  const { messages, isTyping, addMessage, clearHistory } = useAIStore();
  const { mutate: sendMessage } = useAIChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isTyping]);

  const handleSend = (text: string) => {
    addMessage({ role: "user", content: text });
    sendMessage(text);
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-[#09090b]">
      <TerminalHeader onClear={clearHistory} />
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar"
      >
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>
      <ChatInput onSend={handleSend} disabled={isTyping} />
    </div>
  );
}
