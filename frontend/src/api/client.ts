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
  (error) => {
    if (error.response?.status === 401) {
      const { ssoEnabled, logout } = useAuthStore.getState();
      if (ssoEnabled) {
        // Token expired or invalid — clear state so AuthGuard redirects to login
        logout();
      }
    }
    if (error.response?.status === 503) {
      console.warn("Service temporarily unavailable:", error.response.data);
    }
    return Promise.reject(error);
  }
);

export default apiClient;
