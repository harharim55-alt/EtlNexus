import type { UserInfo } from "@/types/auth";

export function isAdmin(user: UserInfo | null): boolean {
  return user?.role === "admin";
}
