import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchMe } from "@/api/auth";
import { useAuthStore } from "@/stores/auth-store";

export function useCurrentUser() {
  const token = useAuthStore((s) => s.token);
  const setUser = useAuthStore((s) => s.setUser);

  const query = useQuery({
    queryKey: ["auth", "me", token],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return fetchMe(token);
    },
    enabled: !!token,
    staleTime: 5 * 60_000,
    retry: 1,
  });

  useEffect(() => {
    if (query.data) setUser(query.data);
  }, [query.data, setUser]);

  return query;
}
