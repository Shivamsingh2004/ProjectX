import { Card } from "@/components/ui";

export default function DashboardPage() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Card title="New Likes"><p className="text-3xl font-bold">12</p></Card>
      <Card title="New Matches"><p className="text-3xl font-bold">5</p></Card>
      <Card title="Unread Messages"><p className="text-3xl font-bold">9</p></Card>
    </div>
  );
}
