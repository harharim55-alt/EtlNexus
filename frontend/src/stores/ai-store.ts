import { create } from "zustand";
import type { ChatMessage } from "@/types/ai";

// Fallback greeting; the real one comes from the backend (AI_GREETING) via
// /api/auth/config and is applied with setGreeting() at startup.
const DEFAULT_GREETING =
  "Hello! I am your AI Data Architect. You can ask me about the existing data products " +
  "or look for a data product that matches your needs. Where would you like to start?";

interface AIState {
  greeting: string;
  messages: ChatMessage[];
  isTyping: boolean;
  addMessage: (msg: ChatMessage) => void;
  setTyping: (typing: boolean) => void;
  clearHistory: () => void;
  /** Set the opening greeting (from server config); reset the chat if not started. */
  setGreeting: (text: string) => void;
}

export const useAIStore = create<AIState>((set, get) => ({
  greeting: DEFAULT_GREETING,
  messages: [{ role: "assistant", content: DEFAULT_GREETING }],
  isTyping: false,
  addMessage: (msg) => set((state) => ({ messages: [...state.messages, msg] })),
  setTyping: (typing) => set({ isTyping: typing }),
  clearHistory: () => set({ messages: [{ role: "assistant", content: get().greeting }], isTyping: false }),
  setGreeting: (text) => {
    if (!text) return;
    const { messages } = get();
    // Only the untouched opening message? Replace it so the new greeting shows.
    const fresh = messages.length <= 1 && messages[0]?.role === "assistant";
    set({ greeting: text, ...(fresh ? { messages: [{ role: "assistant", content: text }] } : {}) });
  },
}));
