"use client";

import { ChatComponent } from "@/components/ChatComponent";
import { useAppStore } from "@/store/useAppStore";

export default function ChatPage() {
  const conversations = useAppStore((s) => s.conversations);
  return <ChatComponent conversations={conversations} />;
}
