"use client";

import {
  Bot,
  CalendarDays,
  CheckSquare,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Settings,
  Umbrella,
  UserCheck
} from "lucide-react";

const items = [
  ["Dashboard", LayoutDashboard],
  ["AI Assistant", Bot],
  ["Meetings", CalendarDays],
  ["ClickUp", CheckSquare],
  ["Slack", MessageSquare],
  ["Attendance", UserCheck],
  ["Leaves", Umbrella],
  ["Settings", Settings]
] as const;

export function AppShell({
  active,
  onSelect,
  children
}: {
  active: string;
  onSelect: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-mist">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-white px-4 py-5 lg:block">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-lg bg-brand text-white">
            <Bot size={22} />
          </div>
          <div>
            <div className="text-sm font-semibold text-ink">Employee AI</div>
            <div className="text-xs text-slate-500">Copilot</div>
          </div>
        </div>
        <nav className="space-y-1">
          {items.map(([label, Icon]) => (
            <button
              key={label}
              onClick={() => onSelect(label)}
              className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition ${
                active === label ? "bg-blue-50 text-brand" : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-line bg-white/90 px-4 backdrop-blur lg:px-8">
          <div className="flex items-center gap-3">
            <button className="grid size-9 place-items-center rounded-md border border-line lg:hidden" aria-label="Open navigation">
              <Menu size={18} />
            </button>
            <div>
              <h1 className="text-lg font-semibold text-ink">{active}</h1>
              <p className="text-xs text-slate-500">OMS, Calendar, ClickUp, and Slack in one place</p>
            </div>
          </div>
          <div className="rounded-full border border-line px-3 py-1 text-xs text-slate-500">Local Ollama</div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
