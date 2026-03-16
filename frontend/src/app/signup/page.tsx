"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/services/api";

export default function Page() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/api/auth/register", { email, password, fullName: "New User" });
      router.push("/onboarding");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to sign up");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 p-6 dark:bg-zinc-950">
      <div className="w-full max-w-md rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h1 className="mb-2 text-2xl font-semibold">Create Account</h1>
        <p className="mb-6 text-sm text-zinc-500">Get started with secure multi-platform dating management.</p>
        <form className="space-y-3" onSubmit={onSubmit}>
          <input id="email" name="email" aria-label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" className="w-full rounded-xl border border-zinc-300 px-3 py-2 dark:border-zinc-700" />
          <input id="password" name="password" aria-label="Password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" type="password" className="w-full rounded-xl border border-zinc-300 px-3 py-2 dark:border-zinc-700" />
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <button type="submit" disabled={loading} aria-label="Continue" className="w-full rounded-xl bg-zinc-900 py-2 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900">{loading ? "Creating..." : "Continue"}</button>
        </form>
      </div>
    </div>
  );
}
