import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dating Platform Aggregator",
  description: "Unified dashboard for multi-platform dating management",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
