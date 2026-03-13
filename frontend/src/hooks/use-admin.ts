import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUsers,
  updateUserRole,
  fetchTeams,
  fetchTeamDetail,
  fetchGrants,
  createGrant,
  deleteGrant,
} from "@/api/admin";
import type { VisibilityGrantRequest } from "@/types/admin";
import { toast } from "sonner";

const USERS_PAGE_SIZE = 100;
const GRANTS_PAGE_SIZE = 100;

export function useAdminUsers(enabled = true) {
  return useInfiniteQuery({
    queryKey: ["admin-users"],
    queryFn: ({ pageParam = 0 }) => fetchUsers(pageParam, USERS_PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    staleTime: 2 * 60_000,
    enabled,
  });
}

export function useAdminTeams(enabled = true) {
  return useQuery({
    queryKey: ["admin-teams"],
    queryFn: fetchTeams,
    staleTime: 2 * 60_000,
    enabled,
  });
}

export function useTeamDetail(teamId: string | null) {
  return useQuery({
    queryKey: ["admin-team-detail", teamId],
    queryFn: () => fetchTeamDetail(teamId!),
    enabled: !!teamId,
    staleTime: 2 * 60_000,
  });
}

export function useAdminGrants(enabled = true) {
  return useInfiniteQuery({
    queryKey: ["admin-grants"],
    queryFn: ({ pageParam = 0 }) => fetchGrants(pageParam, GRANTS_PAGE_SIZE),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
    staleTime: 2 * 60_000,
    enabled,
  });
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      updateUserRole(userId, role),
    onSuccess: () => {
      toast.success("Role updated");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => {
      toast.error("Failed to update role");
    },
  });
}

export function useCreateGrant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: VisibilityGrantRequest) => createGrant(body),
    onSuccess: () => {
      toast.success("Grant created");
      queryClient.invalidateQueries({ queryKey: ["admin-grants"] });
    },
    onError: () => {
      toast.error("Failed to create grant");
    },
  });
}

export function useDeleteGrant() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (grantId: string) => deleteGrant(grantId),
    onSuccess: () => {
      toast.success("Grant revoked");
      queryClient.invalidateQueries({ queryKey: ["admin-grants"] });
    },
    onError: () => {
      toast.error("Failed to revoke grant");
    },
  });
}
