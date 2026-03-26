import { useMemo, useState } from "react";
import { ArrowRight, Ban, ChevronDown, Search } from "lucide-react";
import { formatDateAdmin } from "@/lib/format";
import { useAdminUsers, useAdminGrants, useAdminTeams, useUpdateUserRole, useUpdateUserActive } from "@/hooks/use-admin";
import { useQuery } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { UserInitials } from "@/components/shared/UserInitials";
import { ROLE_STYLES, GRANT_LEVEL_STYLES } from "@/lib/admin-styles";

const ROLES = ["admin", "member", "viewer"] as const;

export function UsersPanel() {
  const {
    data: usersData,
    fetchNextPage: fetchNextUsers,
    hasNextPage: hasMoreUsers,
    isFetchingNextPage: isFetchingMoreUsers,
    isLoading,
    error,
    refetch,
  } = useAdminUsers();
  const users = useMemo(
    () => usersData?.pages.flatMap((p) => p.items) ?? [],
    [usersData],
  );
  const { data: grantsData } = useAdminGrants();
  const grants = useMemo(
    () => grantsData?.pages.flatMap((p) => p.items) ?? [],
    [grantsData],
  );
  const { data: teams } = useAdminTeams();
  const { data: pipelinesData } = useQuery({
    queryKey: ["pipelines-lookup"],
    queryFn: () => fetchPipelines(undefined, 0, 500),
    staleTime: 2 * 60_000,
  });
  const updateRole = useUpdateUserRole();
  const updateActive = useUpdateUserActive();
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const teamMap = useMemo(
    () => new Map((teams ?? []).map((t) => [t.id, t.name])),
    [teams],
  );
  const pipelineMap = useMemo(
    () => new Map((pipelinesData?.items ?? []).map((p) => [p.id, p.name])),
    [pipelinesData],
  );

  const filteredUsers = useMemo(() => {
    if (!searchQuery.trim()) return users;
    const q = searchQuery.toLowerCase();
    return users.filter(
      (u) =>
        u.display_name.toLowerCase().includes(q) ||
        u.email.toLowerCase().includes(q),
    );
  }, [users, searchQuery]);

  if (isLoading) return <LoadingState />;
  if (error) return <ErrorState message="Failed to load users" onRetry={refetch} />;
  if (users.length === 0) return <EmptyState message="No users found" />;

  const toggleExpand = (userId: string) => {
    setExpandedUserId((prev) => (prev === userId ? null : userId));
  };

  const getUserGrants = (userId: string) =>
    grants.filter((g) => g.grantee_user_id === userId);

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-slate-600" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by name or email..."
          className="w-full bg-[#0f0f11] border border-white/[0.06] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/40 transition-colors"
        />
      </div>

      {filteredUsers.length === 0 ? (
        <EmptyState message="No users match your search" />
      ) : (
        <div className="space-y-2">
          {filteredUsers.map((u) => {
            const isExpanded = expandedUserId === u.id;
            const userGrants = isExpanded ? getUserGrants(u.id) : [];

            return (
              <div
                key={u.id}
                className={`bg-[#0f0f11] border rounded-xl transition-colors ${
                  isExpanded
                    ? "border-indigo-500/20"
                    : "border-white/[0.04] hover:border-white/[0.08]"
                }`}
              >
                <div
                  className="p-4 flex items-center gap-4 cursor-pointer"
                  onClick={() => toggleExpand(u.id)}
                >
                  <UserInitials name={u.display_name} size="lg" />

                  <div className={`flex-1 min-w-0 ${!u.is_active ? "opacity-50" : ""}`}>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white truncate">
                        {u.display_name}
                      </span>
                      {!u.is_active && (
                        <span className="text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          deactivated
                        </span>
                      )}
                      {u.teams.length > 0 && (
                        <div className="flex items-center gap-1">
                          {u.teams.map((t) => (
                            <span
                              key={t.id}
                              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.04] text-slate-500 border border-white/[0.06]"
                            >
                              {t.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 font-mono mt-0.5 truncate">
                      {u.email}
                    </p>
                  </div>

                  {/* Role badge / editor */}
                  <div
                    className="shrink-0"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {editingUserId === u.id ? (
                      <div className="flex items-center gap-1">
                        {ROLES.map((role) => (
                          <button
                            key={role}
                            type="button"
                            disabled={updateRole.isPending}
                            onClick={() => {
                              if (role !== u.role) {
                                updateRole.mutate(
                                  { userId: u.id, role },
                                  { onSettled: () => setEditingUserId(null) },
                                );
                              } else {
                                setEditingUserId(null);
                              }
                            }}
                            className={`text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-md border transition-all cursor-pointer ${
                              role === u.role
                                ? ROLE_STYLES[role]
                                : "text-slate-600 bg-transparent border-white/[0.06] hover:border-white/10 hover:text-slate-400"
                            }`}
                          >
                            {role}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setEditingUserId(u.id)}
                        className={`text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded-md border cursor-pointer transition-all hover:brightness-125 ${ROLE_STYLES[u.role] ?? ROLE_STYLES.viewer}`}
                      >
                        {u.role}
                      </button>
                    )}
                  </div>

                  {/* Activate / deactivate toggle */}
                  <div
                    className="shrink-0"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        updateActive.mutate({
                          userId: u.id,
                          isActive: !u.is_active,
                        })
                      }
                      disabled={updateActive.isPending}
                      title={u.is_active ? "Deactivate user" : "Activate user"}
                      className={`p-1.5 rounded-md border transition-all cursor-pointer ${
                        u.is_active
                          ? "text-slate-500 border-transparent hover:text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/20"
                          : "text-rose-400 bg-rose-500/10 border-rose-500/20"
                      }`}
                    >
                      <Ban className="size-3.5" />
                    </button>
                  </div>

                  <ChevronDown
                    className={`size-4 text-slate-600 shrink-0 transition-transform ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                  />
                </div>

                {/* Expanded grants section */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-0 border-t border-white/[0.04]">
                    <div className="pt-3">
                      <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
                        User Grants ({userGrants.length})
                      </span>
                      {userGrants.length === 0 ? (
                        <p className="text-xs text-slate-600 mt-2">
                          No grants assigned to this user
                        </p>
                      ) : (
                        <div className="mt-2 space-y-1.5">
                          {userGrants.map((g) => {
                            const target = g.pipeline_id
                              ? pipelineMap.get(g.pipeline_id) ?? g.pipeline_id
                              : g.source_team_id
                                ? `All of ${g.source_team_name ?? teamMap.get(g.source_team_id) ?? "Unknown"}`
                                : "Unknown";
                            return (
                              <div
                                key={g.id}
                                className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-white/[0.02]"
                              >
                                <ArrowRight className="size-3 text-slate-600 shrink-0" />
                                <span
                                  className={`text-xs ${
                                    g.pipeline_id
                                      ? "text-indigo-400 font-mono"
                                      : "text-teal-400"
                                  }`}
                                >
                                  {target}
                                </span>
                                <span
                                  className={`text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border shrink-0 ${
                                    GRANT_LEVEL_STYLES[g.grant_level] ?? GRANT_LEVEL_STYLES.viewer
                                  }`}
                                >
                                  {g.grant_level}
                                </span>
                                <span className="text-[10px] font-mono text-slate-600 ml-auto">
                                  {formatDateAdmin(g.created_at)}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {hasMoreUsers && (
            <button
              type="button"
              onClick={() => fetchNextUsers()}
              disabled={isFetchingMoreUsers}
              className="w-full py-3 rounded-xl border border-dashed border-white/[0.06] text-slate-600 hover:text-indigo-400 hover:border-indigo-500/20 transition-all cursor-pointer text-xs font-mono disabled:opacity-40"
            >
              {isFetchingMoreUsers
                ? "Loading..."
                : `Load more (${users.length} of ${usersData?.pages[0]?.total ?? 0})`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
