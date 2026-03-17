import { create } from "zustand";
import type { Message } from "@/utils/types";

type ChatState = {
  messages: Message[];
  suggestions: string[];
  suggestionsLoading: boolean;
  partnerTyping: boolean;
  activeConversationId: string | null;

  setActiveConversation: (id: string) => void;
  addMessage: (msg: Message) => void;
  setSuggestions: (s: string[]) => void;
  setSuggestionsLoading: (v: boolean) => void;
  setPartnerTyping: (v: boolean) => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  suggestions: [],
  suggestionsLoading: false,
  partnerTyping: false,
  activeConversationId: null,

  setActiveConversation: (id) =>
    set({ activeConversationId: id, messages: [], suggestions: [] }),

  addMessage: (msg) =>
    set((state) => ({ messages: [...state.messages, msg] })),

  setSuggestions: (s) => set({ suggestions: s }),

  setSuggestionsLoading: (v) => set({ suggestionsLoading: v }),

  setPartnerTyping: (v) => set({ partnerTyping: v }),
}));
