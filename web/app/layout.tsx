import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Prospect Intel Agent",
  description: "Grounded outbound research, one domain at a time.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-950 text-ink-100">{children}</body>
    </html>
  );
}
