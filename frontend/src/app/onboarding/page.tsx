"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/services/api";

export default function Page() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [preferences, setPreferences] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const parsedPreferences = preferences
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      await api.put("/api/users/profile", {
        fullName: fullName || "New User",
        bio: "",
        preferences: parsedPreferences.length ? parsedPreferences : ["serious relationship"],
        connectedPlatforms: [],
      });
      router.push("/dashboard");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to complete onboarding");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 p-6 dark:bg-zinc-950">
      <div className="w-full max-w-md rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <h1 className="mb-2 text-2xl font-semibold">Onboarding</h1>
        <p className="mb-6 text-sm text-zinc-500">Connect platforms and configure profile preferences.</p>
        <form className="space-y-3" onSubmit={onSubmit}>
          <input id="fullName" name="fullName" aria-label="Full Name" value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Full Name" className="w-full rounded-xl border border-zinc-300 px-3 py-2 dark:border-zinc-700" />
          <input id="preferences" name="preferences" aria-label="Preferences" value={preferences} onChange={(event) => setPreferences(event.target.value)} placeholder="Preferences (comma separated)" className="w-full rounded-xl border border-zinc-300 px-3 py-2 dark:border-zinc-700" />
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <button type="submit" disabled={loading} aria-label="Continue" className="w-full rounded-xl bg-zinc-900 py-2 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900">{loading ? "Saving..." : "Continue"}</button>
        </form>
      </div>
    </div>
  );
}
