import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUsers,
  updateUserRole,
  updateUserActive,
  fetchTeams,
  fetchTeamDetail,
  addTeamMember,
  removeTeamMember,
} from "@/api/admin";
import { toast } from "sonner";

const USERS_PAGE_SIZE = 100;

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

export function useUpdateUserActive() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      updateUserActive(userId, isActive),
    onSuccess: () => {
      toast.success("User status updated");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => {
      toast.error("Failed to update user status");
    },
  });
}


export function useAddTeamMember(teamId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (username: string) => addTeamMember(teamId, username),
    onSuccess: (member) => {
      toast.success(`Added ${member.display_name} to the team`);
      queryClient.invalidateQueries({ queryKey: ["admin-team-detail", teamId] });
      queryClient.invalidateQueries({ queryKey: ["admin-teams"] });
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "Failed to add member");
    },
  });
}

export function useRemoveTeamMember(teamId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => removeTeamMember(teamId, userId),
    onSuccess: () => {
      toast.success("Member removed");
      queryClient.invalidateQueries({ queryKey: ["admin-team-detail", teamId] });
      queryClient.invalidateQueries({ queryKey: ["admin-teams"] });
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? "Failed to remove member");
    },
  });
}
