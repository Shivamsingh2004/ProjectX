import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080",
  timeout: 10000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(new Error(err?.response?.data?.message ?? "Request failed"))
);
