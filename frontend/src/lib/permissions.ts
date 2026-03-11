import type { UserInfo } from "@/types/auth";

export function isAdmin(user: UserInfo | null): boolean {
  return user?.role === "admin";
}

export function canEditPipeline(
  user: UserInfo | null,
  pipelineTeam: string | null,
): boolean {
  if (!user) return false;
  if (user.role === "admin") return true;
  if (!pipelineTeam) return true; // unassigned = anyone can edit
  return user.teams.some((t) => t.name === pipelineTeam);
}
