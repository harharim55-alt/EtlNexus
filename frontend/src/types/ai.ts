export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AIChatRequest {
  message: string;
  history: ChatMessage[];
}

export interface AIChatResponse {
  role: "assistant";
  content: string;
}
