import { Card } from "@/components/ui";

export default function AIAssistantPage() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Reply Suggestions"><p>“I love hiking too — what trails do you enjoy most?”</p></Card>
      <Card title="Profile Improvement"><p>Add a specific weekend activity for better engagement.</p></Card>
    </div>
  );
}
