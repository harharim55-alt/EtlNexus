import { useMutation } from "@tanstack/react-query";
import { sendAIMessage } from "@/api/ai";
import { useAIStore } from "@/stores/ai-store";

export function useAIChat() {
  const { messages, addMessage, setTyping } = useAIStore();

  return useMutation({
    mutationFn: (prompt: string) =>
      sendAIMessage({
        message: prompt,
        history: messages,
      }),
    onMutate: () => setTyping(true),
    onSuccess: (response) =>
      addMessage({ role: "assistant", content: response.content }),
    onError: (error) => {
      // A client-side timeout (axios ECONNABORTED) is the long-LLM case, not a
      // dropped connection — say so instead of the generic "severed" message.
      const code = (error as { code?: string })?.code;
      const content =
        code === "ECONNABORTED"
          ? "The Architect took too long to respond and the request timed out. Try a more specific question, or raise AI_REQUEST_TIMEOUT_SECONDS / the API proxy timeout."
          : "Connection to Architect Core severed.";
      addMessage({ role: "assistant", content });
    },
    onSettled: () => setTyping(false),
  });
}
