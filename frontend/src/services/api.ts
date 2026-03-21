import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { createClient } from "@/utils/supabase/client";

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
  timeout: 15_000,
});

// Attach Supabase JWT to every request
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

// Normalise every error into a structured ApiError
api.interceptors.response.use(
  (res: any) => res,
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
  message: string,
  signal?: AbortSignal,
): Promise<{ tone: string; suggestions: string[] }> {
  try {
    const response = await withRetry(() =>
      api.post<{ tone?: string; suggestions?: string[] }>("/api/ai/reply", { message }, { signal }),
    ) as unknown as { data: { tone?: string; suggestions?: string[] } };
    const { data } = response;
    return {
      tone: data.tone ?? "casual",
      suggestions: data.suggestions?.length ? data.suggestions : FALLBACK_SUGGESTIONS,
    };
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    if ((err as { name?: string }).name === "CanceledError") throw err;
    console.error("[api] fetchAiSuggestions failed, using fallback:", err);
    return { tone: "casual", suggestions: FALLBACK_SUGGESTIONS };
  }
}
