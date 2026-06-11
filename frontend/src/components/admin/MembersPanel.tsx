import { useState } from "react";
import { UserPlus, X, Users } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { useTeamDetail, useAddTeamMember, useRemoveTeamMember } from "@/hooks/use-admin";
import { UserInitials } from "@/components/shared/UserInitials";

/** Membership management for a single team the admin belongs to. */
function TeamMemberCard({ teamId, teamName }: { teamId: string; teamName: string }) {
  const currentUserId = useAuthStore((s) => s.user?.id);
  const { data: team, isLoading } = useTeamDetail(teamId);
  const addMember = useAddTeamMember(teamId);
  const removeMember = useRemoveTeamMember(teamId);
  const [username, setUsername] = useState("");

  const submitAdd = () => {
    const u = username.trim();
    if (!u) return;
    addMember.mutate(u, { onSuccess: () => setUsername("") });
  };

  return (
    <div className="bg-surface-alt border border-border rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <Users className="size-4 text-emerald-400" />
        <h3 className="text-sm font-medium text-foreground">{teamName}</h3>
        <span className="text-[10px] font-mono text-text-muted">
          {team?.members.length ?? 0} members
        </span>
      </div>

      {/* Add member by username */}
      <div className="flex items-center gap-2 mb-3">
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submitAdd()}
          placeholder="Add user by username…"
          className="flex-1 bg-background border border-border-prominent rounded-lg px-3 py-1.5 text-sm text-foreground placeholder:text-text-faint focus:outline-none focus:border-indigo-500/50"
        />
        <button
          type="button"
          onClick={submitAdd}
          disabled={!username.trim() || addMember.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer"
        >
          <UserPlus className="size-3.5" /> Add
        </button>
      </div>

      {/* Member list */}
      {isLoading ? (
        <p className="text-xs text-text-faint font-mono">Loading…</p>
      ) : (
        <div className="space-y-1.5">
          {(team?.members ?? []).map((m) => {
            const isSelf = m.id === currentUserId;
            return (
              <div key={m.id} className="flex items-center gap-3 py-1.5 px-2 rounded-lg hover:bg-hover-bg">
                <UserInitials name={m.display_name} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-text-primary truncate">{m.display_name}</span>
                    <span className="text-[9px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded bg-hover-bg text-text-muted border border-border">
                      {m.role}
                    </span>
                  </div>
                  <span className="text-[11px] text-text-muted font-mono truncate">{m.email}</span>
                </div>
                <button
                  type="button"
                  onClick={() => removeMember.mutate(m.id)}
                  disabled={isSelf || removeMember.isPending}
                  title={isSelf ? "You cannot remove yourself" : "Remove from team"}
                  className="shrink-0 p-1.5 rounded-md text-text-muted enabled:hover:text-rose-400 enabled:hover:bg-rose-500/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
                >
                  <X className="size-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function MembersPanel() {
  const teams = useAuthStore((s) => s.user?.teams ?? []);

  if (teams.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        You don't belong to any team, so there are no memberships to manage.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-text-muted font-mono">
        Manage membership of your team(s). Add users by username; you can't remove yourself.
      </p>
      {teams.map((t) => (
        <TeamMemberCard key={t.id} teamId={t.id} teamName={t.name} />
      ))}
    </div>
  );
}
