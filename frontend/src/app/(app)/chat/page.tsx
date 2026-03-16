import { Card } from "@/components/ui";

export default function ChatPage() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card title="Conversation List"><p>Alex, Riley, Jordan</p></Card>
      <div className="lg:col-span-2">
        <Card title="Chat Window"><p>Realtime messages and typing indicators appear here.</p></Card>
      </div>
    </div>
  );
}
