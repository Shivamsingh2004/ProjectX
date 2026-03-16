import { create } from "zustand";
import type { Conversation } from "@/utils/types";

type AppState = {
  darkMode: boolean;
  conversations: Conversation[];
  toggleDarkMode: () => void;
};

export const useAppStore = create<AppState>((set) => ({
  darkMode: false,
  conversations: [
    { id: "conv-1", name: "Alex", platform: "Tinder", lastMessage: "Hey! How's your day?" },
    { id: "conv-2", name: "Riley", platform: "Bumble", lastMessage: "Let's plan coffee ☕" },
  ],
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}));
