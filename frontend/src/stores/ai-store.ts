import { create } from "zustand";
import type { ChatMessage } from "@/types/ai";

interface AIState {
  messages: ChatMessage[];
  isTyping: boolean;
  addMessage: (msg: ChatMessage) => void;
  setTyping: (typing: boolean) => void;
  clearHistory: () => void;
}

const INITIAL_MESSAGE: ChatMessage = {
  role: "assistant",
  content:
    "SYSTEM INITIALIZED. I am your automated Data Architect. State your metric objective, and I will output the required pipeline joins and transformations.",
};

export const useAIStore = create<AIState>((set) => ({
  messages: [INITIAL_MESSAGE],
  isTyping: false,
  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),
  setTyping: (typing) => set({ isTyping: typing }),
  clearHistory: () => set({ messages: [INITIAL_MESSAGE], isTyping: false }),
}));
