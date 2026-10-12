"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { Card } from "./Card";

type DashboardData = {
  attendance?: Record<string, unknown>;
  leave_balance?: Record<string, unknown>;
  meetings_today?: { meetings?: Array<Record<string, string>> };
  clickup_summary?: Record<string, number>;
  tasks_due_today?: { tasks?: Array<Record<string, string>> };
  ai_daily_brief?: string;
};

export function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<DashboardData>("/api/dashboard").then(setData).catch(() => setError("Dashboard data is temporarily unavailable."));
  }, []);

  if (error) return <div className="rounded-lg border border-line bg-white p-6 text-sm text-danger">{error}</div>;
  if (!data) return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-36 animate-pulse rounded-lg bg-white" />)}</div>;

  const meetings = data.meetings_today?.meetings ?? [];
  const dueTasks = data.tasks_due_today?.tasks ?? [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Attendance">
          <p className="text-2xl font-semibold">{String(data.attendance?.status ?? data.attendance?.present ?? "Available")}</p>
          <p className="mt-2 text-sm text-slate-500">Today&apos;s OMS attendance snapshot</p>
        </Card>
        <Card title="Meetings Today">
          <p className="text-2xl font-semibold">{meetings.length}</p>
          <p className="mt-2 text-sm text-slate-500">{meetings[0]?.title ? `Next: ${meetings[0].title}` : "No meetings found"}</p>
        </Card>
        <Card title="ClickUp">
          <p className="text-2xl font-semibold">{data.clickup_summary?.total_open ?? 0} open</p>
          <p className="mt-2 text-sm text-slate-500">{data.clickup_summary?.high_priority ?? 0} high priority</p>
        </Card>
        <Card title="Leave Balance">
          <p className="text-2xl font-semibold">{String(data.leave_balance?.remaining ?? "Ready")}</p>
          <p className="mt-2 text-sm text-slate-500">Remaining leave from OMS</p>
        </Card>
      </div>
      <Card title="AI Daily Brief">
        <p className="text-sm leading-6 text-slate-700">{data.ai_daily_brief}</p>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Today's Meetings">
          <div className="space-y-3">
            {meetings.length ? meetings.map((item) => <Row key={item.id} title={item.title} meta={`${item.start} - ${item.end}`} />) : <Empty text="No meetings today." />}
          </div>
        </Card>
        <Card title="Tasks Due Today">
          <div className="space-y-3">
            {dueTasks.length ? dueTasks.map((item) => <Row key={item.id} title={item.name} meta={`${item.priority ?? "Normal"} · ${item.status ?? "Open"}`} />) : <Empty text="No ClickUp tasks due today." />}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Row({ title, meta }: { title?: string; meta?: string }) {
  return (
    <div className="rounded-md border border-line p-3">
      <div className="text-sm font-medium">{title}</div>
      <div className="mt-1 text-xs text-slate-500">{meta}</div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="rounded-md border border-dashed border-line p-4 text-sm text-slate-500">{text}</p>;
}
