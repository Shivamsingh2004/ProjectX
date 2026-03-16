"use client";

import { useAppStore } from "@/store/useAppStore";

export function TopNavbar() {
  const darkMode = useAppStore((s) => s.darkMode);
  const toggleDarkMode = useAppStore((s) => s.toggleDarkMode);

  return (
    <header className="mb-6 flex items-center justify-between rounded-2xl border border-zinc-200 bg-white px-4 py-3 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <span className="text-sm text-zinc-500">Unified Dashboard</span>
      <button className="rounded-lg border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700" onClick={toggleDarkMode}>
        {darkMode ? "Light" : "Dark"} Mode
      </button>
    </header>
  );
}
