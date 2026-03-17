export type Conversation = {
  id: string;
  name: string;
  platform: string;
  lastMessage: string;
};

export type Message = {
  id: string;
  conversationId: string;
  sender: "me" | "them";
  text: string;
  timestamp: number;
};
