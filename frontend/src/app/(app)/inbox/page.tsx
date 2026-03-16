"use client";

import { Card } from "@/components/ui";
import { useAppStore } from "@/store/useAppStore";

export default function InboxPage() {
  const conversations = useAppStore((s) => s.conversations);
  return (
    <Card title="Unified Inbox">
      <ul className="space-y-3">
        {conversations.map((c) => (
          <li key={c.id} className="rounded-xl border border-zinc-200 p-3 dark:border-zinc-700">
            <p className="font-medium">{c.name} · {c.platform}</p>
            <p className="text-sm text-zinc-500">{c.lastMessage}</p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
