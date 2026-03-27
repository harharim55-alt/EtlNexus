import axios from "axios";
import { useAuthStore } from "@/stores/auth-store";

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

    // 1. Handle 401 — token refresh (SSO only)
    if (status === 401 && !(config as any)._retry) {
      const { ssoEnabled, token: oldToken, logout, oidcSignout } = useAuthStore.getState();
      if (ssoEnabled) {
        (config as any)._retry = true;
        // Wait for OIDC library to refresh the token
        await new Promise((r) => setTimeout(r, 2000));
        const newToken = useAuthStore.getState().token;
        if (newToken && newToken !== oldToken) {
          config.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(config);
        }
        logout();
        if (oidcSignout) await oidcSignout().catch(() => {});
      }
      return Promise.reject(error);
    }

    // 2. Handle transient 5xx — retry with backoff
    const isTransient = !status || status === 502 || status === 503 || status === 504;
    if (isTransient) {
      const retryCount = (config as any)._retryCount ?? 0;
      if (retryCount < 2) {
        (config as any)._retryCount = retryCount + 1;
        await new Promise((r) => setTimeout(r, 1000 * (retryCount + 1)));
        return apiClient(config);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
