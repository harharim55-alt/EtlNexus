import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuthStore } from "@/stores/auth-store";
import type { UserInfo } from "@/types/auth";

const makeUser = (role: string): UserInfo => ({
  id: "user-1",
  email: "test@example.com",
  display_name: "Test User",
  role,
  is_active: true,
  teams: [{ id: "team-1", name: "Dagger", role_in_team: "member" }],
});

beforeEach(() => {
  useAuthStore.setState({
    user: null,
    token: null,
    isAuthenticated: false,
    ssoEnabled: false,
    oidcSignout: null,
  });
});

describe("useAuthStore — initial state", () => {
  it("has null user", () => {
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("has null token", () => {
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("is not authenticated", () => {
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("has ssoEnabled false", () => {
    expect(useAuthStore.getState().ssoEnabled).toBe(false);
  });

  it("has null oidcSignout", () => {
    expect(useAuthStore.getState().oidcSignout).toBeNull();
  });
});

describe("useAuthStore — setUser", () => {
  it("sets a user and marks isAuthenticated true", () => {
    const user = makeUser("member");
    useAuthStore.getState().setUser(user);
    expect(useAuthStore.getState().user).toEqual(user);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("setting null user marks isAuthenticated false", () => {
    useAuthStore.setState({ user: makeUser("admin"), isAuthenticated: true });
    useAuthStore.getState().setUser(null);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("stores admin user role correctly", () => {
    const admin = makeUser("admin");
    useAuthStore.getState().setUser(admin);
    expect(useAuthStore.getState().user?.role).toBe("admin");
  });

  it("stores viewer user role correctly", () => {
    const viewer = makeUser("viewer");
    useAuthStore.getState().setUser(viewer);
    expect(useAuthStore.getState().user?.role).toBe("viewer");
  });

  it("preserves teams on the user object", () => {
    const user = makeUser("member");
    useAuthStore.getState().setUser(user);
    expect(useAuthStore.getState().user?.teams).toHaveLength(1);
    expect(useAuthStore.getState().user?.teams[0].name).toBe("Dagger");
  });
});

describe("useAuthStore — setToken", () => {
  it("stores a JWT token", () => {
    useAuthStore.getState().setToken("my.jwt.token");
    expect(useAuthStore.getState().token).toBe("my.jwt.token");
  });

  it("clears token when set to null", () => {
    useAuthStore.setState({ token: "my.jwt.token" });
    useAuthStore.getState().setToken(null);
    expect(useAuthStore.getState().token).toBeNull();
  });
});

describe("useAuthStore — logout", () => {
  it("clears user, token, and isAuthenticated", () => {
    useAuthStore.setState({
      user: makeUser("admin"),
      token: "some-token",
      isAuthenticated: true,
    });
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});

describe("useAuthStore — setSsoEnabled", () => {
  it("enables SSO", () => {
    useAuthStore.getState().setSsoEnabled(true);
    expect(useAuthStore.getState().ssoEnabled).toBe(true);
  });

  it("disables SSO", () => {
    useAuthStore.setState({ ssoEnabled: true });
    useAuthStore.getState().setSsoEnabled(false);
    expect(useAuthStore.getState().ssoEnabled).toBe(false);
  });
});

describe("useAuthStore — setOidcSignout", () => {
  it("stores an oidcSignout function", () => {
    const fn = vi.fn().mockResolvedValue(undefined);
    useAuthStore.getState().setOidcSignout(fn);
    expect(useAuthStore.getState().oidcSignout).toBe(fn);
  });

  it("clears oidcSignout when set to null", () => {
    useAuthStore.setState({ oidcSignout: vi.fn() });
    useAuthStore.getState().setOidcSignout(null);
    expect(useAuthStore.getState().oidcSignout).toBeNull();
  });
});
