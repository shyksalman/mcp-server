"use client";

import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { Assistant } from "@/components/Assistant";
import { ClickUp } from "@/components/ClickUp";
import { Dashboard } from "@/components/Dashboard";
import { Meetings } from "@/components/Meetings";
import { Card } from "@/components/Card";
import { Slack } from "@/components/Slack";

export default function Page() {
  const [active, setActive] = useState("Dashboard");
  return (
    <AppShell active={active} onSelect={setActive}>
      {active === "Dashboard" && <Dashboard />}
      {active === "AI Assistant" && <Assistant />}
      {active === "Meetings" && <Meetings />}
      {active === "ClickUp" && <ClickUp />}
      {active === "Slack" && <Slack />}
      {active === "Attendance" && <Info title="Attendance" text="Ask the assistant for detailed attendance questions, or use the dashboard for the current snapshot." />}
      {active === "Leaves" && <Info title="Leaves" text="Leave status, balance, and history remain powered by the existing OMS MCP tools." />}
      {active === "Settings" && <Info title="Settings" text="Secrets live in backend environment variables. Frontend only knows the backend API URL." />}
    </AppShell>
  );
}

function Info({ title, text }: { title: string; text: string }) {
  return (
    <Card title={title}>
      <p className="text-sm text-slate-600">{text}</p>
    </Card>
  );
}
