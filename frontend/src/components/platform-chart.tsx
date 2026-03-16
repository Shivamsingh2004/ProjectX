"use client";

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

const data = [
  { platform: "Tinder", matches: 30 },
  { platform: "Bumble", matches: 22 },
  { platform: "Hinge", matches: 18 },
];

export function PlatformChart() {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <XAxis dataKey="platform" />
        <YAxis />
        <Bar dataKey="matches" fill="#4f46e5" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
