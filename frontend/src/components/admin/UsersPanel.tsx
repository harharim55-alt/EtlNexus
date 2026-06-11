import { useMemo, useState } from "react";
import { Ban, Search } from "lucide-react";
import { useAdminUsers, useUpdateUserRole, useUpdateUserActive } from "@/hooks/use-admin";
import { LoadingState } from "@/components/shared/LoadingState";
import { ErrorState } from "@/components/shared/ErrorState";
import { EmptyState } from "@/components/shared/EmptyState";
import { UserInitials } from "@/components/shared/UserInitials";
import { ROLE_STYLES } from "@/lib/admin-styles";

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
  const updateRole = useUpdateUserRole();
  const updateActive = useUpdateUserActive();
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

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

  return (
    <div className="space-y-3">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-3.5 text-text-faint" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by name or email..."
          className="w-full bg-surface-alt border border-border rounded-lg pl-9 pr-3 py-2 text-sm text-foreground placeholder:text-text-faint focus:outline-none focus:border-indigo-500/40 transition-colors"
        />
      </div>

      {filteredUsers.length === 0 ? (
        <EmptyState message="No users match your search" />
      ) : (
        <div className="space-y-2">
          {filteredUsers.map((u) => (
            <div
              key={u.id}
              className="bg-surface-alt border border-border rounded-xl p-4 flex items-center gap-4"
            >
              <UserInitials name={u.display_name} size="lg" />

              <div className={`flex-1 min-w-0 ${!u.is_active ? "opacity-50" : ""}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-foreground truncate">
                    {u.display_name}
                  </span>
                  {!u.is_active && (
                    <span className="text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                      deactivated
                    </span>
                  )}
                  {u.teams.length > 0 && (
                    <div className="flex items-center gap-1 flex-wrap">
                      {u.teams.map((t) => (
                        <span
                          key={t.id}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-hover-bg text-text-muted border border-border"
                        >
                          {t.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-xs text-text-muted font-mono mt-0.5 truncate">
                  {u.email}
                </p>
              </div>

              {/* Role badge / editor */}
              <div className="shrink-0">
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
                            : "text-text-faint bg-transparent border-border hover:border-border-prominent hover:text-text-secondary"
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
              <div className="shrink-0">
                <button
                  type="button"
                  onClick={() =>
                    updateActive.mutate({ userId: u.id, isActive: !u.is_active })
                  }
                  disabled={updateActive.isPending}
                  title={u.is_active ? "Deactivate user" : "Activate user"}
                  className={`p-1.5 rounded-md border transition-all cursor-pointer ${
                    u.is_active
                      ? "text-text-muted border-transparent hover:text-rose-400 hover:bg-rose-500/10 hover:border-rose-500/20"
                      : "text-rose-400 bg-rose-500/10 border-rose-500/20"
                  }`}
                >
                  <Ban className="size-3.5" />
                </button>
              </div>
            </div>
          ))}

          {hasMoreUsers && (
            <button
              type="button"
              onClick={() => fetchNextUsers()}
              disabled={isFetchingMoreUsers}
              className="w-full py-3 rounded-xl border border-dashed border-border text-text-faint hover:text-indigo-400 hover:border-indigo-500/20 transition-all cursor-pointer text-xs font-mono disabled:opacity-40"
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
