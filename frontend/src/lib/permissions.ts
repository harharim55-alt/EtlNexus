import type { UserInfo } from "@/types/auth";

export function isAdmin(user: UserInfo | null): boolean {
  return user?.role === "admin";
}

/** Master admins (superusers) or team-leader admins can reach Access Control. */
export function canManageAccess(user: UserInfo | null): boolean {
  return isAdmin(user) || !!user?.is_master;
}
