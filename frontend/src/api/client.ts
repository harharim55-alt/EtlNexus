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
