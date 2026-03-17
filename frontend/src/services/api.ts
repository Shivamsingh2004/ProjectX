import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

// ---------------------------------------------------------------------------
// Fallback suggestions shown when the AI service is unavailable
// ---------------------------------------------------------------------------
export const FALLBACK_SUGGESTIONS = [
  "Tell me more 😊",
  "That sounds interesting!",
  "What happened next?",
];

// ---------------------------------------------------------------------------
// Structured error type returned by all API helpers
// ---------------------------------------------------------------------------
export type ApiError = { success: false; message: string };

// ---------------------------------------------------------------------------
// Reusable Axios instance
// ---------------------------------------------------------------------------
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080",
  timeout: 10_000,
});

// Attach JWT token from localStorage (client-side only)
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Normalise every error into a structured ApiError
api.interceptors.response.use(
  (res) => res,
  (err: AxiosError<{ message?: string }>) => {
    const message =
      err.response?.data?.message ??
      (err.code === "ECONNABORTED" ? "Request timed out" : "Something went wrong");
    return Promise.reject({ success: false, message } satisfies ApiError);
  },
);

// ---------------------------------------------------------------------------
// Retry helper – exponential back-off, up to `maxRetries` attempts
// ---------------------------------------------------------------------------
async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 2,
  baseDelayMs = 300,
): Promise<T> {
  let attempt = 0;
  while (true) {
    try {
      return await fn();
    } catch (err) {
      if (attempt >= maxRetries) throw err;
      const delay = baseDelayMs * 2 ** attempt;
      await new Promise((resolve) => setTimeout(resolve, delay));
      attempt++;
    }
  }
}

// ---------------------------------------------------------------------------
// AI reply-suggestion helper
// ---------------------------------------------------------------------------
export async function fetchAiSuggestions(
  context: { conversationId: string; lastMessage: string },
  signal?: AbortSignal,
): Promise<string[]> {
  try {
    const { data } = await withRetry(() =>
      api.post<{ suggestions: string[] }>("/ai/reply-suggestion", context, { signal }),
    );
    return data.suggestions?.length ? data.suggestions : FALLBACK_SUGGESTIONS;
  } catch (err) {
    // AbortError – don't log, just propagate so the caller can handle it
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    if ((err as { name?: string }).name === "CanceledError") throw err;
    console.error("[api] fetchAiSuggestions failed, using fallback:", err);
    return FALLBACK_SUGGESTIONS;
  }
}
