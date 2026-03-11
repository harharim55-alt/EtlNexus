import { useQuery } from "@tanstack/react-query";
import { fetchMe } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";

export function useCurrentUser() {
  const token = useAuthStore((s) => s.token);
  const setUser = useAuthStore((s) => s.setUser);

  return useQuery({
    queryKey: ["auth", "me", token],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      const user = await fetchMe(token);
      setUser(user);
      return user;
    },
    enabled: !!token,
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
