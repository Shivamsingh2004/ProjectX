"use client";

import type { ReactNode } from "react";
import { NavigationSidebar } from "@/components/navigation-sidebar";
import { TopNavbar } from "@/components/top-navbar";
import { useRealtime } from "@/hooks/useRealtime";
import { useAppStore } from "@/store/useAppStore";

export function AppShell({ children }: { children: ReactNode }) {
  useRealtime();
  const darkMode = useAppStore((s) => s.darkMode);

  return (
    <div className={`min-h-screen p-6 ${darkMode ? "bg-zinc-950 text-zinc-100" : "bg-zinc-50 text-zinc-900"}`}>
      <div className="mx-auto flex max-w-7xl gap-6">
        <NavigationSidebar />
        <main className="flex-1">
          <TopNavbar />
          {children}
        </main>
      </div>
    </div>
  );
}
