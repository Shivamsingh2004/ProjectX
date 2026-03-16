import { Card } from "@/components/ui";

export default function ConnectedPlatformsPage() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card title="Tinder"><p>Connected</p></Card>
      <Card title="Bumble"><p>Connected</p></Card>
      <Card title="Hinge"><p>Not Connected</p></Card>
    </div>
  );
}
