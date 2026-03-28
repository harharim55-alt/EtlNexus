import { create } from "zustand";
import type { User } from "oidc-client-ts";
import type { UserInfo } from "@/types/auth";

interface AuthState {
  user: UserInfo | null;
  token: string | null;
  isAuthenticated: boolean;
  ssoEnabled: boolean;
  oidcSignout: (() => Promise<void>) | null;
  /** OIDC signinSilent callback for non-React contexts (e.g. axios 401 interceptor) */
  oidcSigninSilent: (() => Promise<User | null>) | null;
  setUser: (user: UserInfo | null) => void;
  setToken: (token: string | null) => void;
  logout: () => void;
  setSsoEnabled: (enabled: boolean) => void;
  setOidcSignout: (fn: (() => Promise<void>) | null) => void;
  setOidcSigninSilent: (fn: (() => Promise<User | null>) | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  ssoEnabled: false,
  oidcSignout: null,
  oidcSigninSilent: null,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setToken: (token) => set({ token }),
  logout: () => set({ user: null, token: null, isAuthenticated: false }),
  setSsoEnabled: (enabled) => set({ ssoEnabled: enabled }),
  setOidcSignout: (fn) => set({ oidcSignout: fn }),
  setOidcSigninSilent: (fn) => set({ oidcSigninSilent: fn }),
}));
