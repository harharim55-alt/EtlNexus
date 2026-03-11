import { useMemo, useState } from "react";
import { ArrowRight, ChevronDown, Search } from "lucide-react";
import { useAdminUsers, useAdminGrants, useAdminTeams, useUpdateUserRole } from "@/hooks/use-admin";
import { useQuery } from "@tanstack/react-query";
import { fetchPipelines } from "@/api/pipelines";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";

const ROLES = ["admin", "member", "viewer"] as const;

const ROLE_STYLES: Record<string, string> = {
  admin: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  member: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
  viewer: "text-slate-400 bg-slate-500/10 border-slate-500/20",
};

function UserInitials({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
  return (
    <div className="size-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-[11px] font-semibold text-indigo-400 select-none shrink-0">
      {initials}
    </div>
  );
}

export function UsersPanel() {
  const { data: users, isLoading, error, refetch } = useAdminUsers();
  const { data: grants } = useAdminGrants();
  const { data: teams } = useAdminTeams();
  const { data: pipelines } = useQuery({
    queryKey: ["pipelines"],
    queryFn: () => fetchPipelines(),
    staleTime: 2 * 60_000,
  });
  const updateRole = useUpdateUserRole();
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const teamMap = useMemo(
    () => new Map((teams ?? []).map((t) => [t.id, t.name])),
    [teams],
  );
  const pipelineMap = useMemo(
    () => new Map((pipelines ?? []).map((p) => [p.id, p.name])),
    [pipelines],
  );

  const filteredUsers = useMemo(() => {
    if (!users) return [];
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
  if (!users || users.length === 0) return <EmptyState message="No users found" />;

  const toggleExpand = (userId: string) => {
    setExpandedUserId((prev) => (prev === userId ? null : userId));
  };

  const getUserGrants = (userId: string) =>
    (grants ?? []).filter((g) => g.grantee_user_id === userId);

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
                  <UserInitials name={u.display_name} />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white truncate">
                        {u.display_name}
                      </span>
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
                                    g.grant_level === "editor"
                                      ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                                      : "text-slate-400 bg-white/[0.03] border-white/[0.06]"
                                  }`}
                                >
                                  {g.grant_level}
                                </span>
                                <span className="text-[10px] font-mono text-slate-600 ml-auto">
                                  {new Date(g.created_at).toLocaleDateString()}
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
        </div>
      )}
    </div>
  );
}
