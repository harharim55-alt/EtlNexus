import { useState } from "react";
import { SendHorizonal } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  return (
    <div className="border-t border-border p-4">
      <div className="flex gap-3 items-center bg-card border border-border rounded-xl px-4 py-2.5">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="Ask about pipelines, joins, or architecture..."
          disabled={disabled}
          className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-faint outline-none font-mono"
        />
        <button
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          className="text-indigo-400 hover:text-indigo-300 disabled:text-text-faint transition-colors"
        >
          <SendHorizonal className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
