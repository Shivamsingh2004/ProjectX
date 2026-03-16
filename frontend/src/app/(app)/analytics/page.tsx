"use client";

import dynamic from "next/dynamic";
import { Card } from "@/components/ui";
const PlatformChart = dynamic(
  () => import("@/components/platform-chart").then((m) => m.PlatformChart),
  { ssr: false },
);

export default function AnalyticsPage() {
  return (
    <Card title="Platform Performance">
      <div className="h-72">
        <PlatformChart />
      </div>
    </Card>
  );
}
