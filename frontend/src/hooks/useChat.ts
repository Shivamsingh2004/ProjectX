"use client";

import { useEffect, useRef, useCallback } from "react";
import { socket } from "@/services/socket";
import { fetchAiSuggestions, FALLBACK_SUGGESTIONS } from "@/services/api";
import { useChatStore } from "@/store/chatStore";
import type { Message } from "@/utils/types";

const DEBOUNCE_MS = 400;

export function useChat(conversationId: string, partnerName: string) {
  const {
    messages,
    suggestions,
    suggestionsLoading,
    partnerTyping,
    addMessage,
    setSuggestions,
    setSuggestionsLoading,
    setPartnerTyping,
    setActiveConversation,
  } = useChatStore();

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // ── boot ──────────────────────────────────────────────────────────────────
  useEffect(() => {
    setActiveConversation(conversationId);
  }, [conversationId, setActiveConversation]);

  // ── cleanup on unmount ────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      abortRef.current?.abort();
    };
  }, []);

  // ── socket ────────────────────────────────────────────────────────────────
  useEffect(() => {
    socket.connect();

    const onMessage = (msg: Message) => {
      if (msg.conversationId !== conversationId) return;
      // Only trigger suggestions for incoming partner messages
      if (msg.sender === "me") return;
      addMessage(msg);
      triggerSuggestions(msg.text);
    };

    const onTyping = (data: { conversationId: string; typing: boolean }) => {
      if (data.conversationId === conversationId) {
        setPartnerTyping(data.typing);
      }
    };

    socket.on("message", onMessage);
    socket.on("typing", onTyping);

    return () => {
      // Only remove the specific listeners; do not disconnect the shared socket
      socket.off("message", onMessage);
      socket.off("typing", onTyping);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // ── helpers ───────────────────────────────────────────────────────────────
  const triggerSuggestions = useCallback(
    (lastMessage: string) => {
      // Cancel any in-flight request
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setSuggestionsLoading(true);
      fetchAiSuggestions(lastMessage, controller.signal)
        .then((s) => {
          setSuggestions(s.suggestions);
          setSuggestionsLoading(false);
        })
        .catch((err: unknown) => {
          const name = (err as { name?: string })?.name;
          if (name === "AbortError" || name === "CanceledError") return;
          setSuggestions(FALLBACK_SUGGESTIONS);
          setSuggestionsLoading(false);
        });
    },
    [conversationId, setSuggestions, setSuggestionsLoading],
  );

  /** Send a message optimistically and over the socket */
  const sendMessage = useCallback(
    (text: string) => {
      const msg: Message = {
        id: crypto.randomUUID(),
        conversationId,
        sender: "me",
        text,
        timestamp: Date.now(),
      };
      addMessage(msg);
      socket.emit("message", msg);
      setSuggestions([]);
    },
    [conversationId, addMessage, setSuggestions],
  );

  /** Debounced handler for the typing indicator + suggestion fetch */
  const onTyping = useCallback(
    (value: string) => {
      socket.emit("typing", { conversationId, typing: value.length > 0 });

      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      if (!value) return;

      debounceTimer.current = setTimeout(() => {
        triggerSuggestions(value);
      }, DEBOUNCE_MS);
    },
    [conversationId, triggerSuggestions],
  );

  return {
    messages,
    suggestions,
    suggestionsLoading,
    partnerTyping,
    partnerName,
    sendMessage,
    onTyping,
  };
}
