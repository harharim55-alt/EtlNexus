import { describe, it, expect } from "vitest";
import { isAdmin } from "@/lib/permissions";
import type { UserInfo } from "@/types/auth";

const makeUser = (role: string): UserInfo => ({
  id: "1",
  email: "test@example.com",
  display_name: "Test User",
  role,
  is_active: true,
  teams: [],
});

describe("isAdmin", () => {
  it("returns true for admin role", () => {
    expect(isAdmin(makeUser("admin"))).toBe(true);
  });

  it("returns false for member role", () => {
    expect(isAdmin(makeUser("member"))).toBe(false);
  });

  it("returns false for viewer role", () => {
    expect(isAdmin(makeUser("viewer"))).toBe(false);
  });

  it("returns false for null user", () => {
    expect(isAdmin(null)).toBe(false);
  });
});
