"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/services/api";
import { socket } from "@/services/socket";
import { useAppStore } from "@/store/useAppStore";
import type { Conversation } from "@/utils/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Message = {
  id: string;
  content: string;
  senderId: string;
  timestamp: string;
  status: "sent" | "delivered" | "read";
};

type AISuggestion = {
  tone: string;
  suggestions: string[];
};

// ---------------------------------------------------------------------------
// Skeleton loader
// ---------------------------------------------------------------------------

function MessageSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-3">
      {[70, 50, 85].map((w) => (
        <div key={w} className="flex items-end gap-2">
          <div className="h-8 w-8 flex-shrink-0 animate-pulse rounded-full bg-zinc-200 dark:bg-zinc-700" />
          <div
            className="h-9 animate-pulse rounded-2xl bg-zinc-200 dark:bg-zinc-700"
            style={{ width: `${w}%` }}
          />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Conversation list item
// ---------------------------------------------------------------------------

function ConversationItem({
  conv,
  active,
  onClick,
}: {
  conv: Conversation;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <motion.button
      layout
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      onClick={onClick}
      className={`w-full rounded-xl border p-3 text-left transition-colors ${
        active
          ? "border-pink-400 bg-pink-50 dark:border-pink-600 dark:bg-pink-950/40"
          : "border-zinc-200 bg-white hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800 dark:hover:border-zinc-600"
      }`}
    >
      <p className="font-semibold text-zinc-800 dark:text-zinc-100">
        {conv.name}
        <span className="ml-1.5 text-xs font-normal text-zinc-400">
          · {conv.platform}
        </span>
      </p>
      <p className="mt-0.5 truncate text-xs text-zinc-500">{conv.lastMessage}</p>
    </motion.button>
  );
}

// ---------------------------------------------------------------------------
// AI Suggestion panel
// ---------------------------------------------------------------------------

function AISuggestionPanel({
  suggestion,
  loading,
  onUse,
}: {
  suggestion: AISuggestion | null;
  loading: boolean;
  onUse: (text: string) => void;
}) {
  if (loading) {
    return (
      <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50">
        <p className="mb-2 text-xs font-semibold text-zinc-400">✨ AI Suggestions</p>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="mb-1.5 h-8 animate-pulse rounded-lg bg-zinc-200 dark:bg-zinc-700"
          />
        ))}
      </div>
    );
  }

  if (!suggestion) return null;

  const toneColors: Record<string, string> = {
    funny: "text-yellow-600 dark:text-yellow-400",
    flirty: "text-pink-600 dark:text-pink-400",
    serious: "text-blue-600 dark:text-blue-400",
    casual: "text-green-600 dark:text-green-400",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/50"
    >
      <p className="mb-2 text-xs font-semibold text-zinc-400">
        ✨ AI Suggestions{" "}
        <span className={`capitalize ${toneColors[suggestion.tone] ?? "text-zinc-500"}`}>
          · {suggestion.tone} tone
        </span>
      </p>
      <div className="flex flex-col gap-1.5">
        {suggestion.suggestions.map((s, i) => (
          <motion.button
            key={i}
            whileHover={{ scale: 1.005 }}
            whileTap={{ scale: 0.995 }}
            onClick={() => onUse(s)}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-left text-sm text-zinc-700 transition-colors hover:border-pink-300 hover:bg-pink-50 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:border-pink-600 dark:hover:bg-pink-950/30"
          >
            {s}
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main chat page
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const conversations = useAppStore((s) => s.conversations);
  const [activeConv, setActiveConv] = useState<Conversation>(
    () => conversations[0] ?? { id: "", name: "No conversations", platform: "", lastMessage: "" },
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isTyping, setIsTyping] = useState(false); // remote party typing
  const [aiSuggestion, setAISuggestion] = useState<AISuggestion | null>(null);
  const [aiLoading, setAILoading] = useState(false);
  const [lastMessage, setLastMessage] = useState("");

  const bottomRef = useRef<HTMLDivElement>(null);
  const aiDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // WebSocket: subscribe to messages, typing, and read receipts
  useEffect(() => {
    socket.connect();

    socket.on("message", (msg: Message) => {
      setMessages((prev) => [...prev, msg]);
    });

    socket.on("typing", ({ typing }: { typing: boolean }) => {
      setIsTyping(typing);
    });

    return () => {
      socket.off("message");
      socket.off("typing");
      socket.disconnect();
    };
  }, []);

  // Load initial placeholder messages when conversation switches
  useEffect(() => {
    setMessagesLoading(true);
    setMessages([]);
    setAISuggestion(null);

    // Simulate network delay / REST fetch
    const t = setTimeout(() => {
      setMessages([
        {
          id: "m1",
          content: activeConv.lastMessage,
          senderId: "them",
          timestamp: new Date(Date.now() - 60_000).toISOString(),
          status: "read",
        },
      ]);
      setLastMessage(activeConv.lastMessage);
      setMessagesLoading(false);
    }, 600);

    return () => clearTimeout(t);
  }, [activeConv]);

  // Debounced AI suggestion fetch when last message changes
  useEffect(() => {
    if (!lastMessage) return;
    if (aiDebounceRef.current) clearTimeout(aiDebounceRef.current);

    aiDebounceRef.current = setTimeout(async () => {
      setAILoading(true);
      try {
        const res = await api.post<AISuggestion>("/api/ai/reply-suggestion", {
          message: lastMessage,
          user_context: `Talking to ${activeConv.name} on ${activeConv.platform}`,
        });
        setAISuggestion(res.data);
      } catch {
        // Graceful degradation — keep previous suggestions
      } finally {
        setAILoading(false);
      }
    }, 400);

    return () => {
      if (aiDebounceRef.current) clearTimeout(aiDebounceRef.current);
    };
  }, [lastMessage, activeConv]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      const optimistic: Message = {
        id: crypto.randomUUID(),
        content: trimmed,
        senderId: "me",
        timestamp: new Date().toISOString(),
        status: "sent",
      };

      setMessages((prev) => [...prev, optimistic]);
      setInput("");
      setIsSending(true);

      try {
        await api.post("/api/messages/send", {
          conversationId: activeConv.id,
          platform: activeConv.platform,
          content: trimmed,
        });
        // Mark as delivered
        setMessages((prev) =>
          prev.map((m) =>
            m.id === optimistic.id ? { ...m, status: "delivered" } : m,
          ),
        );
        setLastMessage(trimmed);
      } catch {
        // Mark as failed
        setMessages((prev) =>
          prev.map((m) =>
            m.id === optimistic.id ? { ...m, status: "sent" } : m,
          ),
        );
      } finally {
        setIsSending(false);
      }
    },
    [activeConv, isSending],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const statusIcon = (status: Message["status"]) => {
    if (status === "read") return "✓✓";
    if (status === "delivered") return "✓✓";
    return "✓";
  };

  return (
    <div className="grid h-[calc(100vh-8rem)] gap-4 lg:grid-cols-3">
      {/* Conversation list */}
      <aside className="flex flex-col gap-2 overflow-y-auto rounded-2xl border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-900">
        <h3 className="mb-1 text-sm font-semibold text-zinc-500 dark:text-zinc-400">
          Conversations
        </h3>
        {conversations.map((c) => (
          <ConversationItem
            key={c.id}
            conv={c}
            active={c.id === activeConv.id}
            onClick={() => setActiveConv(c)}
          />
        ))}
      </aside>

      {/* Chat window */}
      <section className="flex flex-col overflow-hidden rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 lg:col-span-2">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-3 dark:border-zinc-800">
          <div>
            <p className="font-semibold text-zinc-800 dark:text-zinc-100">
              {activeConv.name}
            </p>
            <p className="text-xs text-zinc-400">{activeConv.platform}</p>
          </div>
          <span className="flex h-2 w-2 rounded-full bg-green-400" title="Online" />
        </div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-4">
          {messagesLoading ? (
            <MessageSkeleton />
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={`mb-3 flex ${
                    msg.senderId === "me" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[72%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                      msg.senderId === "me"
                        ? "bg-pink-500 text-white"
                        : "bg-zinc-100 text-zinc-800 dark:bg-zinc-700 dark:text-zinc-100"
                    }`}
                  >
                    <p>{msg.content}</p>
                    <p
                      className={`mt-0.5 text-right text-[10px] ${
                        msg.senderId === "me"
                          ? "text-pink-200"
                          : "text-zinc-400"
                      }`}
                    >
                      {new Date(msg.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}{" "}
                      {msg.senderId === "me" && statusIcon(msg.status)}
                    </p>
                  </div>
                </motion.div>
              ))}

              {/* Typing indicator */}
              {isTyping && (
                <motion.div
                  key="typing"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-3 flex justify-start"
                >
                  <div className="rounded-2xl bg-zinc-100 px-4 py-2.5 dark:bg-zinc-700">
                    <span className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <motion.span
                          key={i}
                          className="h-1.5 w-1.5 rounded-full bg-zinc-400"
                          animate={{ y: [0, -4, 0] }}
                          transition={{
                            duration: 0.8,
                            repeat: Infinity,
                            delay: i * 0.15,
                          }}
                        />
                      ))}
                    </span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          )}
          <div ref={bottomRef} />
        </div>

        {/* AI Suggestions */}
        <div className="border-t border-zinc-100 px-4 pt-3 dark:border-zinc-800">
          <AISuggestionPanel
            suggestion={aiSuggestion}
            loading={aiLoading}
            onUse={(text) => setInput(text)}
          />
        </div>

        {/* Input area */}
        <div className="flex items-end gap-2 border-t border-zinc-100 px-4 py-3 dark:border-zinc-800">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message… (Enter to send)"
            rows={2}
            className="flex-1 resize-none rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm outline-none transition-colors focus:border-pink-400 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-pink-600"
          />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isSending}
            className="rounded-xl bg-pink-500 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:bg-pink-600 disabled:opacity-40"
          >
            {isSending ? "…" : "Send"}
          </motion.button>
        </div>
      </section>
    </div>
  );
}

