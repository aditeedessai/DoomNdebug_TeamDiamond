import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000/api/v1",
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: attach bearer token and handle multipart payloads
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // When sending FormData (e.g. image uploads), let browser define the multipart boundary
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: normalize error messages and handle 401 session expiry safely
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const requestUrl = error.config?.url || "";

    // If unauthorized and not a login/register attempt, clear local session
    if (status === 401 && !requestUrl.includes("/auth/login") && !requestUrl.includes("/auth/register")) {
      localStorage.removeItem("access_token");
    }

    // Extract user-friendly error message from backend HTTPException
    const detail = error.response?.data?.detail || error.response?.data?.message || error.message;
    if (typeof detail === "string") {
      error.userMessage = detail;
    } else if (Array.isArray(detail)) {
      error.userMessage = detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
    } else if (detail && typeof detail === "object") {
      error.userMessage = JSON.stringify(detail);
    } else {
      error.userMessage = "Network error or server unavailable. Please try again.";
    }

    return Promise.reject(error);
  }
);

export default api;
