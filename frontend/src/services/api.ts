import axios, { type InternalAxiosRequestConfig } from "axios";

interface RetryableConfig extends InternalAxiosRequestConfig {
  __retried?: boolean;
}

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080",
  timeout: 15000,
});

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const config = err?.config as RetryableConfig | undefined;
    // Retry idempotent GET requests once on network errors (not 4xx)
    if (
      config &&
      !config.__retried &&
      config.method === "get" &&
      (!err.response || err.response.status >= 500)
    ) {
      config.__retried = true;
      await new Promise((resolve) => setTimeout(resolve, 800));
      return api(config);
    }
    return Promise.reject(new Error(err?.response?.data?.message ?? "Request failed"));
  },
);
