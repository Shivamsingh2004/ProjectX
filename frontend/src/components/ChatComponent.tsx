"use client";

import { memo, useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChat } from "@/hooks/useChat";
import type { Message } from "@/utils/types";

const MAX_MESSAGE_LENGTH = 2000;

// ---------------------------------------------------------------------------
// Sub-components (memoised to avoid unnecessary re-renders)
// ---------------------------------------------------------------------------

const MessageBubble = memo(function MessageBubble({ msg }: { msg: Message }) {
  const isMe = msg.sender === "me";
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={`flex ${isMe ? "justify-end" : "justify-start"}`}
    >
      <span
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
          isMe
            ? "rounded-br-sm bg-gradient-to-br from-rose-500 to-pink-500 text-white"
            : "rounded-bl-sm bg-white text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100"
        }`}
      >
        {/* React escapes text content automatically, preventing XSS */}
        {msg.text}
      </span>
    </motion.div>
  );
});

const TypingDots = memo(function TypingDots({ name }: { name: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-1.5 text-xs text-zinc-400"
    >
      <span>{name} is typing</span>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ repeat: Infinity, duration: 1, delay: i * 0.2 }}
          className="inline-block h-1 w-1 rounded-full bg-zinc-400"
        />
      ))}
    </motion.div>
  );
});

const SuggestionSkeleton = memo(function SuggestionSkeleton() {
  return (
    <div className="flex gap-2">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-8 flex-1 animate-pulse rounded-full bg-zinc-200 dark:bg-zinc-700"
        />
      ))}
    </div>
  );
});

const SuggestionChip = memo(function SuggestionChip({
  text,
  onClick,
}: {
  text: string;
  onClick: () => void;
}) {
  return (
    <motion.button
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      onClick={onClick}
      className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-600 shadow-sm transition-colors hover:bg-rose-100 dark:border-rose-800 dark:bg-rose-950/30 dark:text-rose-300 dark:hover:bg-rose-900/40"
    >
      {text}
    </motion.button>
  );
});

// ---------------------------------------------------------------------------
// Conversation list item
// ---------------------------------------------------------------------------
const ConversationItem = memo(function ConversationItem({
  id,
  name,
  platform,
  lastMessage,
  active,
  onSelect,
}: {
  id: string;
  name: string;
  platform: string;
  lastMessage: string;
  active: boolean;
  onSelect: (id: string, name: string) => void;
}) {
  return (
    <button
      onClick={() => onSelect(id, name)}
      className={`w-full rounded-xl px-3 py-2.5 text-left transition-colors ${
        active
          ? "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300"
          : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
      }`}
    >
      <p className="text-sm font-semibold leading-tight">{name}</p>
      <p className="mt-0.5 truncate text-xs text-zinc-500">{platform} · {lastMessage}</p>
    </button>
  );
});

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
interface ChatComponentProps {
  conversations: { id: string; name: string; platform: string; lastMessage: string }[];
}

export const ChatComponent = memo(function ChatComponent({
  conversations,
}: ChatComponentProps) {
  const [activeId, setActiveId] = useState<string>(conversations[0]?.id ?? "");
  const [activeName, setActiveName] = useState<string>(conversations[0]?.name ?? "");
  const [inputValue, setInputValue] = useState("");

  // Derive effective active conversation (falls back to first if current no longer exists)
  const activeConv =
    conversations.find((c) => c.id === activeId) ?? conversations[0];
  const effectiveActiveId = activeConv?.id ?? "";
  const effectiveActiveName = activeConv?.name ?? activeName;

  const {
    messages,
    suggestions,
    suggestionsLoading,
    partnerTyping,
    sendMessage,
    onTyping,
  } = useChat(effectiveActiveId, effectiveActiveName);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, partnerTyping]);

  const handleSend = useCallback(() => {
    const text = inputValue.trim();
    if (!text) return;
    sendMessage(text);
    setInputValue("");
    inputRef.current?.focus();
  }, [inputValue, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(e.target.value);
      onTyping(e.target.value);
    },
    [onTyping],
  );

  const handleSuggestionClick = useCallback((text: string) => {
    setInputValue(text);
    inputRef.current?.focus();
  }, []);

  const handleConversationSelect = useCallback((id: string, name: string) => {
    setActiveId(id);
    setActiveName(name);
    setInputValue("");
  }, []);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {/* Conversation list */}
      <section className="rounded-2xl border border-zinc-200 bg-white/90 p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90">
        <h3 className="mb-3 text-sm font-semibold text-zinc-500 dark:text-zinc-400">
          Conversations
        </h3>
        <div className="flex flex-col gap-1">
          {conversations.map((c) => (
            <ConversationItem
              key={c.id}
              {...c}
              active={c.id === effectiveActiveId}
              onSelect={handleConversationSelect}
            />
          ))}
        </div>
      </section>

      {/* Chat window */}
      <section className="flex flex-col rounded-2xl border border-zinc-200 bg-white/90 shadow-sm dark:border-zinc-800 dark:bg-zinc-900/90 lg:col-span-2">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-zinc-100 px-5 py-3.5 dark:border-zinc-800">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-rose-400 to-pink-500 text-sm font-bold text-white">
            {effectiveActiveName.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-semibold">{effectiveActiveName}</p>
            <p className="text-xs text-zinc-400">
              {activeConv?.platform ?? ""}
            </p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex flex-1 flex-col gap-2.5 overflow-y-auto p-4" style={{ minHeight: 320, maxHeight: 420 }}>
          <AnimatePresence initial={false}>
            {messages.length === 0 ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-zinc-400"
              >
                <span className="text-3xl">💬</span>
                <p className="text-sm">No messages yet – say hello!</p>
              </motion.div>
            ) : (
              messages.map((msg) => <MessageBubble key={msg.id} msg={msg} />)
            )}
          </AnimatePresence>

          <AnimatePresence>
            {partnerTyping && (
              <motion.div key="typing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <TypingDots name={effectiveActiveName} />
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={bottomRef} />
        </div>

        {/* AI Suggestions */}
        <div className="border-t border-zinc-100 px-4 py-2 dark:border-zinc-800">
          {suggestionsLoading ? (
            <SuggestionSkeleton />
          ) : (
            <AnimatePresence>
              {suggestions.length > 0 && (
                <motion.div
                  key="suggestions"
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  className="flex flex-wrap gap-2"
                >
                  {suggestions.map((s, i) => (
                    <SuggestionChip
                      key={i}
                      text={s}
                      onClick={() => handleSuggestionClick(s)}
                    />
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          )}
        </div>

        {/* Input */}
        <div className="flex items-center gap-2 border-t border-zinc-100 px-4 py-3 dark:border-zinc-800">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Type a message…"
            maxLength={MAX_MESSAGE_LENGTH}
            className="flex-1 rounded-full border border-zinc-200 bg-zinc-50 px-4 py-2 text-sm outline-none transition-all focus:border-rose-400 focus:ring-2 focus:ring-rose-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:border-rose-500 dark:focus:ring-rose-900/30"
          />
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={handleSend}
            disabled={!inputValue.trim()}
            aria-label="Send message"
            className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-rose-500 to-pink-500 text-white shadow-sm transition-opacity disabled:opacity-40"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
              <path d="M3.105 3.105a1 1 0 011.293-.092l12 7a1 1 0 010 1.674l-12 7a1 1 0 01-1.399-1.302L4.613 11H10a1 1 0 000-2H4.613L2.999 4.395a1 1 0 01.106-.29z" />
            </svg>
          </motion.button>
        </div>
      </section>
    </div>
  );
});
