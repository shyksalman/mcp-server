import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Employee AI Copilot",
  description: "Internal employee copilot for OMS, Calendar, and ClickUp"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
