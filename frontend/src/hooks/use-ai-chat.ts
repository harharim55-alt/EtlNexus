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
    onError: () =>
      addMessage({
        role: "assistant",
        content: "Connection to Architect Core severed.",
      }),
    onSettled: () => setTyping(false),
  });
}
