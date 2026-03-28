import axios from "axios";
import { useAuthStore } from "@/stores/auth-store";

// Extend Axios config with retry metadata to avoid `as any` casts
declare module "axios" {
  interface InternalAxiosRequestConfig {
    _retry?: boolean;
    _retryCount?: number;
  }
}

/** HTTP methods that are safe to retry (idempotent) */
const IDEMPOTENT_METHODS = new Set(["get", "head", "options", "put"]);

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// Attach Bearer token from auth store
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token && token !== "no-sso") {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Unified response error interceptor: handles 401 token refresh and transient 5xx retries
apiClient.interceptors.response.use(
  (response) => response,
  async (error: import("axios").AxiosError) => {
    const config = error.config;
    if (!config) return Promise.reject(error);

    const status = error.response?.status;

    // 1. Handle 401 — token refresh via OIDC signinSilent (SSO only)
    if (status === 401 && !config._retry) {
      const { ssoEnabled, logout, oidcSignout, oidcSigninSilent } =
        useAuthStore.getState();
      if (ssoEnabled && oidcSigninSilent) {
        config._retry = true;
        try {
          const oidcUser = await oidcSigninSilent();
          if (oidcUser?.access_token) {
            // Sync refreshed token to the auth store and retry the request
            useAuthStore.getState().setToken(oidcUser.access_token);
            config.headers.Authorization = `Bearer ${oidcUser.access_token}`;
            return apiClient(config);
          }
        } catch {
          // signinSilent failed — fall through to logout
        }
        logout();
        if (oidcSignout) await oidcSignout().catch(() => {});
      }
      return Promise.reject(error);
    }

    // 2. Handle transient 5xx — retry with backoff + jitter (idempotent methods only)
    const method = (config.method ?? "").toLowerCase();
    const isTransient =
      !status || status === 502 || status === 503 || status === 504;
    if (isTransient && IDEMPOTENT_METHODS.has(method)) {
      const retryCount = config._retryCount ?? 0;
      if (retryCount < 2) {
        config._retryCount = retryCount + 1;
        const jitter = Math.random() * 500;
        await new Promise((r) =>
          setTimeout(r, 1000 * (retryCount + 1) + jitter),
        );
        return apiClient(config);
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
