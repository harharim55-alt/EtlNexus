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

// Retry transient errors (502/503/504, network errors) up to 2 times with 1s delay
apiClient.interceptors.response.use(undefined, async (error) => {
  const config = error.config;
  if (config) {
    const status = error.response?.status;
    const isTransient = !status || status === 502 || status === 503 || status === 504;
    const isNotClientError = !status || status >= 500;
    if (isTransient && isNotClientError) {
      config._retryCount = config._retryCount ?? 0;
      if (config._retryCount < 2) {
        config._retryCount += 1;
        await new Promise((r) => setTimeout(r, 1000));
        return apiClient(config);
      }
    }
  }
  return Promise.reject(error);
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      const { ssoEnabled } = useAuthStore.getState();
      if (ssoEnabled) {
        // Token may be mid-silent-renewal — retry once after a short delay
        originalRequest._retry = true;
        const oldToken = useAuthStore.getState().token;

        await new Promise((r) => setTimeout(r, 2000));

        const newToken = useAuthStore.getState().token;
        if (newToken && newToken !== oldToken) {
          // Token was refreshed during the wait — retry with the new token
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        }

        // Token unchanged — genuine auth failure, trigger full logout
        const { logout, oidcSignout } = useAuthStore.getState();
        logout();
        if (oidcSignout) {
          await oidcSignout().catch(() => {});
        }
      }
    }

    if (error.response?.status === 503) {
      console.warn("Service temporarily unavailable:", error.response.data);
    }

    return Promise.reject(error);
  },
);

export default apiClient;
